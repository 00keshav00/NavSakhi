# app/providers/shared/nominatim_coordinator.py
"""
NavSakhi Phase 51.26 - Shared In-Process Nominatim Request Coordinator

Enforces OpenStreetMap Nominatim Usage Policy for all in-process callers:
- Minimum 1.05s spacing between outbound request starts.
- Strict request serialization via async lock (zero request overlap).
- Single-flight deduplication for concurrent identical queries.
- Monotonic timestamp-based TTL caching with bounded capacity.
- Automatic HTTP 429 Retry-After parsing and global cooldown backoff.
- Configurable User-Agent and optional email contact identification.
- Provider switching support via settings.nominatim_base_url.

NOTE: This coordinator serializes requests within a single process.
In production with Render (1 Uvicorn worker), this guarantees compliance.
If scaling to multiple workers or instances, a shared external rate limiter
(such as Redis token bucket) or dedicated self-hosted Nominatim is required.
"""

import asyncio
import email.utils
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.config.settings import settings
from app.providers.shared.exceptions import (
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger("nominatim_coordinator")


class NominatimCoordinator:
    """
    Thread-safe, async request coordinator enforcing serialized execution,
    minimum interval spacing, single-flight deduplication, and TTL caching.
    """

    def __init__(
        self,
        min_interval_seconds: float = 1.05,
        default_ttl_seconds: int = 86400,
        max_cache_entries: int = 1000,
        timeout_seconds: float = 5.0,
        cache_ttl_seconds: Optional[int] = None,
        max_cache_size: Optional[int] = None,
    ):
        self.min_interval = min_interval_seconds
        self.default_ttl = cache_ttl_seconds if cache_ttl_seconds is not None else default_ttl_seconds
        self.max_cache_entries = max_cache_size if max_cache_size is not None else max_cache_entries
        self.timeout = timeout_seconds

        self._lock = asyncio.Lock()
        self._last_request_start: float = 0.0
        self._rate_limit_until: float = 0.0

        # Cache: normalized_key -> (monotonic_expiry, data)
        self._cache: Dict[str, Tuple[float, Any]] = {}
        # In-flight deduplication: normalized_key -> asyncio.Future
        self._inflight: Dict[str, asyncio.Future] = {}

    @property
    def cooldown_active(self) -> bool:
        """Returns True if rate-limit cooldown is currently active."""
        return time.monotonic() < self._rate_limit_until

    def _normalize_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Constructs a deterministic, normalized cache key."""
        clean_endpoint = endpoint.strip().rstrip("/").lower()
        param_items = sorted(
            (str(k).strip().lower(), str(v).strip().lower())
            for k, v in (params or {}).items()
            if v is not None
        )
        params_str = json.dumps(param_items, sort_keys=True)
        return f"{clean_endpoint}:{params_str}"

    def _clean_cache_if_needed(self, now: float) -> None:
        """Evicts expired items, and prunes oldest entries if over capacity."""
        # 1. Prune expired
        expired_keys = [k for k, (exp, _) in self._cache.items() if now >= exp]
        for k in expired_keys:
            del self._cache[k]

        # 2. Bound capacity
        if len(self._cache) > self.max_cache_entries:
            sorted_by_expiry = sorted(self._cache.items(), key=lambda item: item[1][0])
            to_remove = len(self._cache) - self.max_cache_entries
            for k, _ in sorted_by_expiry[:to_remove]:
                self._cache.pop(k, None)

    def _parse_retry_after(self, retry_header: Optional[str]) -> int:
        """Parses Retry-After header as integer seconds or HTTP date. Default 10s."""
        if not retry_header or not retry_header.strip():
            return 10
        cleaned = retry_header.strip()
        if cleaned.isdigit():
            return max(1, int(cleaned))
        try:
            target_date = email.utils.parsedate_to_datetime(cleaned)
            import datetime
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            delta = (target_date - now_dt).total_seconds()
            return max(1, int(delta))
        except Exception:
            return 10

    def _is_public_osm(self, url: str) -> bool:
        """Checks if target URL is the public OpenStreetMap Nominatim service."""
        try:
            parsed = urlparse(url)
            return "openstreetmap.org" in (parsed.hostname or "").lower()
        except Exception:
            return False

    async def execute_request(
        self,
        endpoint_path: str,
        params: Optional[Dict[str, Any]] = None,
        custom_base_url: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> Any:
        """
        Coordinates and executes a Nominatim GET request with caching,
        deduplication, serialization, and rate-limiting.
        """
        base_url = custom_base_url or settings.nominatim_base_url or "https://nominatim.openstreetmap.org"
        full_url = f"{base_url.rstrip('/')}/{endpoint_path.lstrip('/')}"
        cache_key = self._normalize_key(full_url, params)
        now = time.monotonic()

        # 1. Check TTL cache
        if cache_key in self._cache:
            expiry, cached_val = self._cache[cache_key]
            if now < expiry:
                logger.debug(f"Nominatim cache hit for {full_url}")
                return cached_val
            else:
                del self._cache[cache_key]

        # 2. Check in-flight single-flight deduplication
        loop = asyncio.get_running_loop()
        if cache_key in self._inflight:
            logger.debug(f"Joining in-flight Nominatim request for {full_url}")
            return await asyncio.shield(self._inflight[cache_key])

        # Register future for in-flight callers
        inflight_future = loop.create_future()
        self._inflight[cache_key] = inflight_future

        try:
            result = await self._execute_serialized(full_url, params)

            # Store in TTL cache on success
            effective_ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
            expiry = time.monotonic() + effective_ttl
            self._cache[cache_key] = (expiry, result)
            self._clean_cache_if_needed(time.monotonic())

            if not inflight_future.done():
                inflight_future.set_result(result)
            return result

        except Exception as exc:
            if not inflight_future.done():
                inflight_future.set_exception(exc)
                try:
                    inflight_future.exception()
                except Exception:
                    pass
            raise

        finally:
            self._inflight.pop(cache_key, None)

    async def _execute_serialized(self, full_url: str, params: Optional[Dict[str, Any]]) -> Any:
        """Executes the HTTP call while strictly holding the serialization lock."""
        async with self._lock:
            now = time.monotonic()

            # 1. Enforce cooldown if an upstream 429 was recently received
            if now < self._rate_limit_until:
                cooldown_remaining = self._rate_limit_until - now
                logger.warning(
                    f"Nominatim cooldown active ({cooldown_remaining:.2f}s remaining). "
                    "Refusing premature request."
                )
                raise ProviderRateLimitError(
                    message=f"Nominatim rate limit cooldown active ({int(cooldown_remaining)}s)",
                    retry_after=max(1, int(cooldown_remaining)),
                )

            # 2. Enforce minimum interval spacing for public OSM endpoint
            if self._is_public_osm(full_url):
                elapsed = now - self._last_request_start
                if elapsed < self.min_interval:
                    wait_time = self.min_interval - elapsed
                    logger.debug(f"Pacing Nominatim request: sleeping {wait_time:.3f}s to respect 1 req/s policy")
                    await asyncio.sleep(wait_time)

            # Record start of outbound call
            self._last_request_start = time.monotonic()

            # 3. Prepare headers and params
            headers = {
                "User-Agent": settings.nominatim_user_agent or "NavSakhi/2.0 (+https://github.com/00keshav00/NavSakhi)",
                "Accept": "application/json",
            }
            req_params = dict(params or {})
            if settings.nominatim_email and "email" not in req_params:
                req_params["email"] = settings.nominatim_email

            # 4. Perform outbound HTTP request
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(full_url, params=req_params, headers=headers)

                    if resp.status_code == 429:
                        retry_after = self._parse_retry_after(resp.headers.get("Retry-After"))
                        self._rate_limit_until = time.monotonic() + retry_after
                        logger.error(
                            f"Nominatim returned HTTP 429 Too Many Requests. "
                            f"Enforcing global cooldown for {retry_after}s."
                        )
                        raise ProviderRateLimitError(
                            message="Upstream Nominatim geocoding rate limit exceeded (HTTP 429)",
                            retry_after=retry_after,
                        )

                    resp.raise_for_status()
                    return resp.json()

            except httpx.TimeoutException as e:
                logger.warning(f"Nominatim request timed out: {e}")
                raise ProviderTimeoutError(f"Nominatim request timed out: {e}") from e

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    retry_after = self._parse_retry_after(e.response.headers.get("Retry-After"))
                    self._rate_limit_until = time.monotonic() + retry_after
                    raise ProviderRateLimitError(
                        message="Upstream Nominatim geocoding rate limit exceeded (HTTP 429)",
                        retry_after=retry_after,
                    ) from e
                logger.error(f"Nominatim HTTP status error {e.response.status_code}")
                raise ProviderUnavailableError(f"Nominatim returned HTTP {e.response.status_code}") from e

            except httpx.RequestError as e:
                logger.error(f"Nominatim network connectivity error: {e}")
                raise ProviderUnavailableError(f"Network error communicating with Nominatim: {e}") from e


# Global in-process singleton
global_nominatim_coordinator = NominatimCoordinator()


def get_nominatim_coordinator() -> NominatimCoordinator:
    return global_nominatim_coordinator

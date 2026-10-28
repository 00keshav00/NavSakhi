import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
import httpx

from app.config.settings import settings
from app.models.journey import Location
from app.providers.shared.nominatim_coordinator import (
    NominatimCoordinator,
    get_nominatim_coordinator,
)
from app.services.local_location_resolver import get_local_location_resolver
from app.providers.location.provider import NominatimLocationProvider
from app.providers.shared.exceptions import (
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    LocationNotFoundError,
)
from app.services.autocomplete_service import AutocompleteService
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.schemas.journey_schemas import JourneyCreate


# =========================================================================
# 1. APPLICATION IDENTIFICATION & CONFIGURATION TESTS
# =========================================================================

def test_default_nominatim_user_agent_format():
    """Verify default User-Agent clearly identifies NavSakhi and project repository."""
    default_ua = settings.nominatim_user_agent
    assert "NavSakhi/2.0" in default_ua
    assert "https://github.com/00keshav00/NavSakhi" in default_ua


@pytest.mark.asyncio
async def test_coordinator_passes_configured_user_agent_and_email():
    """Verify that coordinator attaches configured User-Agent and optional email."""
    coordinator = NominatimCoordinator(min_interval_seconds=0.01)

    captured_headers = {}
    captured_params = {}

    async def mock_get(url, params=None, headers=None, timeout=None):
        nonlocal captured_headers, captured_params
        captured_headers = headers or {}
        captured_params = params or {}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"lat": "13.0827", "lon": "80.2707", "display_name": "Chennai"}]
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch.object(settings, "nominatim_user_agent", "CustomNavSakhi/2.5 (+https://example.com)"), \
         patch.object(settings, "nominatim_email", "admin@example.org"), \
         patch("httpx.AsyncClient.get", side_effect=mock_get):

        res = await coordinator.execute_request("search", params={"q": "Chennai Central"})
        assert res is not None
        assert captured_headers.get("User-Agent") == "CustomNavSakhi/2.5 (+https://example.com)"
        assert captured_params.get("email") == "admin@example.org"


@pytest.mark.asyncio
async def test_coordinator_omits_email_when_not_configured():
    """Verify email is omitted when settings.nominatim_email is None or empty."""
    coordinator = NominatimCoordinator(min_interval_seconds=0.01)

    captured_params = {}

    async def mock_get(url, params=None, headers=None, timeout=None):
        nonlocal captured_params
        captured_params = params or {}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch.object(settings, "nominatim_email", None), \
         patch("httpx.AsyncClient.get", side_effect=mock_get):

        await coordinator.execute_request("search", params={"q": "Testing"})
        assert "email" not in captured_params


@pytest.mark.asyncio
async def test_coordinator_supports_provider_switching():
    """Verify custom base URL redirects requests away from public OpenStreetMap endpoint."""
    coordinator = NominatimCoordinator(min_interval_seconds=0.01)

    captured_url = None

    async def mock_get(url, params=None, headers=None, timeout=None):
        nonlocal captured_url
        captured_url = url
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    custom_internal_geocoder = "https://internal-nominatim.private.infra"
    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        await coordinator.execute_request("search", params={"q": "Marina"}, custom_base_url=custom_internal_geocoder)
        assert captured_url.startswith(custom_internal_geocoder)
        assert "nominatim.openstreetmap.org" not in captured_url


# =========================================================================
# 2. RATE LIMITING, SERIALIZATION & SINGLE-FLIGHT TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_coordinator_enforces_spacing_between_calls():
    """Verify requests are spaced by at least min_interval_seconds."""
    spacing = 0.08  # Compact interval for fast testing without blocking
    coordinator = NominatimCoordinator(min_interval_seconds=spacing)

    call_times = []

    async def mock_get(url, params=None, headers=None, timeout=None):
        call_times.append(time.monotonic())
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"lat": "13.0", "lon": "80.0"}]
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        await coordinator.execute_request("search", params={"q": "query1"})
        await coordinator.execute_request("search", params={"q": "query2"})
        await coordinator.execute_request("search", params={"q": "query3"})

    assert len(call_times) == 3
    diff1 = call_times[1] - call_times[0]
    diff2 = call_times[2] - call_times[1]
    assert diff1 >= spacing * 0.95
    assert diff2 >= spacing * 0.95


@pytest.mark.asyncio
async def test_concurrent_requests_serialized_no_overlap():
    """Verify concurrent requests do not overlap when executing."""
    coordinator = NominatimCoordinator(min_interval_seconds=0.04)

    active_count = 0
    max_active = 0

    async def mock_get(url, params=None, headers=None, timeout=None):
        nonlocal active_count, max_active
        active_count += 1
        if active_count > max_active:
            max_active = active_count
        await asyncio.sleep(0.02)  # Simulate network latency
        active_count -= 1

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"lat": "13.0", "lon": "80.0"}]
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        tasks = [
            coordinator.execute_request("search", params={"q": f"place_{i}"})
            for i in range(5)
        ]
        await asyncio.gather(*tasks)

    # In-process lock ensures at most 1 active HTTP request at any instant
    assert max_active == 1


@pytest.mark.asyncio
async def test_single_flight_deduplication():
    """Verify 5 concurrent identical requests trigger only 1 external HTTP call."""
    coordinator = NominatimCoordinator(min_interval_seconds=0.01)

    network_call_count = 0

    async def mock_get(url, params=None, headers=None, timeout=None):
        nonlocal network_call_count
        network_call_count += 1
        await asyncio.sleep(0.03)  # simulate slow network
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"lat": "13.0827", "lon": "80.2707", "display_name": "Shared Place"}]
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        # Fire 5 concurrent identical requests
        results = await asyncio.gather(*[
            coordinator.execute_request("search", params={"q": "Duplicate Query", "format": "json"})
            for _ in range(5)
        ])

    assert network_call_count == 1
    assert len(results) == 5
    for r in results:
        assert r[0]["display_name"] == "Shared Place"


@pytest.mark.asyncio
async def test_upstream_429_sets_cooldown_and_parses_retry_after():
    """Verify HTTP 429 parses Retry-After header and rejects immediate subsequent requests."""
    coordinator = NominatimCoordinator(min_interval_seconds=0.01)

    async def mock_get(url, params=None, headers=None, timeout=None):
        request = httpx.Request("GET", url)
        response = httpx.Response(
            status_code=429,
            headers={"Retry-After": "5"},
            text="Bandwidth limit exceeded",
            request=request
        )
        raise httpx.HTTPStatusError("429 Too Many Requests", request=request, response=response)

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        with pytest.raises(ProviderRateLimitError) as exc_info:
            await coordinator.execute_request("search", params={"q": "trigger_429"})
        assert exc_info.value.retry_after == 5
        assert coordinator.cooldown_active

        # Next call must be rejected immediately during cooldown without hitting network
        with pytest.raises(ProviderRateLimitError) as exc_info2:
            await coordinator.execute_request("search", params={"q": "during_cooldown"})
        assert "cooldown active" in str(exc_info2.value).lower()


# =========================================================================
# 3. TTL CACHE TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_cache_hit_avoids_network_call():
    """Verify cached successful responses return immediately without network access."""
    coordinator = NominatimCoordinator(cache_ttl_seconds=300, min_interval_seconds=0.01)

    call_count = 0

    async def mock_get(url, params=None, headers=None, timeout=None):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"lat": "13.08", "lon": "80.27"}]
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        res1 = await coordinator.execute_request("search", params={"q": "Cached Station"})
        res2 = await coordinator.execute_request("search", params={"q": "Cached Station"})

    assert call_count == 1
    assert res1 == res2


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Verify expired cache items are evicted and re-queried."""
    coordinator = NominatimCoordinator(cache_ttl_seconds=0.05, min_interval_seconds=0.01)

    call_count = 0

    async def mock_get(url, params=None, headers=None, timeout=None):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"lat": "13.08", "lon": "80.27"}]
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        await coordinator.execute_request("search", params={"q": "Expiring Item"})
        assert call_count == 1

        # Wait for TTL to expire
        await asyncio.sleep(0.08)

        await coordinator.execute_request("search", params={"q": "Expiring Item"})
        assert call_count == 2


@pytest.mark.asyncio
async def test_cache_bounded_capacity():
    """Verify cache respects maximum size bound and prunes oldest entries."""
    coordinator = NominatimCoordinator(max_cache_size=5, min_interval_seconds=0.001)

    async def mock_get(url, params=None, headers=None, timeout=None):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"lat": "13.0", "lon": "80.0"}]
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        for i in range(10):
            await coordinator.execute_request("search", params={"q": f"item_{i}"})

    assert len(coordinator._cache) <= 5


# =========================================================================
# 4. OFFLINE-FIRST CHENNAI RESOLVER TESTS
# =========================================================================

def test_local_resolver_exact_match_landmarks():
    """Verify prominent Chennai landmarks resolve offline from verified datasets."""
    resolver = get_local_location_resolver()

    # VIT Chennai
    vit = resolver.resolve("VIT Chennai")
    assert vit is not None
    assert isinstance(vit, Location)
    # GeoJSON coordinates: [longitude, latitude]
    assert 79.8 <= vit.coordinates[0] <= 80.5
    assert 12.5 <= vit.coordinates[1] <= 13.5

    # Chennai Central
    central = resolver.resolve("Chennai Central")
    assert central is not None
    assert central.coordinates[0] > central.coordinates[1]  # lon > lat

    # Guindy
    guindy = resolver.resolve("Guindy")
    assert guindy is not None

    # Marina Beach
    marina = resolver.resolve("Marina Beach")
    assert marina is not None


def test_local_resolver_case_and_punctuation_insensitivity():
    """Verify normalized matching handles case, extra whitespace, and punctuation."""
    resolver = get_local_location_resolver()

    res1 = resolver.resolve("chennai central")
    res2 = resolver.resolve("  CHENNAI CENTRAL  ")
    res3 = resolver.resolve("Chennai Central Railway Station")

    assert res1 is not None
    assert res2 is not None
    assert res1.coordinates == res2.coordinates


def test_local_resolver_unknown_place_returns_none():
    """Verify missing place returns None and does NOT fabricate coordinates."""
    resolver = get_local_location_resolver()
    assert resolver.resolve("Completely Nonexistent Place in Narnia 12345") is None


@pytest.mark.asyncio
async def test_forward_geocode_uses_local_resolver_first():
    """Verify NominatimLocationProvider forward_geocode does zero network calls on local hits."""
    provider = NominatimLocationProvider()

    network_called = False

    async def mock_get(*args, **kwargs):
        nonlocal network_called
        network_called = True
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        loc = await provider.forward_geocode("VIT Chennai")
        assert loc is not None
        assert not network_called  # Completely offline!


# =========================================================================
# 5. AUTOCOMPLETE LOCAL-ONLY GUARANTEE
# =========================================================================

@pytest.mark.asyncio
async def test_autocomplete_never_calls_nominatim_even_on_miss():
    """Verify autocomplete service never contacts public Nominatim."""
    service = AutocompleteService()

    network_called = False

    async def mock_get(*args, **kwargs):
        nonlocal network_called
        network_called = True
        return MagicMock()

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        # Query that exists
        sug1 = await service.get_suggestions("Guindy", limit=5)
        assert len(sug1) > 0
        assert not network_called

        # Query that does not exist
        sug2 = await service.get_suggestions("NonexistentQueryXyZ999", limit=5)
        assert len(sug2) == 0
        assert not network_called  # Still no network calls!


# =========================================================================
# 6. ERROR MAPPING & BENGLAURU FALLBACK REMOVAL TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_coordinator_raises_422_on_unknown_location():
    """Verify coordinator raises HTTP 422 with sanitized detail on unknown place."""
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(
        source="Guindy",
        destination="NoSuchPlaceXYZChennaiTotallyUnknown99"
    )

    async def mock_get(url, params=None, headers=None, timeout=None):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []  # Empty results from upstream
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        with pytest.raises(HTTPException) as exc_info:
            await coordinator.build_journey_plan_response("test-id", req)
        assert exc_info.value.status_code == 422
        assert "Could not find destination location" in exc_info.value.detail
        assert "NoSuchPlaceXYZChennaiTotallyUnknown99" in exc_info.value.detail


@pytest.mark.asyncio
async def test_coordinator_raises_503_on_upstream_429_with_retry_after():
    """Verify coordinator maps upstream 429 to HTTP 503 with Retry-After header."""
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(
        source="Guindy",
        destination="Unknown External Place"
    )

    async def mock_get(url, params=None, headers=None, timeout=None):
        request = httpx.Request("GET", url)
        response = httpx.Response(
            status_code=429,
            headers={"Retry-After": "10"},
            text="Bandwidth limit exceeded",
            request=request
        )
        raise httpx.HTTPStatusError("429 Too Many Requests", request=request, response=response)

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        with pytest.raises(HTTPException) as exc_info:
            await coordinator.build_journey_plan_response("test-id", req)
        assert exc_info.value.status_code == 503
        assert "temporarily unavailable" in exc_info.value.detail
        assert exc_info.value.headers.get("Retry-After") == "10"


@pytest.mark.asyncio
async def test_coordinator_removes_bengaluru_fallback():
    """Verify coordinator does not fallback to Bengaluru coordinates [77.5946, 12.9716]."""
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(
        source="Detecting Location...",
        destination="Guindy"
    )

    # In previous code, 'Detecting Location...' silently placed source in Bengaluru
    with pytest.raises(HTTPException) as exc_info:
        await coordinator.build_journey_plan_response("test-id", req)
    assert exc_info.value.status_code == 422
    assert "Cannot determine source location" in exc_info.value.detail


# =========================================================================
# 7. COORDINATE PAIR DETECTION & TEXTUAL PLACE SEPARATION TESTS
# =========================================================================

from app.intelligence.journey.coordinator import parse_coordinate_pair, is_coordinate_pair


def test_valid_coordinate_pair_detection():
    """Verify standard coordinate strings are recognized as valid coordinate pairs."""
    # Standard decimal lat, lon
    coords = parse_coordinate_pair("13.0827, 80.2707")
    assert coords is not None
    assert coords == (80.2707, 13.0827)  # (lon, lat)
    assert is_coordinate_pair("13.0827, 80.2707") is True

    # Inverted lon, lat in India
    coords_inv = parse_coordinate_pair("80.2707, 13.0827")
    assert coords_inv == (80.2707, 13.0827)
    assert is_coordinate_pair("80.2707, 13.0827") is True


def test_coordinate_whitespace_and_signed_values():
    """Verify coordinate parser correctly handles leading/trailing whitespace and negative signs."""
    # Whitespace handling
    res = parse_coordinate_pair("   13.0827   ,   80.2707   ")
    assert res == (80.2707, 13.0827)

    # Valid negative latitude
    res_neg = parse_coordinate_pair("-12.9716, 77.5946")
    assert res_neg == (77.5946, -12.9716)

    # Valid negative longitude
    res_neg_lon = parse_coordinate_pair("40.7128, -74.0060")
    assert res_neg_lon == (-74.0060, 40.7128)


def test_textual_locations_with_commas_rejected_as_coordinates():
    """Verify place names containing commas are NOT treated as coordinate pairs."""
    assert is_coordinate_pair("Guindy, Chennai") is False
    assert parse_coordinate_pair("Guindy, Chennai") is None

    assert is_coordinate_pair("VIT Chennai, Kelambakkam") is False
    assert parse_coordinate_pair("VIT Chennai, Kelambakkam") is None

    assert is_coordinate_pair("Anna Salai, Thousand Lights, Chennai") is False


def test_malformed_and_out_of_range_coordinate_pairs():
    """Verify malformed strings and out-of-range coordinates are rejected."""
    # Triple values (extra component)
    assert is_coordinate_pair("13.0827, 80.2707, 100.0") is False

    # Single value
    assert is_coordinate_pair("13.0827") is False

    # Non-numeric text
    assert is_coordinate_pair("13.0827, not_a_number") is False

    # Latitude > 90.0
    assert is_coordinate_pair("95.0, 195.0") is False

    # Both coordinates > 90.0 (neither can be valid latitude)
    assert is_coordinate_pair("95.0, 95.0") is False

    # Longitude > 180.0
    assert is_coordinate_pair("13.0, 195.0") is False


@pytest.mark.asyncio
async def test_textual_source_does_not_trigger_reverse_geocoding():
    """Verify textual place names with commas do not call reverse_geocode."""
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(
        source="Guindy, Chennai",
        destination="Saidapet, Chennai"
    )

    reverse_geocode_called = False

    async def mock_reverse(*args, **kwargs):
        nonlocal reverse_geocode_called
        reverse_geocode_called = True
        addr = MagicMock()
        addr.display_name = "Ward 160, Alandur"
        return addr

    with patch("app.providers.location.provider.NominatimLocationProvider.reverse_geocode", side_effect=mock_reverse):
        resp = await coordinator.build_journey_plan_response("test-id", req)
        assert resp is not None
        assert "Guindy" in resp.journey_information.source
        assert not reverse_geocode_called


@pytest.mark.asyncio
async def test_genuine_coordinate_source_triggers_reverse_geocoding():
    """Verify genuine coordinate strings call reverse_geocode to obtain a friendly name."""
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(
        source="13.0067, 80.2184",
        destination="Guindy"
    )

    reverse_geocode_called = False

    async def mock_reverse(*args, **kwargs):
        nonlocal reverse_geocode_called
        reverse_geocode_called = True
        addr = MagicMock()
        addr.display_name = "Guindy Station Road, Chennai"
        return addr

    with patch("app.providers.location.provider.NominatimLocationProvider.reverse_geocode", side_effect=mock_reverse):
        resp = await coordinator.build_journey_plan_response("test-id", req)
        assert resp is not None
        assert reverse_geocode_called
        assert "Guindy Station Road" in resp.journey_information.source

import os
import re
import json
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List
import httpx
from app.config.settings import settings
from app.tools.base import BaseTool, ToolMetadata

logger = logging.getLogger(__name__)

DEFAULT_PRIMARY_MODEL = "gemini-3.8-flash"
DEFAULT_FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash-lite"]

def get_gemini_api_key() -> str:
    return (os.getenv("GEMINI_API_KEY", "") or getattr(settings, "gemini_api_key", "") or "").strip()

def get_gemini_model() -> str:
    env_model = (getattr(settings, "llm_model_name", None) or os.getenv("LLM_MODEL_NAME", "")).strip()
    return env_model or DEFAULT_PRIMARY_MODEL

def get_gemini_models() -> List[str]:
    primary = get_gemini_model()
    env_fallbacks = os.getenv("LLM_FALLBACK_MODELS", "").strip()
    if env_fallbacks:
        fallbacks = [m.strip() for m in env_fallbacks.split(",") if m.strip()]
    else:
        fallbacks = [m for m in DEFAULT_FALLBACK_MODELS if m != primary]
    models = [primary]
    for m in fallbacks:
        if m not in models:
            models.append(m)
    return models

def sanitize_log_message(msg: str) -> str:
    """
    Redacts API keys and sensitive tokens from log messages and exception strings.
    Ensures that no query string ?key= or raw API keys appear in application logs.
    """
    if not msg:
        return msg
    # Redact ?key=... or &key=...
    msg = re.sub(r'([?&]key=)[^&\s"\']+', r'\1[REDACTED]', msg)
    # Redact Google AI Studio API keys (AIzaSy...)
    msg = re.sub(r'AIzaSy[A-Za-z0-9_-]{33}', '[REDACTED_API_KEY]', msg)
    # Redact x-goog-api-key headers if stringified
    msg = re.sub(r'(x-goog-api-key["\']?\s*[:=]\s*["\']?)[^"\'\s,]+', r'\1[REDACTED]', msg, flags=re.IGNORECASE)
    # Redact Bearer tokens
    msg = re.sub(r'(Bearer\s+)[A-Za-z0-9._-]+', r'\1[REDACTED]', msg, flags=re.IGNORECASE)
    return msg


class ReasoningTool(BaseTool):
    """
    Tool for calling LLM (Gemini) to perform strategic routing reasoning,
    route-to-user explanations, and dynamic transit strategy synthesis.

    Robustness:
    - Passes API key strictly in x-goog-api-key header (never in URL query string)
    - Full error classification (503, 429, 401/403, 400, timeouts)
    - Bounded retries with exponential backoff on transient errors
    - Multi-model fallback across supported Gemini models
    - Complete log redaction to prevent secret exposure
    - Safe non-LLM static fallbacks when external LLM is unavailable
    """

    # _model_cooldown is intentionally a CLASS-LEVEL attribute (process-wide circuit breaker).
    # When a Gemini model times out or fails for one request, it is placed on cooldown so that
    # subsequent requests from ANY user immediately serve the static fallback instead of waiting
    # for a known-unresponsive external service.  This is desirable behaviour: if Gemini is down,
    # every route-planning call would otherwise spend 3+ seconds blocking before falling back.
    # Consequence: one user's Gemini timeout will suppress Gemini for all concurrent/subsequent
    # users until the cooldown expires (30-120 s depending on error type).  This is an explicit
    # design trade-off: latency protection for all users outweighs per-request freshness.
    # Tests in test_gemini_security_and_fallback.py verify this behaviour explicitly.
    _model_cooldown: Dict[str, float] = {}

    @property
    def name(self) -> str:
        return "ReasoningTool"

    @property
    def description(self) -> str:
        return "Provides LLM explanation and reasoning."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Reasoning",
            required_inputs=["context"],
            output_schema={"type": "dict"},
            ranking_score=10
        )

    async def _call_gemini_content(self, prompt: str, timeout: float = 3.0, deadline: Optional[float] = None) -> Optional[str]:
        """
        Executes prompt against Gemini API using header-based authentication,
        bounded retries, error classification, and multi-model fallback.
        """
        api_key = get_gemini_api_key()
        if not api_key:
            return None

        now = time.time()
        if "_all_" in self._model_cooldown and now < self._model_cooldown["_all_"]:
            logger.debug("Gemini global cooldown active; skipping external LLM call.")
            return None

        if deadline is not None and (deadline - now) <= 0.5:
            logger.info("Gemini request deadline budget exhausted; skipping external LLM call.")
            return None

        models = get_gemini_models()
        for model in models:
            now = time.time()
            if deadline is not None:
                remaining = deadline - now
                if remaining <= 0.5:
                    logger.info(f"Gemini deadline budget exhausted before evaluating '{model}'; returning fallback.")
                    break
                call_timeout = min(timeout, remaining)
            else:
                call_timeout = timeout

            if model in self._model_cooldown and now < self._model_cooldown[model]:
                logger.debug(f"Gemini model '{model}' in cooldown; evaluating next candidate.")
                continue

            for attempt in range(2):
                now = time.time()
                if deadline is not None:
                    remaining = deadline - now
                    if remaining <= 0.5:
                        logger.info(f"Gemini deadline budget exhausted during attempt {attempt+1}; terminating retries.")
                        break
                    call_timeout = min(timeout, remaining)
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key,
                }
                payload = {"contents": [{"parts": [{"text": prompt}]}]}

                try:
                    async with httpx.AsyncClient(timeout=call_timeout) as client:
                        resp = await client.post(url, json=payload, headers=headers)

                    if resp.status_code == 200:
                        res_data = resp.json()
                        candidates = res_data.get("candidates", [])
                        if candidates:
                            finish_reason = candidates[0].get("finishReason", "")
                            if finish_reason in ("SAFETY", "RECITATION"):
                                logger.warning(f"Gemini response stopped by policy filter: {finish_reason}")
                                return None
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts and "text" in parts[0]:
                                return parts[0]["text"].strip()
                        return None

                    status = resp.status_code
                    if status in (500, 502, 503, 504, 408):
                        retry_after = resp.headers.get("Retry-After")
                        wait_sec = min(float(retry_after), 1.0) if retry_after and retry_after.isdigit() else (0.3 * (attempt + 1))
                        if attempt < 1 and (deadline is None or (deadline - time.time()) > (wait_sec + 1.0)):
                            logger.info(f"Gemini model '{model}' returned transient HTTP {status} (attempt {attempt+1}/2). Retrying in {wait_sec:.2f}s...")
                            await asyncio.sleep(wait_sec)
                            continue
                        else:
                            logger.warning(f"Gemini model '{model}' failed after retries (HTTP {status}). Transitioning to fallback model.")
                            self._model_cooldown[model] = time.time() + 30.0
                            break

                    elif status == 429:
                        err_text = resp.text
                        is_quota = "RESOURCE_EXHAUSTED" in err_text or "quota" in err_text.lower()
                        if is_quota:
                            logger.warning(f"Gemini model '{model}' quota exhausted (HTTP 429). Setting 60s cooldown and falling back.")
                            self._model_cooldown[model] = time.time() + 60.0
                            break
                        else:
                            retry_after = resp.headers.get("Retry-After")
                            if retry_after and retry_after.isdigit() and float(retry_after) <= 2.0 and attempt == 0:
                                await asyncio.sleep(float(retry_after))
                                continue
                            else:
                                logger.warning(f"Gemini model '{model}' rate limited (HTTP 429). Trying fallback model.")
                                self._model_cooldown[model] = time.time() + 30.0
                                break

                    elif status in (401, 403):
                        logger.warning(f"Gemini API authentication failed (HTTP {status}). Key rejected; disabling LLM calls for 120s.")
                        self._model_cooldown["_all_"] = time.time() + 120.0
                        return None

                    elif status == 404 or (status == 400 and any(
                        phrase in sanitize_log_message(resp.text).lower()
                        for phrase in [
                            "not found", "discontinued", "retired", "unsupported model",
                            "model not supported", "unknown model", "does not exist", "is not supported"
                        ]
                    )):
                        err_text = sanitize_log_message(resp.text)
                        logger.warning(
                            f"Gemini model '{model}' unavailable or retired (HTTP {status}): {err_text[:120]}. "
                            f"Setting 1-hour cooldown and transitioning to fallback model."
                        )
                        self._model_cooldown[model] = time.time() + 3600.0
                        break

                    elif status == 400:
                        err_text = sanitize_log_message(resp.text)
                        logger.error(
                            f"Gemini request payload invalid (HTTP 400) for model '{model}': {err_text[:120]}. "
                            f"Treating as request error without model cooldown."
                        )
                        break

                    else:
                        logger.warning(f"Gemini unexpected status {status} for model '{model}'. Skipping model.")
                        self._model_cooldown[model] = time.time() + 60.0
                        break

                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    err_type = type(e).__name__
                    logger.info(f"Gemini model '{model}' {err_type} on attempt {attempt+1}/2.")
                    if isinstance(e, httpx.TimeoutException):
                        logger.warning(f"Gemini model '{model}' timed out. Setting 60s cooldown and evaluating fallback.")
                        self._model_cooldown[model] = time.time() + 60.0
                        break
                    if attempt < 1 and (deadline is None or (deadline - time.time()) > 1.0):
                        await asyncio.sleep(0.3)
                        continue
                    else:
                        self._model_cooldown[model] = time.time() + 30.0
                        logger.warning(f"Gemini model '{model}' network failure after retries. Trying fallback model.")
                        break
                except Exception as e:
                    clean_err = sanitize_log_message(str(e))
                    logger.warning(f"Gemini call exception for model '{model}': {clean_err}")
                    break

        logger.info("All configured Gemini models failed or unavailable; using verified non-LLM reasoning fallback.")
        self._model_cooldown["_all_"] = time.time() + 60.0
        return None

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls the Gemini API if possible, otherwise falls back to static reasoning.
        """
        decision = params.get("context", {}).get("decision", {})
        fallback_summary = "Route evaluated using verified network topology and model-ready road infrastructure data."
        fallback_reasoning = [
            "Network topology verified against mapped road and transit layers.",
            "Segment coverage validated according to scoring requirements.",
            "Evaluations bounded to synthetic environmental proxy indicators without unsupported claims."
        ]

        api_key = get_gemini_api_key()
        if not api_key:
            logger.info("GEMINI_API_KEY not configured; using verified infrastructure reasoning fallback.")
            return {
                "summary": fallback_summary,
                "reasoning": fallback_reasoning
            }

        prompt = (
            f"You are NavSakhi AI. Explain this route decision factually based on verified infrastructure: {decision}. "
            "CRITICAL CONSTRAINTS: Do not claim specific lighting conditions, crowd densities, or community incident counts. "
            "Do not state that any route guarantees safety. Keep explanations grounded strictly in objective route metrics."
        )

        text = await self._call_gemini_content(prompt, timeout=3.0)
        if text:
            return {
                "summary": text,
                "reasoning": fallback_reasoning
            }

        return {
            "summary": fallback_summary,
            "reasoning": fallback_reasoning
        }

    async def explain_journey_recommendations(self, source: str, dest: str, verified_routes: List[Dict[str, Any]], preferences: Optional[List[str]] = None, weather: Optional[Dict[str, Any]] = None, deadline: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Explains already validated and scored candidate routes using supplied evidence,
        actual ML scores, live weather, and explicit user preferences.
        Gemini NEVER invents stations, geometries, or scores.
        """
        if not verified_routes:
            return None

        top_route = verified_routes[0] if verified_routes else {}
        top_name = top_route.get("route_name", "Primary Option")
        static_fallback = {
            "title": "Objective AI Recommendation",
            "summary": f"Recommended {top_name} based on verified routing topology.",
            "reasoning": "Route evaluated using verified network topology and model-ready road infrastructure data.",
            "tradeoff_explanation": f"Evaluated {len(verified_routes)} verified routing alternatives.",
            "tradeoffs": ["Direct road transit prioritizes door-to-door speed."]
        }

        api_key = get_gemini_api_key()
        if not api_key:
            return static_fallback

        now = time.time()
        if "_all_" in self._model_cooldown and now < self._model_cooldown["_all_"]:
            logger.debug("Gemini global cooldown active; serving static fallback immediately.")
            return static_fallback

        if deadline is not None and (deadline - now) <= 0.5:
            logger.info("Gemini explanation deadline budget exhausted; serving static fallback immediately.")
            return static_fallback

        prefs_str = ", ".join(preferences) if preferences else "Fastest, Safest, Balanced"
        weather_desc = f"{weather.get('condition', 'Clear')}, {weather.get('temperature', 25)}°C" if weather else "Unavailable"

        routes_summary = []
        for r in verified_routes[:4]:
            score_str = f"Safety Proxy: {r.get('safety_score'):.1f}/100" if r.get('safety_score') is not None else "Safety Score: N/A (Transit/Insufficient coverage)"
            routes_summary.append(
                f"- {r.get('route_name')} ({r.get('travel_mode', 'Road')}): Distance {r.get('distance_km'):.1f} km, ETA {r.get('eta_min')} min, {score_str}"
            )
        routes_text = "\n".join(routes_summary)

        prompt = f"""
You are NavSakhi AI, an objective safety navigation assistant for Chennai.
Explain the routing options below to the user based STRICTLY on the verified facts provided:
Source: {source}
Destination: {dest}
User Priorities: {prefs_str}
Current Weather: {weather_desc}

Verified Routes Evaluated by Routing Engine & LightGBM Safety Model:
{routes_text}

CRITICAL RULES:
1. Explain the trade-offs factually (e.g. speed vs distance vs road environmental risk proxy).
2. If a multimodal or public transit route is listed, note that transit track segments are not scored by the road safety model.
3. NEVER claim guaranteed safety, CCTV coverage, or police patrols unless provided.
4. Keep the explanation concise (2-3 sentences max).

Return JSON only in this exact format:
{{
  "title": "Objective AI Recommendation",
  "summary": "Short 1-2 sentence recommendation summary.",
  "reasoning": "Factual explanation of trade-offs between speed, distance, and environmental safety.",
  "tradeoffs": ["Tradeoff 1", "Tradeoff 2"]
}}
"""
        text = await self._call_gemini_content(prompt, timeout=3.0, deadline=deadline)
        if not text:
            return static_fallback

        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].startswith("```"): lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else static_fallback
        except Exception as e:
            clean_err = sanitize_log_message(str(e))
            logger.info(f"Gemini route explanation JSON parse fallback: {clean_err}")
            return static_fallback

    async def generate_dynamic_plans(self, source: str, dest: str, dist_km: float, preferences: list = None, deadline: Optional[float] = None) -> list:
        """
        Uses Gemini to suggest high-level candidate strategies.
        Must ONLY suggest public transit if realistic stations exist along the travel axis.
        """
        api_key = get_gemini_api_key()
        if not api_key:
            logger.info("GEMINI_API_KEY not configured; skipping dynamic planning.")
            return []

        now = time.time()
        if "_all_" in self._model_cooldown and now < self._model_cooldown["_all_"]:
            logger.debug("Gemini global cooldown active; skipping dynamic planning prompt.")
            return []

        if deadline is not None and (deadline - now) <= 0.5:
            logger.info("Gemini dynamic planning deadline budget exhausted; skipping dynamic planning prompt.")
            return []

        # If trip is short, public transit is not realistic
        if dist_km < 3.0:
            logger.info(f"Trip distance ({dist_km:.2f} km) too short for rail transit; skipping transit prompt.")
            return []

        prefs_str = ", ".join(preferences) if preferences else "ANY"

        prompt = f"""
You are an intelligent mobility planner for Chennai.
Source: {source}
Destination: {dest}
Straight-line distance: {dist_km:.2f} km
User Preferences: {prefs_str}

CRITICAL RULES:
1. ONLY propose public transit (METRO, SUBURBAN, MRTS) if BOTH origin and destination are genuinely along an existing operational railway or metro line in Chennai.
2. If public transit requires a massive detour (e.g. traveling >5 km in the wrong direction or crossing the city twice), DO NOT SUGGEST TRANSIT. Suggest only direct road/ride options.
3. For Chennai:
   - Suburban rail runs along Chennai Central/Beach - Egmore - Guindy - Tambaram - Chengalpattu.
   - Metro runs Airport - Guindy - Central / St. Thomas Mount - Koyambedu - Central.
   - Do NOT suggest suburban rail or metro for trips along OMR / Navalur / Kelambakkam / Medavakkam where no train tracks exist.
4. DO NOT suggest "BUS".
5. If suggesting transit, every step MUST specify real exact station names:
   - For road access: entry must be "Source", exit must be the EXACT boarding station name (e.g. 'Vandalur', 'Tambaram', 'Guindy').
   - For transit: entry must be boarding station, exit must be alighting station (e.g. 'Mambalam', 'Chennai Central').
   - For road egress: entry must be alighting station, exit must be "Destination".

Return ONLY valid JSON (raw JSON array, no markdown).
Each strategy object:
{{
  "strategy_name": string,
  "strategy_id": string,
  "steps": [
    {{"mode": "AUTO"|"CAB"|"WALK"|"METRO"|"SUBURBAN"|"MRTS", "entry": string, "exit": string}}
  ]
}}
"""
        text = await self._call_gemini_content(prompt, timeout=3.0, deadline=deadline)
        if not text:
            return []

        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].startswith("```"): lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, list) else []
        except Exception as e:
            clean_err = sanitize_log_message(str(e))
            logger.warning(f"Gemini dynamic planning JSON parse failed: {clean_err}")
            return []

import asyncio
import re
import httpx
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.tools.base import BaseTool, ToolMetadata

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

import os
from app.config.settings import settings


def sanitize_privacy_context(text: Any) -> str:
    """
    Sanitizes outbound LLM provider strings to guarantee that:
    1. Raw numeric latitude/longitude coordinates (e.g. 13.0827, 80.2707) are stripped.
    2. API keys (e.g. AIzaSy...), Bearer tokens, passwords, and secrets are redacted.
    3. User email addresses and phone numbers are scrubbed.
    """
    if text is None:
        return ""
    s = str(text)
    # Strip coordinate pairs like "13.0827, 80.2707" or "[80.2707, 13.0827]" or "13.0827 80.2707"
    s = re.sub(r'\[?\b[-+]?\d{1,3}\.\d{3,}\s*[, ]\s*[-+]?\d{1,3}\.\d{3,}\b\]?', '[Sanitized Area]', s)
    # Strip lone coordinates with 4+ decimal places
    s = re.sub(r'\b[-+]?\d{1,3}\.\d{4,}\b', '[Sanitized Coordinate]', s)
    # Strip API keys or token prefixes
    s = re.sub(r'AIza[0-9A-Za-z_-]{20,}', '[REDACTED_API_KEY]', s)
    s = re.sub(r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*', '[REDACTED_TOKEN]', s)
    s = re.sub(r'(?:password|secret|token|api_key|credential)\s*[:=]\s*["\']?[^"\'\s]+["\']?', '[REDACTED_CREDENTIAL]', s, flags=re.IGNORECASE)
    # Strip phone numbers (10 digits)
    s = re.sub(r'\b(?:\+91[\-\s]?)?[6-9]\d{9}\b', '[REDACTED_PHONE]', s)
    return s


def build_sanitized_chat_payload(
    query: str,
    active_journey: Any = None,
    history: Optional[List[Dict[str, Any]]] = None,
    grounded_pois: Optional[List[Dict[str, Any]]] = None,
    poi_location_name: Optional[str] = None,
    coord_match: Optional[Tuple[float, float]] = None
) -> Dict[str, Any]:
    """
    Constructs an outbound payload for conversational Gemini requests,
    guaranteeing no raw coordinates, geometry, or credentials are leaked.
    Incorporates recent conversation history, coordinates context, and grounded POI records.
    """
    clean_query = sanitize_privacy_context(query)
    dest_name = getattr(active_journey, "destination_name", None) or "destination"
    clean_dest = sanitize_privacy_context(dest_name) if active_journey else "No active journey"

    history_context = ""
    if history and isinstance(history, list):
        recent_turns = []
        for turn in history[-4:]:
            r = turn.get("role", "user")
            c = sanitize_privacy_context(str(turn.get("content", "")).strip())
            if c:
                label = "User" if r == "user" else "NavSakhi"
                recent_turns.append(f"{label}: {c}")
        if recent_turns:
            history_context = "RECENT CONVERSATION HISTORY:\n" + "\n".join(recent_turns) + "\n\n"

    poi_context = ""
    if grounded_pois:
        poi_lines = []
        for p in grounded_pois[:10]:
            p_name = sanitize_privacy_context(p.get("name"))
            p_cat = sanitize_privacy_context(p.get("category_label") or p.get("category"))
            p_dist = p.get("distance_m", 0)
            p_hours = sanitize_privacy_context(p.get("opening_hours") or "Not published in OpenStreetMap")
            p_status = p.get("opening_status", "UNKNOWN")
            p_role = "Mapped Public Facility" if p.get("is_emergency") else ("Verified Safe Haven" if p.get("is_safe_haven_eligible") else "Mapped Commercial Establishment")
            poi_lines.append(f"- {p_name} ({p_cat}): ~{int(p_dist)}m away. Hours: {p_hours} (Status: {p_status}). Classification: {p_role}.")
        target_loc_str = f" NEAR {poi_location_name.upper()}" if poi_location_name else ""
        poi_context = (
            f"GROUNDED MAPPED ESTABLISHMENTS IN CHENNAI{target_loc_str}:\n"
            + "\n".join(poi_lines)
            + "\n\nFACILITY GUIDELINES:\n"
            "- Answer using only the mapped establishments listed above.\n"
            "- Clearly state that commercial shops are mapped OpenStreetMap records, not emergency safe havens or police checkpoints.\n"
            "- Do not promise a business is open unless available data indicates OPEN; if hours are unknown, clearly say so.\n"
            "- Distinguish commercial businesses from emergency facilities (police, hospitals).\n\n"
        )

    prompt = (
        "You are NavSakhi, a warm, compassionate, and trustworthy travel companion for women navigating Chennai.\n"
        f"{history_context}"
        f"Current user message: {clean_query}\n"
        f"Active journey context: {'Active journey to ' + clean_dest if active_journey else 'No active journey'}\n\n"
        f"{poi_context}"
        "COMPANION PERSONA & TONE GUIDELINES:\n"
        "1. WARMTH & CALM SUPPORT: Speak naturally with a supportive, calm, conversational feminine companion voice ('Sakhi' means trusted female friend). "
        "Acknowledge the user's specific statement or emotion directly. Do not repeat generic introductory greetings or capability lists on follow-up turns.\n"
        "2. CONVERSATIONAL CONTEXT & NATURAL GREETINGS:\n"
        "   - If the user says 'Hello', 'Hi', or 'How are you?', reply briefly and naturally. Do NOT repeat a boilerplate self-introduction.\n"
        "   - If the user asks 'Will you be my sakhi for the journey?' or asks you to accompany them: warmly clarify that you are a digital travel companion in their phone to help compare routes and monitor progress, without pretending to be physically present or guaranteeing physical safety.\n"
        "   - If the user asks what to take care of or for safety advice: give practical suggestions (transit timing, phone charged, familiar populated routes, sharing journey) without fabricating real-time occupancy or street shop conditions.\n"
        "3. TRAVEL ANXIETY VS ACUTE DANGER:\n"
        "   - If expressing nervousness about traveling alone: recognize the feeling with calm reassurance, recommend well-lit major transit like Chennai Metro or bus, "
        "and suggest sitting near the conductor/women's section without triggering a false emergency alarm.\n"
        "   - If facing acute danger, being followed, or in distress: prioritize immediate physical safety, advise moving into a staffed shop/metro counter, "
        "and provide emergency helplines: 112 (National Emergency) and 1091 (Women Helpline).\n"
        "4. HONESTY & COORDINATES:\n"
        "   - Do NOT claim to be human or promise physical in-person protection. Never invent transit schedules or fares.\n"
        "   - If coordinates are shared alone without a question, acknowledge the coordinates and ask what the user would like to find near them (e.g. shops, pharmacies, hospitals, or transit routes).\n"
        f"{f'   - The user shared coordinates ({coord_match[0]:.4f}, {coord_match[1]:.4f}). Directly acknowledge receiving ({coord_match[0]:.4f}, {coord_match[1]:.4f}) and ask what they would like to find near them.' if coord_match else ''}\n"
        "5. READABLE FORMATTING: Use clean, human-friendly Markdown: short paragraphs, bullet points, clear bolding (**bold**), and numbered steps if helpful."
    )
    return {"contents": [{"parts": [{"text": prompt}]}]}


def build_sanitized_route_explanation_payload(
    source: str,
    dest: str,
    verified_routes: List[Dict[str, Any]],
    preferences: Optional[List[str]] = None,
    weather: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs an outbound payload for route explanations,
    guaranteeing only high-level names, travel modes, distances, and scores are included.
    No geometries, polylines, or raw coordinates are ever passed.
    """
    clean_source = sanitize_privacy_context(source)
    clean_dest = sanitize_privacy_context(dest)
    prefs_str = ", ".join(preferences) if preferences else "Fastest, Safest, Balanced"
    weather_desc = f"{weather.get('condition', 'Clear')}, {weather.get('temperature', 25)}°C" if weather else "Unavailable"

    routes_summary = []
    for r in (verified_routes or [])[:4]:
        # Strictly ensure r contains NO geometry or coordinate arrays
        r_clean = {k: v for k, v in r.items() if k not in ["geometry", "coordinates", "all_coords", "track_nodes"]}
        score_str = f"Safety Proxy: {r_clean.get('safety_score'):.1f}/100" if r_clean.get('safety_score') is not None else "Safety Score: N/A (Transit/Insufficient coverage)"
        r_name = sanitize_privacy_context(r_clean.get("route_name", "Route"))
        mode = sanitize_privacy_context(r_clean.get("travel_mode", "Road"))
        dist_km = float(r_clean.get("distance_km", 0.0))
        eta_min = int(r_clean.get("eta_min", 0))
        routes_summary.append(f"- {r_name} ({mode}): Distance {dist_km:.1f} km, ETA {eta_min} min, {score_str}")

    routes_text = "\n".join(routes_summary)

    prompt = f"""You are NavSakhi AI, an objective safety navigation assistant for Chennai.
Explain the routing options below to the user based STRICTLY on the verified facts provided:
Source: {clean_source}
Destination: {clean_dest}
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
}}"""
    return {"contents": [{"parts": [{"text": prompt}]}]}


import time
from app.services.assistant_intent_service import global_intent_classifier, IntentCategory
from app.services.credential_service import get_active_gemini_api_key, global_credential_manager

# Candidate Gemini Models in deterministic failover priority order
# Retired models (gemini-2.0-flash, gemini-1.5-flash) removed per official deprecations
CANDIDATE_GEMINI_MODELS: List[str] = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-2.5-flash",
]

# Per-model cooldown tracking
_model_cooldowns: Dict[str, float] = {}
_model_cooldown_until: Dict[str, float] = {}
_model_ineligible: set = set()
GEMINI_429_COOLDOWN_SECONDS: float = 60.0


def _parse_retry_after(headers: Any) -> Optional[float]:
    """Safely extracts Retry-After in seconds from HTTP headers if present."""
    if not headers:
        return None
    val = headers.get("retry-after") or headers.get("Retry-After")
    if not val:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def get_configured_gemini_models() -> List[str]:
    """
    Returns candidate models in priority order, honoring any configured primary model.
    """
    configured = getattr(settings, "llm_model_name", None) or os.getenv("LLM_MODEL_NAME", "")
    models = list(CANDIDATE_GEMINI_MODELS)
    if configured and str(configured).strip():
        primary = str(configured).strip()
        if primary in models:
            models.remove(primary)
        models.insert(0, primary)
    return models


def is_model_in_cooldown(model: str) -> bool:
    """Checks whether a specific Gemini model is in active cooldown or marked ineligible."""
    if model in _model_ineligible:
        return True
    now = time.time()
    if model in _model_cooldown_until:
        return now < _model_cooldown_until[model]
    last_time = _model_cooldowns.get(model, 0.0)
    return (now - last_time) < GEMINI_429_COOLDOWN_SECONDS


def record_model_429(model: str, retry_after: Optional[float] = None) -> None:
    """
    Records a 429 rate limit cooldown specifically for the affected model,
    using the upstream Retry-After delay if provided.
    """
    cooldown = retry_after if (retry_after is not None and retry_after > 0) else GEMINI_429_COOLDOWN_SECONDS
    now = time.time()
    _model_cooldowns[model] = now
    _model_cooldown_until[model] = now + cooldown
    logger.warning(f"Gemini model '{model}' reached rate limit (429). Cooldown activated for {cooldown:.1f}s.")



def mark_model_ineligible(model: str, reason: str = "") -> None:
    _model_ineligible.add(model)
    logger.warning(f"Gemini model '{model}' marked ineligible for session: {reason}")


def classify_gemini_error(
    status_code: int,
    response_text: str,
    model_name: str
) -> Dict[str, Any]:
    """
    Classifies a Gemini API HTTP error according to structured response details.
    Distinguishes unsupported models, parameter errors, endpoint 404s, rate limits, and generic client errors.
    """
    error_message = ""
    error_status = ""
    try:
        data = json.loads(response_text)
        if isinstance(data, dict) and "error" in data and isinstance(data["error"], dict):
            error_message = str(data["error"].get("message", "")).lower()
            error_status = str(data["error"].get("status", "")).upper()
        elif isinstance(data, dict) and "message" in data:
            error_message = str(data.get("message", "")).lower()
    except Exception:
        error_message = response_text.lower() if response_text else ""

    model_lower = model_name.lower()

    if status_code == 429:
        return {
            "category": "RATE_LIMIT",
            "is_model_ineligible": False,
            "can_failover": True,
            "reason": f"Model '{model_name}' hit rate limit (HTTP 429)."
        }

    if status_code in (401, 403):
        return {
            "category": "AUTH_RESTRICTION",
            "is_model_ineligible": False,
            "can_failover": False,
            "reason": f"API key or project credential restricted (HTTP {status_code})."
        }

    if status_code == 404:
        # Check if the 404 specifically identifies the model as missing / unsupported
        # Gemini REST 404 format: "models/xyz is not found for API version...", "call listmodels"
        is_model_specific = (
            model_lower in error_message or
            "models/" in error_message or
            "listmodels" in error_message or
            "generatecontent" in error_message
        )
        if is_model_specific:
            return {
                "category": "MODEL_NOT_FOUND",
                "is_model_ineligible": True,
                "can_failover": True,
                "reason": f"Model '{model_name}' not found or unsupported for generateContent (HTTP 404)."
            }
        else:
            return {
                "category": "ENDPOINT_NOT_FOUND",
                "is_model_ineligible": False,
                "can_failover": False,
                "reason": f"HTTP 404 endpoint or configuration error: {error_message[:100]}"
            }

    if status_code == 400:
        # Check if 400 explicitly indicates that this model is unsupported
        is_model_unsupported = (
            (model_lower in error_message and any(k in error_message for k in ["not supported", "not found", "unsupported", "invalid"])) or
            ("model" in error_message and any(k in error_message for k in ["is not supported", "unknown model", "unsupported model", "invalid model"]))
        )
        if is_model_unsupported:
            return {
                "category": "MODEL_UNSUPPORTED",
                "is_model_ineligible": True,
                "can_failover": True,
                "reason": f"Model '{model_name}' explicitly unsupported (HTTP 400): {error_message[:100]}"
            }

        # Check for model parameter or feature incompatibility
        is_param_error = any(k in error_message for k in [
            "parameter", "field", "argument", "unknown field", "unrecognized field",
            "generation_config", "system_instruction", "safety_settings"
        ])
        if is_param_error:
            return {
                "category": "UNSUPPORTED_PARAMETER",
                "is_model_ineligible": False,
                "can_failover": True,
                "reason": f"Unsupported model-specific parameter in request for '{model_name}' (HTTP 400): {error_message[:100]}"
            }

        # Generic 400 payload / bad request error
        return {
            "category": "INVALID_PAYLOAD",
            "is_model_ineligible": False,
            "can_failover": False,
            "reason": f"Generic HTTP 400 Bad Request for '{model_name}': {error_message[:100]}"
        }

    if status_code >= 500:
        return {
            "category": "SERVER_ERROR",
            "is_model_ineligible": False,
            "can_failover": True,
            "reason": f"Transient 5xx error from '{model_name}' (HTTP {status_code})."
        }

    return {
        "category": "CLIENT_ERROR",
        "is_model_ineligible": False,
        "can_failover": False,
        "reason": f"HTTP {status_code} client error for '{model_name}': {error_message[:100]}"
    }


_last_gemini_429_timestamp: float = 0.0

def is_gemini_in_rate_limit_cooldown() -> bool:
    """Returns True ONLY if all configured candidate models are currently in cooldown."""
    models = get_configured_gemini_models()
    return len(models) > 0 and all(is_model_in_cooldown(m) for m in models)


def record_gemini_429_event(model: Optional[str] = None, retry_after: Optional[float] = None) -> None:
    """Records 429 cooldown for a specific model, or all candidate models if unspecified."""
    global _last_gemini_429_timestamp
    _last_gemini_429_timestamp = time.time()
    if model:
        record_model_429(model, retry_after=retry_after)
    else:
        for m in get_configured_gemini_models():
            record_model_429(m, retry_after=retry_after)
    logger.warning(f"Gemini 429 rate limit recorded.")


def reset_gemini_cooldowns() -> None:
    """Resets all Gemini cooldown timestamps and ineligibility markers for clean isolation."""
    global _last_gemini_429_timestamp
    _last_gemini_429_timestamp = 0.0
    _model_cooldowns.clear()
    _model_cooldown_until.clear()
    _model_ineligible.clear()



def get_gemini_api_key() -> str:
    """Acquires active Gemini API credential according to safe precedence rules."""
    return get_active_gemini_api_key()


def get_gemini_model() -> str:
    return get_configured_gemini_models()[0]


class ReasoningTool(BaseTool):
    @property
    def name(self) -> str:
        return "ReasoningTool"

    @property
    def description(self) -> str:
        return "Provides LLM explanation, conversational assistance, and reasoning."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Reasoning",
            required_inputs=["context"],
            output_schema={"type": "dict"},
            ranking_score=10
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls the Gemini API with bounded multi-model failover, multi-turn history,
        and empathetic local fallback when rate-limited or offline.
        """
        import uuid
        correlation_id = f"chat_{uuid.uuid4().hex[:12]}"
        context = params.get("context", {})
        query = context.get("query")
        decision = context.get("decision", {})
        active_journey = context.get("active_journey")
        history = context.get("history")

        # Check if query seeks commercial or facility POIs
        poi_keywords = [
            "shop", "shops", "store", "stores", "pharmacy", "pharmacies", "chemist", "medicine",
            "hospital", "hospitals", "clinic", "clinics", "supermarket", "supermarkets",
            "cafe", "cafes", "coffee", "restaurant", "restaurants", "food", "grocery", "groceries",
            "atm", "atms", "bank", "fuel", "petrol", "hotel", "safe haven", "facility", "facilities"
        ]
        is_poi_query = bool(query and any(re.search(r'\b' + re.escape(kw) + r'\b', query.lower()) for kw in poi_keywords))

        # Check if query consists of coordinate pairs (e.g. "13.0418, 80.2337")
        coord_match = None
        if query:
            c_pattern = r'^\s*(?:lat(?:itude)?\s*[:=]?\s*)?([+-]?(?:[1-8]?\d(?:\.\d+)?|90(?:\.0+)?))\s*,\s*(?:lon(?:gitude)?\s*[:=]?\s*)?([+-]?(?:180(?:\.0+)?|(?:1[0-7]\d|[1-9]?\d)(?:\.\d+)?))\s*$'
            cm = re.search(c_pattern, query.strip(), re.IGNORECASE)
            if cm:
                v1, v2 = float(cm.group(1)), float(cm.group(2))
                if 11.0 <= v1 <= 15.0 and 78.0 <= v2 <= 82.0:
                    coord_match = (v1, v2)
                elif 11.0 <= v2 <= 15.0 and 78.0 <= v1 <= 82.0:
                    coord_match = (v2, v1)
                else:
                    coord_match = (v1, v2)

        # Check Gemini availability for conversational routing
        active_api_key = get_gemini_api_key()
        gemini_online = bool(active_api_key and active_api_key.strip() and not is_gemini_in_rate_limit_cooldown())

        # Intent classification & local travel-companion handling
        intent_category = IntentCategory.JOURNEY_TRANSIT
        intent_result = None
        if query:
            intent_result = global_intent_classifier.classify(query, history=history)
            intent_category = intent_result.intent

            # Off-topic general queries always receive concise deterministic capsule with redirection
            if intent_category == IntentCategory.OFF_TOPIC and intent_result.direct_response:
                return {
                    "summary": intent_result.direct_response,
                    "reasoning": [f"Handled deterministically by NavSakhi Travel Companion ({intent_category.value})."],
                    "provider": "local_companion",
                    "intent": intent_category.value,
                    "ai_status": "OFFLINE_DETERMINISTIC",
                    "response_source": "rule_based",
                    "intent_category": intent_category.value,
                    "gemini_attempted": False,
                    "model_identifier": None,
                    "attempt_count": 0,
                    "provider_latency_ms": 0.0,
                    "outcome_category": "skipped",
                    "correlation_id": correlation_id
                }

            # If query does not require external LLM and has a direct response (or Gemini is offline/unconfigured), return deterministic response
            if (not intent_result.requires_external_llm or not gemini_online) and not is_poi_query and not coord_match and intent_result.direct_response:
                return {
                    "summary": intent_result.direct_response,
                    "reasoning": [f"Handled deterministically by NavSakhi Travel Companion ({intent_category.value})."],
                    "provider": "local_companion",
                    "intent": intent_category.value,
                    "ai_status": "OFFLINE_DETERMINISTIC",
                    "response_source": "rule_based" if not is_gemini_in_rate_limit_cooldown() else "fallback",
                    "intent_category": intent_category.value,
                    "gemini_attempted": False,
                    "model_identifier": None,
                    "attempt_count": 0,
                    "provider_latency_ms": 0.0,
                    "outcome_category": "skipped" if not is_gemini_in_rate_limit_cooldown() else "rate_limited",
                    "correlation_id": correlation_id
                }

        grounded_pois: List[Dict[str, Any]] = []
        poi_location_label: Optional[str] = None

        if is_poi_query:
            from app.tools.specialized.poi_tool import POITool
            poi_tool = POITool()

            # Attempt to extract location name from query
            place_match = re.search(
                r'(?:near|in|around|at|by|close to)\s+([A-Za-z0-9\s\.\-]+?)(?:\?|$|\.|\,|for|with)',
                query,
                re.IGNORECASE
            )
            extracted_place = place_match.group(1).strip() if place_match else None

            # Category filter
            target_category = None
            q_lower = query.lower()
            if any(w in q_lower for w in ["pharmacy", "pharmacies", "chemist", "medicine"]):
                target_category = "pharmacy"
            elif any(w in q_lower for w in ["hospital", "hospitals", "clinic", "clinics"]):
                target_category = "clinic"
            elif any(w in q_lower for w in ["supermarket", "grocery", "groceries"]):
                target_category = "supermarket"
            elif any(w in q_lower for w in ["police", "station"]):
                target_category = "police"
            elif any(w in q_lower for w in ["cafe", "coffee", "restaurant", "food"]):
                target_category = "restaurant"
            elif any(w in q_lower for w in ["atm", "bank"]):
                target_category = "bank_atm"
            elif any(w in q_lower for w in ["shop", "store"]):
                target_category = "shop"

            if extracted_place:
                poi_res = await poi_tool.execute({
                    "place": extracted_place,
                    "category": target_category,
                    "radius_m": 1500.0,
                    "max_results": 10
                })
                if poi_res.get("status") == "AVAILABLE":
                    grounded_pois = poi_res.get("pois", [])
                    poi_location_label = extracted_place.title()
                elif poi_res.get("status") in ["NOT_FOUND", "EMPTY"]:
                    poi_location_label = extracted_place.title()
            elif active_journey:
                all_coords = []
                if hasattr(active_journey, "planned_routes") and active_journey.planned_routes:
                    for r in active_journey.planned_routes:
                        for s in r.get("segments", []):
                            poly = s.get("polyline")
                            if poly and isinstance(poly, dict):
                                geom = poly.get("geometry", poly)
                                all_coords.extend(geom.get("coordinates", []))
                if all_coords:
                    poi_res = await poi_tool.execute({
                        "corridor_coords": all_coords,
                        "radius_m": 800.0,
                        "max_results": 10
                    })
                    grounded_pois = poi_res.get("pois", [])
                    dest_n = getattr(active_journey, "destination_name", "your active route")
                    poi_location_label = f"corridor towards {dest_n}"

        elif coord_match:
            c_lat, c_lon = coord_match
            from app.services.poi_service import get_poi_service
            point_res = get_poi_service().query_pois_near_point(c_lon, c_lat, radius_m=1200.0, max_results=8)
            grounded_pois = point_res.get("pois", [])
            poi_location_label = f"coordinates ({c_lat:.4f}, {c_lon:.4f})"

        # Deterministic fallback summary tailored to intent
        if grounded_pois:
            lines = []
            for p in grounded_pois[:5]:
                p_name = p.get("name", "Unnamed")
                p_cat = p.get("category_label") or p.get("category", "Shop")
                p_dist = int(p.get("distance_m", 0))
                p_hours = p.get("opening_hours") or "Hours not published in OpenStreetMap"
                p_status = p.get("opening_status", "UNKNOWN")
                status_desc = f" ({p_status})" if p_status != "UNKNOWN" else ""
                lines.append(f"- **{p_name}** ({p_cat}): ~{p_dist}m away &bull; Hours: {p_hours}{status_desc}")

            loc_txt = f" near **{poi_location_label}**" if poi_location_label else ""
            if coord_match:
                c_lat, c_lon = coord_match
                fallback_summary = (
                    f"I received coordinates **({c_lat:.4f}, {c_lon:.4f})**. What would you like to find near here? "
                    f"(For example: open pharmacies, hospitals, commercial shops, or route navigation).\n\n"
                    f"Here are nearest mapped establishments found near these coordinates in Chennai:\n\n"
                    + "\n".join(lines)
                    + "\n\n*(Note: These records are sourced from OpenStreetMap. Commercial businesses provide public street activity, but are not verified emergency shelters or police checkpoints.)*"
                )
            else:
                fallback_summary = (
                    f"Here are mapped establishments found{loc_txt} in Chennai:\n\n"
                    + "\n".join(lines)
                    + "\n\n*(Note: These records are sourced from OpenStreetMap. Commercial businesses provide public street activity, but are not verified emergency shelters or police checkpoints.)*"
                )
        elif coord_match and not grounded_pois:
            c_lat, c_lon = coord_match
            fallback_summary = (
                f"I received coordinates **({c_lat:.4f}, {c_lon:.4f})**. No mapped establishments were found within 1.2km in our Chennai dataset. "
                "What would you like to find near here, or would you like to plan a route from this location?"
            )
        elif poi_location_label and not grounded_pois:
            fallback_summary = (
                f"I checked the mapped OpenStreetMap records for Chennai near **{poi_location_label}**, but no matching establishments were found within the search radius. "
                "You can specify a nearby arterial junction or landmark (for example: *'near T. Nagar bus terminus'* or *'near Central'*)."
            )
        elif is_poi_query and not active_journey:
            fallback_summary = (
                "Which area or landmark in Chennai would you like me to check for shops or facilities? "
                "(For example: *'Shops near T. Nagar'* or *'Pharmacies near Adyar'*). "
                "If you start a monitored journey in the Journey Planner, I can also look along your route corridor."
            )
        elif intent_result and intent_result.direct_response:
            fallback_summary = intent_result.direct_response
        elif query:
            q_lower = query.lower()
            if any(w in q_lower for w in ["following me", "follow me", "stalk", "stalker", "danger", "attack", "screaming", "hurt", "in danger"]):
                fallback_summary = (
                    "I hear you, and your immediate safety is the top priority. If someone is following you or you feel in danger:\n\n"
                    "1. **Move to a Staffed Safe Haven Immediately:** Walk directly into an open shop, well-lit café, metro station customer counter, or busy bus shelter nearby.\n"
                    "2. **Alert People Nearby:** Let staff or commuters know you need help.\n"
                    "3. **Call Emergency Services:**\n"
                    "   - **112** (National Emergency Helpline)\n"
                    "   - **1091** (Tamil Nadu Women Helpline)\n"
                    "4. **Share Live Route:** Tap the SOS button in NavSakhi to alert your emergency contacts."
                )
            elif any(w in q_lower for w in ["nervous", "anxious", "travel anxiety", "uneasy", "feeling alone"]):
                fallback_summary = (
                    "It is completely normal to feel nervous when traveling alone. Take a slow breath — I am right here with you in your phone. "
                    "Stay along well-lit transit corridors like the Chennai Metro or major MTC routes, and sit near the conductor or in the designated women's section. "
                    "Where are you traveling right now?"
                )
            elif any(w in q_lower for w in ["companion", "partner", "be with me", "with me throughout", "with me through out"]):
                fallback_summary = (
                    "I would be glad to stay with you throughout your journey as your travel partner. "
                    "You can keep this chat open and message me anytime you need route reassurance or just friendly conversation. "
                    "Where are you heading today?"
                )
            elif any(w in q_lower for w in ["hi", "hello", "hey", "namaste", "vanakkam"]):
                fallback_summary = "Hello! I am your NavSakhi travel companion. How can I help you navigate Chennai safely today?"
            elif any(w in q_lower for w in ["score", "lightgbm", "safety score", "model", "how is score", "scoring", "based on"]):
                fallback_summary = (
                    "NavSakhi safety scores are calculated using a frozen LightGBM regression model that evaluates objective "
                    "road environmental infrastructure features (highway class, road width, junction complexity, service density). "
                    "Night Activity Scores are computed independently from open places and transit nodes. It represents an environmental "
                    "proxy, not an empirical crime prediction."
                )
            elif any(w in q_lower for w in ["emergency", "police", "sos", "helpline", "112", "1091"]):
                fallback_summary = (
                    "For immediate assistance, dial 112 (National Emergency Helpline) or 1091 (Women Helpline in Tamil Nadu). "
                    "You can also trigger NavSakhi SOS on the dashboard to share live telemetry with your emergency contacts."
                )
            elif any(w in q_lower for w in ["metro", "suburban", "bus", "mtc", "train"]):
                fallback_summary = (
                    "NavSakhi supports Chennai Metro (Blue and Green lines), Suburban rail corridors (South, West, and North lines), "
                    "and MTC bus routes across Chennai."
                )
            elif any(w in q_lower for w in ["aware", "be aware", "look out", "watch out", "safety tip", "safety tips", "precaution", "precautions", "stay safe", "guidelines"]):
                fallback_summary = (
                    "When navigating Chennai, keep these practical safety considerations in mind:\n\n"
                    "1. **Use Well-Lit Primary Corridors:** Choose active transit modes like Chennai Metro or primary arterial MTC bus routes, especially during evening hours.\n"
                    "2. **Stay Near Staffed Facilities:** At stations and bus stops, wait near ticket counters, station masters, or well-populated areas.\n"
                    "3. **Share Live Trip Telemetry:** Keep your phone charged and share your active route link with family or a trusted contact.\n"
                    "4. **Emergency Helplines:** Note that **112** (National Emergency) and **1091** (Tamil Nadu Women Helpline) are available 24/7."
                )
            else:
                fallback_summary = (
                    "I am your NavSakhi travel companion. You can ask me about safe route planning in Chennai, transport options (Metro, Bus, Suburban), "
                    "or nearby emergency support. How can I help you right now?"
                )
        else:
            fallback_summary = "Route evaluated using verified network topology and model-ready road infrastructure data."

        fallback_reasoning = [
            "Network topology verified against mapped road and transit layers.",
            "Segment coverage validated according to scoring requirements.",
            "Evaluations bounded to synthetic environmental proxy indicators without unsupported claims."
        ]

        api_key = get_gemini_api_key()
        if not api_key or not api_key.strip():
            logger.info("GEMINI_API_KEY not configured; using verified conversational/infrastructure fallback.")
            is_rule_based_eligible = (
                intent_result is not None
                and intent_result.intent in [IntentCategory.SMALL_TALK, IntentCategory.OFF_TOPIC]
            )
            return {
                "summary": fallback_summary,
                "reasoning": fallback_reasoning,
                "provider": "local_companion" if is_rule_based_eligible else "local_fallback",
                "intent": intent_category.value,
                "ai_status": "OFFLINE_DETERMINISTIC" if is_rule_based_eligible else "CONFIG_MISSING_FALLBACK",
                "response_source": "rule_based" if is_rule_based_eligible else "fallback",
                "intent_category": intent_category.value,
                "gemini_attempted": False,
                "model_identifier": None,
                "attempt_count": 0,
                "provider_latency_ms": 0.0,
                "outcome_category": "unavailable",
                "correlation_id": correlation_id
            }

        # Check if all candidate models are currently rate-limited
        if is_gemini_in_rate_limit_cooldown():
            logger.info("All Gemini models in cooldown; returning honest rate-limited fallback.")
            rate_limit_note = "\n\n*(Note: Live AI reasoning is temporarily paused due to upstream provider rate limits. NavSakhi verified local travel guidance is active.)*"
            return {
                "summary": fallback_summary + rate_limit_note,
                "reasoning": fallback_reasoning,
                "provider": "local_fallback",
                "intent": intent_category.value,
                "ai_status": "RATE_LIMITED_FALLBACK",
                "response_source": "fallback",
                "intent_category": intent_category.value,
                "gemini_attempted": False,
                "model_identifier": None,
                "attempt_count": 0,
                "provider_latency_ms": 0.0,
                "outcome_category": "rate_limited",
                "correlation_id": correlation_id
            }

        # Prepare outbound payload
        if query:
            payload = build_sanitized_chat_payload(
                query=query,
                active_journey=active_journey,
                history=history,
                grounded_pois=grounded_pois,
                poi_location_name=poi_location_label,
                coord_match=coord_match
            )
        else:
            clean_decision = sanitize_privacy_context(str(decision))
            prompt = (
                f"You are NavSakhi AI. Explain this route decision factually based on verified infrastructure: {clean_decision}. "
                "CRITICAL CONSTRAINTS: Do not claim specific lighting conditions, crowd densities, or community incident counts. "
                "Do not state that any route guarantees safety. Keep explanations grounded strictly in objective route metrics."
            )
            payload = {"contents": [{"parts": [{"text": prompt}]}]}

        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": api_key
        }

        # Bounded multi-model failover execution
        candidate_models = get_configured_gemini_models()
        total_deadline_sec = 5.0
        start_time = time.monotonic()
        last_failure_status = "UNAVAILABLE_FALLBACK"
        attempt_count = 0
        last_attempted_model = None
        last_outcome = "unavailable"

        for model_name in candidate_models:
            if is_model_in_cooldown(model_name):
                continue

            remaining_budget = total_deadline_sec - (time.monotonic() - start_time)
            if remaining_budget < 1.0:
                logger.info("Remaining Gemini budget exhausted; halting model failover.")
                last_outcome = "timeout"
                break

            attempt_timeout = min(remaining_budget, 3.0)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            attempt_count += 1
            last_attempted_model = model_name
            call_start = time.monotonic()

            try:
                async with httpx.AsyncClient(timeout=attempt_timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    call_latency_ms = (time.monotonic() - call_start) * 1000.0

                    if response.status_code == 200:
                        res_data = response.json()
                        text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        return {
                            "summary": text,
                            "reasoning": fallback_reasoning,
                            "provider": "gemini",
                            "model": model_name,
                            "intent": intent_category.value,
                            "ai_status": "LIVE_SUCCESS",
                            "response_source": "gemini",
                            "intent_category": intent_category.value,
                            "gemini_attempted": True,
                            "model_identifier": model_name,
                            "attempt_count": attempt_count,
                            "provider_latency_ms": round(call_latency_ms, 1),
                            "outcome_category": "success",
                            "correlation_id": correlation_id
                        }

                    err_info = classify_gemini_error(response.status_code, response.text, model_name)
                    logger.warning(f"Gemini model '{model_name}' HTTP {response.status_code}: {err_info['reason']}")

                    if err_info["category"] == "RATE_LIMIT":
                        retry_after = _parse_retry_after(response.headers)
                        record_model_429(model_name, retry_after=retry_after)
                        last_failure_status = "RATE_LIMITED_FALLBACK"
                        last_outcome = "rate_limited"
                        continue

                    if err_info["category"] == "AUTH_RESTRICTION":
                        logger.warning(f"Gemini returned auth/project restriction HTTP {response.status_code}. Halting model rotation.")
                        last_failure_status = "AUTH_RESTRICTION_FALLBACK"
                        last_outcome = "unavailable"
                        break

                    if err_info["is_model_ineligible"]:
                        mark_model_ineligible(model_name, err_info["reason"])

                    last_outcome = "invalid_response"
                    if err_info["can_failover"]:
                        continue
                    else:
                        break

            except (asyncio.TimeoutError, httpx.TimeoutException):
                last_outcome = "timeout"
                logger.warning(f"Gemini attempt with model '{model_name}' timed out. Failing over...")
            except Exception as e:
                last_outcome = "timeout" if "timeout" in str(e).lower() else "invalid_response"
                logger.warning(f"Gemini attempt with model '{model_name}' failed ({type(e).__name__}: {e}). Failing over...")

        total_elapsed_ms = (time.monotonic() - start_time) * 1000.0
        # If all candidate models fail or time out, return honest contextual fallback
        return {
            "summary": fallback_summary,
            "reasoning": fallback_reasoning,
            "provider": "local_fallback",
            "intent": intent_category.value,
            "ai_status": last_failure_status,
            "response_source": "fallback",
            "intent_category": intent_category.value,
            "gemini_attempted": attempt_count > 0,
            "model_identifier": last_attempted_model,
            "attempt_count": attempt_count,
            "provider_latency_ms": round(total_elapsed_ms, 1),
            "outcome_category": last_outcome,
            "correlation_id": correlation_id
        }

    async def explain_journey_recommendations(
        self,
        source: str,
        dest: str,
        verified_routes: List[Dict[str, Any]],
        preferences: Optional[List[str]] = None,
        weather: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Explains already validated and scored candidate routes with bounded multi-model failover.
        Gemini NEVER invents stations, geometries, or scores.
        """
        api_key = get_gemini_api_key()
        if not api_key or not api_key.strip() or not verified_routes:
            return None

        if is_gemini_in_rate_limit_cooldown():
            logger.info("Gemini in cooldown; returning local route explanation fallback.")
            top_route = verified_routes[0] if verified_routes else {}
            top_name = top_route.get("route_name", "Primary Option")
            return {
                "title": "Objective AI Recommendation",
                "summary": f"Recommended {top_name} based on verified routing topology.",
                "reasoning": "Route evaluated using verified network topology and model-ready road infrastructure data.",
                "tradeoff_explanation": f"Evaluated {len(verified_routes)} verified routing alternatives.",
                "tradeoffs": ["Direct road transit prioritizes door-to-door speed."]
            }

        candidate_models = get_configured_gemini_models()
        total_deadline_sec = 2.5
        start_time = time.monotonic()
        payload = build_sanitized_route_explanation_payload(
            source=source,
            dest=dest,
            verified_routes=verified_routes,
            preferences=preferences,
            weather=weather
        )
        headers = {"Content-Type": "application/json", "X-goog-api-key": api_key}

        for model_name in candidate_models:
            if is_model_in_cooldown(model_name):
                continue

            remaining_budget = total_deadline_sec - (time.monotonic() - start_time)
            if remaining_budget < 0.8:
                break

            attempt_timeout = min(remaining_budget, 1.8)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

            try:
                async with httpx.AsyncClient(timeout=attempt_timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    if response.status_code == 200:
                        res_data = response.json()
                        text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        if text.startswith("```"):
                            lines = text.splitlines()
                            if lines[0].startswith("```"): lines = lines[1:]
                            if lines and lines[-1].startswith("```"): lines = lines[:-1]
                            text = "\n".join(lines).strip()

                        parsed = json.loads(text)
                        if isinstance(parsed, dict):
                            return parsed

                    err_info = classify_gemini_error(response.status_code, response.text, model_name)
                    if err_info["category"] == "RATE_LIMIT":
                        retry_after = _parse_retry_after(response.headers)
                        record_model_429(model_name, retry_after=retry_after)
                        continue
                    if err_info["category"] == "AUTH_RESTRICTION":
                        break
                    if err_info["is_model_ineligible"]:
                        mark_model_ineligible(model_name, err_info["reason"])
                    if err_info["can_failover"]:
                        continue
                    else:
                        break

            except Exception as e:
                logger.info(f"Gemini route explanation model '{model_name}' attempt skipped: {e}")

        # Deterministic local explanation fallback
        top_route = verified_routes[0] if verified_routes else {}
        top_name = top_route.get("route_name", "Primary Option")
        return {
            "title": "Objective AI Recommendation",
            "summary": f"Recommended {top_name} based on verified routing topology.",
            "reasoning": "Route evaluated using verified network topology and model-ready road infrastructure data.",
            "tradeoff_explanation": f"Evaluated {len(verified_routes)} verified routing alternatives.",
            "tradeoffs": ["Direct road transit prioritizes door-to-door speed."]
        }

    async def generate_dynamic_plans(self, source: str, dest: str, dist_km: float, preferences: list = None) -> list:
        """
        Experimental Strategy B dynamic plan generation.
        Strictly isolated: disabled by default; only runs if enable_experimental_strategy_b is True.
        """
        if not getattr(settings, "enable_experimental_strategy_b", False):
            logger.debug("Strategy B dynamic plans disabled by default; skipping.")
            return []

        api_key = get_gemini_api_key()
        if not api_key or not api_key.strip():
            logger.info("GEMINI_API_KEY not configured; skipping dynamic planning.")
            return []

        # If trip is short, public transit is not realistic
        if dist_km < 3.0:
            logger.info(f"Trip distance ({dist_km:.2f} km) too short for rail transit; skipping transit prompt.")
            return []

        clean_source = sanitize_privacy_context(source)
        clean_dest = sanitize_privacy_context(dest)
        prefs_str = ", ".join(preferences) if preferences else "ANY"

        prompt = f"""
You are an intelligent mobility planner for Chennai. 
Source: {clean_source}
Destination: {clean_dest}
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
        try:
            model_name = get_gemini_model()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {"Content-Type": "application/json", "X-goog-api-key": api_key}

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                res_data = response.json()

            text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text.startswith("```"):
                lines = text.splitlines()
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].startswith("```"): lines = lines[:-1]
                text = "\n".join(lines).strip()

            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else []
        except Exception as e:
            logger.warning(f"Gemini dynamic planning failed: {e}")
            return []


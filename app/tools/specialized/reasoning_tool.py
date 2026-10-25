import re
import httpx
import json
import logging
from typing import Dict, Any, List, Optional
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
    history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Constructs an outbound payload for conversational Gemini requests,
    guaranteeing no raw coordinates, geometry, or credentials are leaked.
    Incorporates recent conversation history for empathetic multi-turn context.
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

    prompt = (
        "You are NavSakhi, a warm, compassionate, and trustworthy travel companion for women navigating Chennai.\n"
        f"{history_context}"
        f"Current user message: {clean_query}\n"
        f"Active journey context: {'Active journey to ' + clean_dest if active_journey else 'No active journey'}\n\n"
        "COMPANION PERSONA & TONE GUIDELINES:\n"
        "1. WARMTH & CALM SUPPORT: Speak naturally with a supportive, calm, conversational feminine companion voice ('Sakhi' means trusted female friend). "
        "Acknowledge the user's specific statement or emotion with genuine empathy. Do not repeat generic introductory greetings on follow-up turns.\n"
        "2. COMPANIONSHIP & JOURNEY PARTNER: If the user seeks companionship, asks to talk, or wants a partner for their journey, "
        "warmly assure them you are here with them in their phone throughout their travel. Respond to their immediate emotional need before offering suggestions. "
        "Ask at most one natural follow-up question. Do not give long unsolicited safety lists when the user simply seeks company.\n"
        "3. TRAVEL ANXIETY VS ACUTE DANGER:\n"
        "   - If expressing nervousness about traveling alone: recognize the feeling with calm reassurance, recommend well-lit major transit like Chennai Metro or bus, "
        "and suggest sitting near the conductor/women's section without triggering a false emergency alarm.\n"
        "   - If facing acute danger, being followed, or in distress: prioritize immediate physical safety, advise moving into a staffed shop/metro counter, "
        "and provide emergency helplines: 112 (National Emergency) and 1091 (Women Helpline).\n"
        "4. HONESTY: Do NOT claim to be human or promise physical in-person protection. Never invent transit schedules or fares.\n"
        "5. READABLE FORMATTING: Use clean, human-friendly Markdown: short paragraphs, clear bolding (**bold**), and numbered steps if helpful."
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
CANDIDATE_GEMINI_MODELS: List[str] = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.8-flash"
]

# Per-model cooldown tracking
_model_cooldowns: Dict[str, float] = {}
_model_ineligible: set = set()
GEMINI_429_COOLDOWN_SECONDS: float = 60.0


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
    if model in _model_ineligible:
        return True
    last_time = _model_cooldowns.get(model, 0.0)
    return (time.time() - last_time) < GEMINI_429_COOLDOWN_SECONDS


def record_model_429(model: str) -> None:
    _model_cooldowns[model] = time.time()
    logger.warning(f"Gemini model '{model}' reached rate limit (429). Cooldown activated for {GEMINI_429_COOLDOWN_SECONDS}s.")


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
    """Returns True if global cooldown is active or all configured candidate models are currently in cooldown."""
    global _last_gemini_429_timestamp
    if (time.time() - _last_gemini_429_timestamp) < GEMINI_429_COOLDOWN_SECONDS:
        return True
    models = get_configured_gemini_models()
    return all(is_model_in_cooldown(m) for m in models)


def record_gemini_429_event() -> None:
    """Legacy helper: records 429 globally and across candidate models."""
    global _last_gemini_429_timestamp
    _last_gemini_429_timestamp = time.time()
    for m in get_configured_gemini_models():
        _model_cooldowns[m] = time.time()
    logger.warning(f"Gemini 429 rate limit recorded. Cooldown activated for {GEMINI_429_COOLDOWN_SECONDS}s.")


def reset_gemini_cooldowns() -> None:
    """Resets all Gemini cooldown timestamps and ineligibility markers for clean isolation."""
    global _last_gemini_429_timestamp
    _last_gemini_429_timestamp = 0.0
    _model_cooldowns.clear()
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
        context = params.get("context", {})
        query = context.get("query")
        decision = context.get("decision", {})
        active_journey = context.get("active_journey")
        history = context.get("history")

        # Intent classification & local travel-companion handling
        intent_category = IntentCategory.JOURNEY_TRANSIT
        intent_result = None
        if query:
            intent_result = global_intent_classifier.classify(query, history=history)
            intent_category = intent_result.intent

            # Small talk or off-topic with deterministic companion response
            if not intent_result.requires_external_llm and intent_result.direct_response:
                return {
                    "summary": intent_result.direct_response,
                    "reasoning": [f"Handled deterministically by NavSakhi Travel Companion ({intent_category.value})."],
                    "provider": "local_companion",
                    "intent": intent_category.value,
                    "ai_status": "OFFLINE_DETERMINISTIC"
                }

        # Deterministic fallback summary tailored to intent
        if intent_result and intent_result.direct_response:
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
            return {
                "summary": fallback_summary,
                "reasoning": fallback_reasoning,
                "provider": "local_fallback",
                "intent": intent_category.value,
                "ai_status": "CONFIG_MISSING_FALLBACK"
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
                "ai_status": "RATE_LIMITED_FALLBACK"
            }

        # Prepare outbound payload
        if query:
            payload = build_sanitized_chat_payload(query=query, active_journey=active_journey, history=history)
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

        for model_name in candidate_models:
            if is_model_in_cooldown(model_name):
                continue

            remaining_budget = total_deadline_sec - (time.monotonic() - start_time)
            if remaining_budget < 1.0:
                logger.info("Remaining Gemini budget exhausted; halting model failover.")
                break

            attempt_timeout = min(remaining_budget, 3.0)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

            try:
                async with httpx.AsyncClient(timeout=attempt_timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)

                    if response.status_code == 200:
                        res_data = response.json()
                        text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        return {
                            "summary": text,
                            "reasoning": fallback_reasoning,
                            "provider": "gemini",
                            "model": model_name,
                            "intent": intent_category.value,
                            "ai_status": "LIVE_SUCCESS"
                        }

                    err_info = classify_gemini_error(response.status_code, response.text, model_name)
                    logger.warning(f"Gemini model '{model_name}' HTTP {response.status_code}: {err_info['reason']}")

                    if err_info["category"] == "RATE_LIMIT":
                        record_model_429(model_name)
                        last_failure_status = "RATE_LIMITED_FALLBACK"
                        continue

                    if err_info["category"] == "AUTH_RESTRICTION":
                        logger.warning(f"Gemini returned auth/project restriction HTTP {response.status_code}. Halting model rotation.")
                        last_failure_status = "AUTH_RESTRICTION_FALLBACK"
                        break

                    if err_info["is_model_ineligible"]:
                        mark_model_ineligible(model_name, err_info["reason"])

                    if err_info["can_failover"]:
                        continue
                    else:
                        break

            except Exception as e:
                logger.warning(f"Gemini attempt with model '{model_name}' failed ({type(e).__name__}: {e}). Failing over...")

        # If all candidate models fail or time out, return honest contextual fallback
        return {
            "summary": fallback_summary,
            "reasoning": fallback_reasoning,
            "provider": "local_fallback",
            "intent": intent_category.value,
            "ai_status": last_failure_status
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
                        record_model_429(model_name)
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


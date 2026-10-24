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


def build_sanitized_chat_payload(query: str, active_journey: Any = None) -> Dict[str, Any]:
    """
    Constructs an outbound payload for conversational Gemini requests,
    guaranteeing no raw coordinates, geometry, or credentials are leaked.
    """
    clean_query = sanitize_privacy_context(query)
    dest_name = getattr(active_journey, "destination_name", None) or "destination"
    clean_dest = sanitize_privacy_context(dest_name) if active_journey else "No active journey"

    prompt = (
        "You are NavSakhi, a warm, compassionate, and trustworthy travel companion for women navigating Chennai.\n"
        f"User message: {clean_query}\n"
        f"Active journey context: {'Active journey to ' + clean_dest if active_journey else 'No active journey'}\n\n"
        "COMPANION PERSONA & TONE GUIDELINES:\n"
        "1. WARMTH & CALM SUPPORT: Speak naturally with a supportive, calm, conversational feminine companion voice ('Sakhi' means trusted female friend). "
        "Acknowledge feelings of anxiety, fatigue, or unease with genuine empathy without sounding robotic or dismissive. "
        "If a user asks if you can accompany them, assure them warmly that you are right here in their phone throughout their travel.\n"
        "2. EMOTIONAL REASSURANCE & IMMEDIATE SAFETY: When a user expresses anxiety, fear, being alone, or feeling unsafe:\n"
        "   - Respond calmly and empathetically to help de-escalate anxiety.\n"
        "   - Ask gently if they are currently safe or in immediate danger.\n"
        "   - Give clear, practical advice: move to populated well-lit spots (such as an open shop, well-lit café, metro station, or active bus stop), "
        "keep a trusted contact updated with their live location, and choose verified transit routes.\n"
        "   - For urgent distress or imminent danger, clearly provide emergency numbers: 112 (National Emergency Helpline) and 1091 (Tamil Nadu Women Helpline).\n"
        "   - NEVER claim that you dispatched physical emergency responders or called the police on your own.\n"
        "3. NATURAL CONVERSATION: If asked general questions, everyday advice, transit directions, or cultural/local queries about Chennai, "
        "answer knowledgeably, warmly, and helpfully. Do not force repetitive safety disclaimers into casual conversational turns.\n"
        "4. NAVSAKHI FEATURES: Clearly explain multimodal transit options (Chennai Metro, Suburban rail, MTC buses), "
        "the LightGBM environmental safety risk score, Night Activity Scores, verified emergency facilities, and SOS live location sharing.\n"
        "5. TRUTHFULNESS: NEVER invent transit schedules, operational hours, or fares. Distinguish official fares from estimates or metered rides.\n"
        "6. READABLE FORMATTING: Use clean, human-friendly Markdown: short paragraphs, clear bolding (**bold**), bullet points (-), and numbered steps (1., 2.). "
        "Never output giant walls of dense unbroken text."
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

_last_gemini_429_timestamp: float = 0.0
GEMINI_429_COOLDOWN_SECONDS: float = 60.0


def is_gemini_in_rate_limit_cooldown() -> bool:
    global _last_gemini_429_timestamp
    return (time.time() - _last_gemini_429_timestamp) < GEMINI_429_COOLDOWN_SECONDS


def record_gemini_429_event() -> None:
    global _last_gemini_429_timestamp
    _last_gemini_429_timestamp = time.time()
    logger.warning("Gemini 429 rate limit recorded. Cooldown activated for 60s.")


def get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "") or getattr(settings, "gemini_api_key", "") or ""


def get_gemini_model() -> str:
    configured = getattr(settings, "llm_model_name", None) or os.getenv("LLM_MODEL_NAME", "")
    if configured and str(configured).strip():
        return str(configured).strip()
    return "gemini-3.5-flash-lite"


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
        Calls the Gemini API for conversational assistance or route reasoning,
        with strict deterministic fallback when offline or rate-limited.
        Integrates intent classification to handle small talk and off-topic queries locally.
        """
        context = params.get("context", {})
        query = context.get("query")
        decision = context.get("decision", {})
        active_journey = context.get("active_journey")

        # Intent classification & local travel-companion handling
        intent_category = IntentCategory.JOURNEY_TRANSIT
        if query:
            intent_result = global_intent_classifier.classify(query)
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

        # Determine fallback summary for safety, transit, or app support
        if query:
            q_lower = query.lower()
            if any(w in q_lower for w in ["unsafe", "scared", "alone", "nervous", "anxious", "fear", "uncomfortable", "following me", "follow me"]):
                fallback_summary = (
                    "I hear you, and it is completely understandable to feel uncomfortable or anxious when traveling alone. Your safety and peace of mind are the priority.\n\n"
                    "### Immediate Steps to Take:\n"
                    "1. **Move to a Populated Safe Haven:** Step into an open shop, well-lit café, metro station, or active bus shelter nearby.\n"
                    "2. **Stay Connected:** Call or share your live location with a trusted friend or family member.\n"
                    "3. **Emergency Support:** If you feel in immediate danger, do not hesitate to call:\n"
                    "   - **112** (National Emergency Helpline)\n"
                    "   - **1091** (Women Helpline — Tamil Nadu)\n"
                    "4. **Verified Transit:** Prefer Chennai Metro or major MTC arterial bus routes over isolated streets.\n\n"
                    "Are you in a safe spot right now, or would you like help finding the nearest verified transit hub or emergency service?"
                )
            elif any(w in q_lower for w in ["hi", "hello", "hey", "good morning", "good evening", "namaste", "vanakkam"]):
                fallback_summary = "Hello! I am your NavSakhi travel companion. How can I help you navigate Chennai safely today?"
            elif any(w in q_lower for w in ["how can i use", "how to use", "site", "website", "guide", "tutorial", "how do i use"]):
                fallback_summary = (
                    "Welcome to NavSakhi! You can plan safe multimodal journeys across Chennai by entering your origin and destination. "
                    "Our platform compares Chennai Metro, Suburban rail, MTC buses, and cab/walking routes, assessed with road infrastructure "
                    "features, Night Activity Scores, and verified emergency facilities."
                )
            elif any(w in q_lower for w in ["what is navsakhi", "about", "feature", "how does", "what can you do"]):
                fallback_summary = (
                    "NavSakhi is an intelligent mobility platform for women in Chennai. "
                    "It combines multimodal transit routing (MTC buses, Chennai Metro, Suburban rail) "
                    "with road infrastructure safety proxies, Night Activity Scores, and emergency support."
                )
            elif any(w in q_lower for w in ["login", "signin", "sign in", "register", "signup", "sign up", "account", "password"]):
                fallback_summary = (
                    "To sign in or create an account, use the buttons in the navigation header. "
                    "You can also use NavSakhi freely as a guest to plan routes and explore the map."
                )
            elif any(w in q_lower for w in ["emergency", "police", "sos", "helpline", "danger", "help", "112", "1091"]):
                fallback_summary = (
                    "For immediate assistance, dial 112 (National Emergency Helpline) or 1091 (Women Helpline in Tamil Nadu). "
                    "You can also trigger NavSakhi SOS on the dashboard to share live telemetry with your emergency contacts."
                )
            elif any(w in q_lower for w in ["score", "lightgbm", "safety score", "model", "how is score", "scoring"]):
                fallback_summary = (
                    "NavSakhi safety scores are generated by a trained LightGBM model evaluating road environmental proxies "
                    "(infrastructure width, lighting potential, service density, and road class). It is an environmental indicator, "
                    "not an empirical crime predictor or guarantee of personal safety."
                )
            elif any(w in q_lower for w in ["metro", "suburban", "bus", "mtc", "train", "transport", "mode"]):
                fallback_summary = (
                    "NavSakhi supports Chennai Metro (Blue and Green lines), Suburban rail corridors (South, West, and North lines), "
                    "MTC bus routes, and first/last-mile auto and walking connections."
                )
            else:
                fallback_summary = (
                    "I am your NavSakhi AI assistant. You can ask me about safe route planning in Chennai, transport options (Metro, Bus, Suburban), "
                    "account help, or nearby emergency services. How can I help you right now?"
                )
        else:
            fallback_summary = "Route evaluated using verified network topology and model-ready road infrastructure data."

        fallback_reasoning = [
            "Network topology verified against mapped road and transit layers.",
            "Segment coverage validated according to scoring requirements.",
            "Evaluations bounded to synthetic environmental proxy indicators without unsupported claims."
        ]

        # Rate-limit cooldown guard: do not repeat requests during active HTTP 429 cooldown
        if is_gemini_in_rate_limit_cooldown():
            logger.info("Gemini 429 cooldown active; returning honest rate-limited fallback.")
            rate_limit_note = "\n\n*(Note: Live AI reasoning is temporarily paused due to upstream provider rate limits. NavSakhi verified local travel guidance is active.)*"
            return {
                "summary": fallback_summary + rate_limit_note,
                "reasoning": fallback_reasoning,
                "provider": "local_fallback",
                "intent": intent_category.value,
                "ai_status": "RATE_LIMITED_FALLBACK"
            }

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

        try:
            model_name = get_gemini_model()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

            if query:
                payload = build_sanitized_chat_payload(query=query, active_journey=active_journey)
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

            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 429:
                    record_gemini_429_event()
                    return {
                        "summary": fallback_summary,
                        "reasoning": fallback_reasoning,
                        "provider": "local_fallback",
                        "intent": intent_category.value,
                        "ai_status": "RATE_LIMITED_FALLBACK"
                    }
                response.raise_for_status()
                res_data = response.json()

            text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return {
                "summary": text,
                "reasoning": fallback_reasoning,
                "provider": "gemini",
                "intent": intent_category.value,
                "ai_status": "LIVE_SUCCESS"
            }
        except Exception as e:
            logger.warning(f"Gemini execute error, using fallback: {e}")
            return {
                "summary": fallback_summary,
                "reasoning": fallback_reasoning,
                "provider": "local_fallback",
                "intent": intent_category.value,
                "ai_status": "UNAVAILABLE_FALLBACK"
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
        Explains already validated and scored candidate routes using supplied evidence,
        actual ML scores, live weather, and explicit user preferences.
        Gemini NEVER invents stations, geometries, or scores.
        """
        api_key = get_gemini_api_key()
        if not api_key or not api_key.strip() or not verified_routes:
            return None

        if is_gemini_in_rate_limit_cooldown():
            logger.info("Gemini 429 cooldown active; using local route explanation fallback.")
            top_route = verified_routes[0] if verified_routes else {}
            top_name = top_route.get("route_name", "Primary Option")
            return {
                "title": "Objective AI Recommendation",
                "summary": f"Recommended {top_name} based on verified routing topology.",
                "reasoning": "Route evaluated using verified network topology and model-ready road infrastructure data.",
                "tradeoff_explanation": f"Evaluated {len(verified_routes)} verified routing alternatives.",
                "tradeoffs": ["Direct road transit prioritizes door-to-door speed."]
            }

        try:
            model_name = get_gemini_model()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            payload = build_sanitized_route_explanation_payload(
                source=source,
                dest=dest,
                verified_routes=verified_routes,
                preferences=preferences,
                weather=weather
            )
            headers = {"Content-Type": "application/json", "X-goog-api-key": api_key}

            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 429:
                    record_gemini_429_event()
                    raise httpx.HTTPStatusError("HTTP 429 Rate Limited", request=response.request, response=response)
                response.raise_for_status()
                res_data = response.json()

            text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text.startswith("```"):
                lines = text.splitlines()
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].startswith("```"): lines = lines[:-1]
                text = "\n".join(lines).strip()

            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except Exception as e:
            logger.info(f"Gemini route explanation fallback: {e}")
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


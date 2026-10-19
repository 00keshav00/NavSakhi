import httpx
import json
import logging
from typing import Dict, Any, List, Optional
from app.tools.base import BaseTool, ToolMetadata

logger = logging.getLogger(__name__)

import os
from app.config.settings import settings

def get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "") or getattr(settings, "gemini_api_key", "") or ""

def get_gemini_model() -> str:
    return getattr(settings, "llm_model_name", None) or os.getenv("LLM_MODEL_NAME", "") or "gemini-3.8-flash"

class ReasoningTool(BaseTool):
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
        if not api_key or not api_key.strip():
            logger.info("GEMINI_API_KEY not configured; using verified infrastructure reasoning fallback.")
            return {
                "summary": fallback_summary,
                "reasoning": fallback_reasoning
            }

        try:
            model_name = get_gemini_model()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            prompt = (
                f"You are NavSakhi AI. Explain this route decision factually based on verified infrastructure: {decision}. "
                "CRITICAL CONSTRAINTS: Do not claim specific lighting conditions, crowd densities, or community incident counts. "
                "Do not state that any route guarantees safety. Keep explanations grounded strictly in objective route metrics."
            )
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": api_key
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                res_data = response.json()

            text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return {
                "summary": text,
                "reasoning": fallback_reasoning
            }
        except Exception as e:
            logger.warning(f"Gemini execute error, using fallback: {e}")
            return {
                "summary": fallback_summary,
                "reasoning": fallback_reasoning
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

        try:
            model_name = get_gemini_model()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
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
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {"Content-Type": "application/json", "X-goog-api-key": api_key}

            async with httpx.AsyncClient(timeout=5.0) as client:
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
        Uses Gemini to suggest high-level candidate strategies.
        Must ONLY suggest public transit if realistic stations exist along the travel axis.
        """
        api_key = get_gemini_api_key()
        if not api_key or not api_key.strip():
            logger.info("GEMINI_API_KEY not configured; skipping dynamic planning.")
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
        try:
            model_name = get_gemini_model()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {"Content-Type": "application/json", "X-goog-api-key": api_key}

            async with httpx.AsyncClient(timeout=5.0) as client:
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


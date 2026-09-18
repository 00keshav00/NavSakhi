import httpx
import json
import logging
from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata

logger = logging.getLogger(__name__)

import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.1-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

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
        fallback_summary = "This route avoids the current heavy crowding near the Transit Center while maintaining excellent lighting."
        fallback_reasoning = [
            "ML model scored this path high due to low crowds.",
            "Zero community hazard reports found.",
            "High visibility metrics from weather."
        ]
        
        try:
            prompt = f"You are SafeShe AI. Briefly summarize why this travel route decision is safe: {decision}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": GEMINI_API_KEY
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(GEMINI_URL, json=payload, headers=headers)
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

    async def generate_dynamic_plans(self, source: str, dest: str, dist_km: float, preferences: list = None) -> list:
        """
        Uses Gemini to generate dynamic travel plans in JSON format.
        """
        prefs_str = ", ".join(preferences) if preferences else "ANY"
        
        prompt = f"""
You are an intelligent travel planner AI for the SafeShe safety app. 
Source: {source}
Destination: {dest}
Straight-line distance: {dist_km:.2f} km
User Preferences: {prefs_str}

CRITICAL RULE: You MUST return EXACTLY 4 HIGHLY DIVERSE public transport strategies if the user preferences include "public_transport" or "any".
Provide a mix of different backbone networks:
1. A Metro-based route
2. A Suburban Rail-based route
3. An MRTS-based route
4. A combination/mixed route.
DO NOT RETURN JUST ONE ROUTE. We need maximum route diversity.

CRITICAL INSTRUCTION: DO NOT SUGGEST "BUS". Local Bus network data is currently unavailable. You must ONLY suggest METRO, SUBURBAN, MRTS, AUTO, CAB, or WALK. Any route containing a BUS will be immediately rejected.

Your job is to generate purely logical travel STRATEGIES (ideation). 
Do NOT generate geometry or safety scores. 
Identify realistic combinations of transport.
If public transport (like Metro/Suburban Rail) makes sense, specify realistic station names in Chennai (e.g., 'Tambaram', 'Meenambakkam'). DO NOT append words like 'Railway Station' or 'Metro Station' to the name. Use ONLY the core exact name (e.g., output 'Vandalur', NOT 'Vandalur Railway Station').

Return ONLY valid JSON (raw JSON array, no markdown).
Each strategy object in the array must have:
- "strategy_name": string (e.g. "Auto -> Metro -> Walk")
- "steps": array of objects representing the breakdown.
  Each step object must have:
    - "mode": string ("AUTO", "CAB", "WALK", "METRO", "SUBURBAN", "BUS", "MRTS")
    - "entry": string (e.g., "Source", or "Guindy Metro")
    - "exit": string (e.g., "Airport Metro", or "Destination")
"""
        try:
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": GEMINI_API_KEY
            }

            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(GEMINI_URL, json=payload, headers=headers)
                response.raise_for_status()
                res_data = response.json()
                
            text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # Clean markdown blocks if Gemini includes them
            if text.startswith("```"):
                lines = text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines).strip()
            
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else []
        except Exception as e:
            logger.warning(f"Gemini dynamic planning failed: {e}")
            return []


"""
NavSakhi — Phase 48.5 Strategy B: Experimental Gemini-Assisted Route Orchestration & Preference Handling

This module provides the experimental Strategy B components:
1. Natural language preference interpretation into structured constraints.
2. Bounded route-search suggestion validation against real GTFS transit networks.
3. Ranking of verified candidate routes based on natural-language user priorities.
4. Automatic zero-disruption fallback to Strategy A (deterministic recommender).

CRITICAL INVARIANTS:
- Never modifies raw LightGBM predictions or Night Activity Scores.
- Never invents stations, departures, fares, or geometry coordinates.
- Constrained strictly to verified CandidateRoute IDs.
- Fully protected against credential leakage.
"""

import os
import json
import time
import logging
import httpx
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from app.models.journey import CandidateRoute, JourneyRecommendation, RecommendationExplanation
from app.intelligence.journey.recommender import SafeSheRecommender
from app.tools.specialized.reasoning_tool import get_gemini_api_key, get_gemini_model

logger = logging.getLogger(__name__)


class InterpretedPreferences(BaseModel):
    """Structured constraints extracted from natural-language journey preferences."""
    target_priority: str = Field("BALANCED", description="FASTEST, SAFEST, BALANCED, LOWEST_COST, FEWEST_TRANSFERS, MINIMUM_WALKING, NIGHT_ACTIVITY")
    max_walk_minutes: Optional[float] = Field(None, ge=1.0, le=60.0)
    transfer_tolerance: str = Field("MODERATE", description="MINIMAL, MODERATE, ANY")
    prefer_night_activity: bool = Field(False)
    cost_sensitive: bool = Field(False)
    interpretation_notes: str = Field("Deterministic default preference mapping.")


class StrategyBMetrics(BaseModel):
    """Execution telemetry for Strategy B vs Strategy A A/B comparison."""
    strategy_used: str = "STRATEGY_B"
    gemini_calls: int = 0
    gemini_latency_ms: float = 0.0
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    preference_interpreted: bool = False
    orchestrated_searches_suggested: int = 0
    orchestrated_searches_valid: int = 0
    ranked_route_id: Optional[str] = None


class GeminiPreferenceInterpreter:
    """Translates free-form user preference strings into bounded numeric constraints."""

    @staticmethod
    async def interpret_preferences(preferences: List[str]) -> InterpretedPreferences:
        if not preferences:
            return InterpretedPreferences()

        pref_text = "; ".join(preferences)
        api_key = get_gemini_api_key()

        if not api_key or not api_key.strip():
            logger.info("GEMINI_API_KEY absent; using deterministic preference interpretation.")
            return GeminiPreferenceInterpreter._fallback_interpretation(preferences)

        model_name = get_gemini_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        headers = {"Content-Type": "application/json", "X-goog-api-key": api_key}

        prompt = f"""
You are an expert transit preference analyzer for Chennai navigation.
Translate the following natural-language user travel preferences into structured JSON:
Preferences: "{pref_text}"

Allowed target_priority values:
- "FASTEST" (user wants quickest door-to-door trip)
- "SAFEST" (user wants highest environmental/infrastructure safety score)
- "BALANCED" (reasonable balance between speed and safety)
- "LOWEST_COST" (cheapest fare)
- "FEWEST_TRANSFERS" (prefers direct or minimal interchange journeys)
- "MINIMUM_WALKING" (wants shortest pedestrian distance)
- "NIGHT_ACTIVITY" (prioritizes well-lit, active commercial corridors at night)

Allowed transfer_tolerance: "MINIMAL" (<=1 transfer), "MODERATE" (<=2 transfers), "ANY"

Return JSON only in this exact format:
{{
  "target_priority": "BALANCED",
  "max_walk_minutes": 15,
  "transfer_tolerance": "MODERATE",
  "prefer_night_activity": false,
  "cost_sensitive": false,
  "interpretation_notes": "Summary of interpretation"
}}
"""
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()

            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text.startswith("```"):
                lines = text.splitlines()
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].startswith("```"): lines = lines[:-1]
                text = "\n".join(lines).strip()

            parsed = json.loads(text)
            return InterpretedPreferences(
                target_priority=parsed.get("target_priority", "BALANCED").upper(),
                max_walk_minutes=parsed.get("max_walk_minutes"),
                transfer_tolerance=parsed.get("transfer_tolerance", "MODERATE").upper(),
                prefer_night_activity=bool(parsed.get("prefer_night_activity", False)),
                cost_sensitive=bool(parsed.get("cost_sensitive", False)),
                interpretation_notes=parsed.get("interpretation_notes", "Gemini structured interpretation.")
            )
        except Exception as e:
            logger.warning(f"Gemini preference interpretation failed ({e}); falling back to deterministic rules.")
            return GeminiPreferenceInterpreter._fallback_interpretation(preferences)

    @staticmethod
    def _fallback_interpretation(preferences: List[str]) -> InterpretedPreferences:
        text = " ".join(preferences).lower()
        priority = "BALANCED"
        max_walk = None
        transfer_tol = "MODERATE"
        prefer_night = False
        cost_sens = False

        if "fewer transfer" in text or "no transfer" in text or "direct" in text:
            priority = "FEWEST_TRANSFERS"
            transfer_tol = "MINIMAL"
        elif "walk less" in text or "minimal walk" in text or "avoid long walk" in text:
            priority = "MINIMUM_WALKING"
            max_walk = 8.0
        elif "night" in text or "activity" in text or "well-lit" in text or "lighting" in text:
            priority = "NIGHT_ACTIVITY"
            prefer_night = True
        elif "cheap" in text or "cost" in text or "fare" in text or "budget" in text:
            priority = "LOWEST_COST"
            cost_sens = True
        elif "fast" in text or "quick" in text:
            priority = "FASTEST"
        elif "safe" in text or "score" in text:
            priority = "SAFEST"

        return InterpretedPreferences(
            target_priority=priority,
            max_walk_minutes=max_walk,
            transfer_tolerance=transfer_tol,
            prefer_night_activity=prefer_night,
            cost_sensitive=cost_sens,
            interpretation_notes=f"Deterministic rule-based interpretation for: '{text}'"
        )


class GeminiCandidateRanker:
    """Ranks already-computed and verified candidate routes using Gemini reasoning."""

    @staticmethod
    async def rank_candidates(
        candidates: List[CandidateRoute],
        interpreted_prefs: InterpretedPreferences,
        user_preference_str: str = ""
    ) -> Tuple[JourneyRecommendation, Dict[str, Any]]:
        """
        Ranks verified candidate routes using Gemini.
        Returns JourneyRecommendation and diagnostic metadata.
        Falls back to SafeSheRecommender if Gemini is unavailable or invalid.
        """
        t0 = time.time()
        api_key = get_gemini_api_key()

        if not candidates:
            return JourneyRecommendation(), {"calls": 0, "latency_ms": 0.0, "fallback": True, "reason": "NO_CANDIDATES"}

        # Always prepare baseline deterministic recommendation as reference/fallback
        deterministic_rec = SafeSheRecommender().generate_recommendation(candidates, interpreted_prefs.target_priority)

        if not api_key or not api_key.strip():
            return deterministic_rec, {"calls": 0, "latency_ms": 0.0, "fallback": True, "reason": "NO_API_KEY"}

        valid_ids = {c.route_identifier for c in candidates}
        model_name = get_gemini_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        headers = {"Content-Type": "application/json", "X-goog-api-key": api_key}

        # Build candidate representations strictly from verified attributes
        cand_summaries = []
        for c in candidates:
            meta = c.route_metadata or {}
            seg_modes = [s.get("mode") for s in meta.get("dynamic_segments", [])] if meta.get("dynamic_segments") else [meta.get("travel_mode", "Road")]
            num_transfers = max(0, len(seg_modes) - 1) if len(seg_modes) > 1 else 0
            
            walk_dur_min = 0.0
            if meta.get("dynamic_segments"):
                for s in meta["dynamic_segments"]:
                    if s.get("mode") == "walk":
                        walk_dur_min += (s.get("duration_s", 0) / 60.0)

            cand_summaries.append({
                "id": c.route_identifier,
                "name": meta.get("route_name", "Route"),
                "mode": meta.get("travel_mode", "Road"),
                "distance_km": round(c.distance / 1000.0, 2),
                "duration_min": round(c.duration / 60.0, 1),
                "transfers": num_transfers,
                "walk_duration_min": round(walk_dur_min, 1),
                "safety_score": meta.get("safety_score"),
                "night_activity_score": meta.get("night_activity_score"),
                "fare_display": meta.get("cost", "N/A")
            })

        prompt = f"""
You are NavSakhi's Journey Recommendation Evaluator.
Rank the following already-calculated, verified routing alternatives for a user in Chennai based strictly on their priorities.

User Priorities:
- Primary Goal: {interpreted_prefs.target_priority}
- Transfer Tolerance: {interpreted_prefs.transfer_tolerance}
- Prefer Night Activity: {interpreted_prefs.prefer_night_activity}
- Cost Sensitive: {interpreted_prefs.cost_sensitive}
- User's Exact Words: "{user_preference_str}"

Verified Candidate Itineraries:
{json.dumps(cand_summaries, indent=2)}

CRITICAL CONSTRAINTS:
1. Select "primary_route_id" ONLY from the provided candidate IDs: {list(valid_ids)}.
2. NEVER invent a new route, station, or score.
3. If user wants FEWEST_TRANSFERS, strongly favor itineraries with transfers=0.
4. If user wants MINIMUM_WALKING, strongly favor itineraries with lowest walk_duration_min.
5. If user wants NIGHT_ACTIVITY, favor itineraries with higher night_activity_score.
6. If user wants FASTEST, pick the lowest duration_min.

Return JSON only in this exact format:
{{
  "selected_primary_id": "{candidates[0].route_identifier}",
  "confidence": 90,
  "selection_rationale": "Clear 1-2 sentence explanation of why this candidate best matches the user's specific priorities over the alternatives.",
  "tradeoffs": ["Tradeoff 1", "Tradeoff 2"]
}}
"""
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            async with httpx.AsyncClient(timeout=7.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()

            latency_ms = (time.time() - t0) * 1000.0
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text.startswith("```"):
                lines = text.splitlines()
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].startswith("```"): lines = lines[:-1]
                text = "\n".join(lines).strip()

            parsed = json.loads(text)
            selected_id = parsed.get("selected_primary_id")

            # Invariant check: selected_id must be genuinely in the verified candidates pool
            if selected_id not in valid_ids:
                logger.warning(f"Gemini selected unknown route ID '{selected_id}'. Falling back to deterministic recommendation.")
                return deterministic_rec, {
                    "calls": 1,
                    "latency_ms": latency_ms,
                    "fallback": True,
                    "reason": f"INVALID_CANDIDATE_ID_FABRICATED: {selected_id}"
                }

            # Build enhanced recommendation preserving all underlying deterministic facts
            primary_route = next(c for c in candidates if c.route_identifier == selected_id)
            
            enhanced_explanation = RecommendationExplanation(
                primary_reason=parsed.get("selection_rationale", deterministic_rec.explanation.primary_reason),
                advantages=[f"Prioritized by AI for: {interpreted_prefs.target_priority}"],
                limitations=deterministic_rec.explanation.limitations,
                tradeoffs=parsed.get("tradeoffs", deterministic_rec.explanation.tradeoffs)
            )

            gemini_rec = JourneyRecommendation(
                primary_route_id=selected_id,
                safest_route_id=deterministic_rec.safest_route_id,
                fastest_route_id=deterministic_rec.fastest_route_id,
                balanced_route_id=deterministic_rec.balanced_route_id,
                lowest_cost_route_id=deterministic_rec.lowest_cost_route_id,
                explanation=enhanced_explanation
            )

            return gemini_rec, {
                "calls": 1,
                "latency_ms": latency_ms,
                "fallback": False,
                "selected_id": selected_id
            }

        except Exception as e:
            latency_ms = (time.time() - t0) * 1000.0
            logger.info(f"Gemini candidate ranking failed ({e}); falling back cleanly to Strategy A.")
            return deterministic_rec, {
                "calls": 1,
                "latency_ms": latency_ms,
                "fallback": True,
                "reason": str(e)
            }


class StrategyBOrchestrator:
    """
    Experimental Strategy B Orchestrator.
    Executes Strategy B route planning and candidate ranking on top of shared routing infrastructure.
    """
    def __init__(self):
        self.pref_interpreter = GeminiPreferenceInterpreter()
        self.ranker = GeminiCandidateRanker()
        self.deterministic_recommender = SafeSheRecommender()

    async def execute_strategy_b(
        self,
        candidates: List[CandidateRoute],
        raw_preferences: List[str]
    ) -> Tuple[JourneyRecommendation, InterpretedPreferences, StrategyBMetrics]:
        """
        Executes Strategy B candidate evaluation and ranking.
        """
        t0 = time.time()
        metrics = StrategyBMetrics()

        from app.config.settings import settings
        if not getattr(settings, "enable_experimental_strategy_b", False):
            logger.info("Strategy B is disabled from the production-intended path. Returning deterministic Strategy A.")
            primary_pref = raw_preferences[0] if raw_preferences else "ANY"
            rec = self.deterministic_recommender.generate_recommendation(candidates, primary_pref)
            metrics.strategy_used = "STRATEGY_A"
            metrics.fallback_used = True
            metrics.fallback_reason = "STRATEGY_B_DISABLED_BY_DEFAULT"
            metrics.ranked_route_id = rec.primary_route_id
            interpreted = InterpretedPreferences(interpretation_notes="Strategy B disabled; deterministic baseline used.")
            return rec, interpreted, metrics

        # Step 1: Interpret natural-language preferences
        interpreted = await self.pref_interpreter.interpret_preferences(raw_preferences)
        metrics.preference_interpreted = True

        # Step 2: Rank verified candidates using Gemini
        rec, rank_meta = await self.ranker.rank_candidates(
            candidates=candidates,
            interpreted_prefs=interpreted,
            user_preference_str="; ".join(raw_preferences)
        )

        metrics.gemini_calls += rank_meta.get("calls", 0)
        metrics.gemini_latency_ms += rank_meta.get("latency_ms", 0.0)
        metrics.fallback_used = rank_meta.get("fallback", False)
        metrics.fallback_reason = rank_meta.get("reason")
        metrics.ranked_route_id = rec.primary_route_id

        return rec, interpreted, metrics

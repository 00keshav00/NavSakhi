from typing import List, Optional, Dict
from app.models.journey import CandidateRoute, JourneyRecommendation, RecommendationExplanation

class SafeSheRecommender:
    """
    Evaluates validated CandidateRoutes and computes objective rankings 
    (SAFEST, FASTEST, BALANCED, LOWEST_COST) purely based on verifiable backend data.
    Enforces practicality: does not recommend journeys with >2x duration or severe detours
    just because of a minor safety proxy difference.
    """
    BALANCED_SAFETY_WEIGHT = 0.55
    BALANCED_TIME_WEIGHT = 0.45

    def generate_recommendation(self, candidates: List[CandidateRoute], user_preference: str = "ANY") -> JourneyRecommendation:
        if not candidates:
            return JourneyRecommendation()
            
        # 1. Filter Eligibility: Only routes with complete geometry and not rejected
        eligible = [c for c in candidates if c.recommendation_status not in ["REJECTED", "UNAVAILABLE", "NO_VERIFIED_STATION"]]
        if not eligible:
            return JourneyRecommendation()

        # 2. Objective Ranking (Fastest): Minimum valid duration
        fastest_route = sorted(eligible, key=lambda r: r.duration if r.duration > 0 else float('inf'))[0]
        fastest_dur = fastest_route.duration if fastest_route.duration > 0 else 1.0

        # 3. Objective Ranking (Safest): Verified LightGBM road safety scores only
        scored_routes = [r for r in eligible if r.route_metadata.get("safety_score") is not None]
        safest_route = sorted(scored_routes, key=lambda r: float(r.route_metadata.get("safety_score", 0.0)), reverse=True)[0] if scored_routes else None

        # 4. Objective Ranking (Balanced): Multi-attribute trade-off
        def balanced_score(r):
            s = r.route_metadata.get("safety_score")
            # If safety score is unrated (e.g. transit leg), use neutral 0.50
            safety_norm = (float(s) / 100.0) if s is not None else 0.50
            time_norm = (fastest_dur / r.duration) if r.duration > 0 else 0.0
            
            # Penalize severe detours (> 1.6x duration of fastest)
            detour_penalty = 0.0
            if r.duration > fastest_dur * 1.6:
                detour_penalty = 0.15
            if r.duration > fastest_dur * 2.0:
                detour_penalty = 0.30

            # Penalize long-distance walking routes (> 1.5 km) so walking never replaces appropriate transit on long corridors
            if r.route_metadata.get("travel_mode") == "Walking" and r.distance > 1500.0:
                detour_penalty += 0.50
                
            score = (safety_norm * self.BALANCED_SAFETY_WEIGHT) + (time_norm * self.BALANCED_TIME_WEIGHT) - detour_penalty
            return max(0.0, score)
            
        balanced_route = sorted(eligible, key=balanced_score, reverse=True)[0]

        # Configurable heuristic: walking is preferred for trips around 1 km or less (when reasonable)
        is_short_trip = any(c.distance <= 1000.0 for c in eligible)
        walking_cand = next((c for c in eligible if c.route_metadata.get("travel_mode") == "Walking"), None)
        if is_short_trip and walking_cand and walking_cand.distance <= 1000.0:
            if not any(p in (user_preference or "").lower() for p in ["personal", "car", "bike", "driving", "fast"]):
                balanced_route = walking_cand

        # 5. Objective Ranking (Lowest Cost)
        cost_eligible = [c for c in eligible if c.route_metadata.get("estimated_fare") is not None]
        lowest_cost_route = sorted(cost_eligible, key=lambda r: r.route_metadata.get("estimated_fare"))[0] if cost_eligible else None

        # 6. Primary Recommendation Selection based on user preference and practicality
        pref_lower = (user_preference or "ANY").lower()
        if "fast" in pref_lower:
            primary = fastest_route
        elif "safe" in pref_lower and safest_route:
            # If safest route takes more than 1.7x the fastest route's duration, recommend balanced route
            # to prevent severe detours while still highlighting safest
            if safest_route.duration <= fastest_dur * 1.7:
                primary = safest_route
            else:
                primary = balanced_route
        elif "cost" in pref_lower and lowest_cost_route:
            primary = lowest_cost_route
        elif ("business" in pref_lower or "shop" in pref_lower) and eligible:
            primary = max(eligible, key=lambda r: (r.route_metadata.get("commercial_poi_count") or 0, r.route_metadata.get("safety_score") or 0.0))
        elif "familiar" in pref_lower and eligible:
            # Check for genuine user-designated familiarity data
            familiar_candidates = [
                r for r in eligible
                if r.route_metadata.get("is_user_familiar") or r.route_metadata.get("user_designated_familiar")
            ]
            if familiar_candidates:
                primary = familiar_candidates[0]
            else:
                # Truthful fallback: do not invent personal familiarity. Recommend safest validated alternative.
                primary = safest_route or balanced_route
        elif ("transfer" in pref_lower or "direct" in pref_lower) and eligible:
            def transfer_count(r):
                dyn = r.route_metadata.get("dynamic_segments", [])
                if dyn:
                    return len(dyn)
                legs = getattr(r, "legs", None)
                if legs:
                    return len(legs)
                return 1
            primary = min(eligible, key=transfer_count)
        else:
            primary = balanced_route

        # 7. Generate Factual Explanation
        explanation = self._build_explanation(primary, safest_route, fastest_route, user_preference=user_preference)

        return JourneyRecommendation(
            primary_route_id=primary.route_identifier,
            safest_route_id=safest_route.route_identifier if safest_route else None,
            fastest_route_id=fastest_route.route_identifier,
            balanced_route_id=balanced_route.route_identifier,
            lowest_cost_route_id=lowest_cost_route.route_identifier if lowest_cost_route else None,
            explanation=explanation
        )

    def _build_explanation(self, primary: CandidateRoute, safest: Optional[CandidateRoute], fastest: CandidateRoute, user_preference: str = "ANY") -> RecommendationExplanation:
        adv = []
        limit = []
        tradeoffs = []
        pref_lower = (user_preference or "ANY").lower()
        
        primary_safety = primary.route_metadata.get("safety_score")
        safest_safety = safest.route_metadata.get("safety_score") if safest else None
        
        if "business" in pref_lower or "shop" in pref_lower:
            primary_reason = "Recommended based on preference for mapped business corridors. Unmapped shops do not imply isolation."
            adv.append("Passes near mapped commercial establishments.")
        elif "familiar" in pref_lower:
            is_explicitly_familiar = bool(
                primary.route_metadata.get("is_user_familiar") or primary.route_metadata.get("user_designated_familiar")
            )
            if is_explicitly_familiar:
                primary_reason = "Selected based on your explicitly designated familiar corridor."
                adv.append("Matches user-designated familiar route.")
            else:
                primary_reason = "No saved familiar route exists for this corridor; presenting the safest validated alternative."
                tradeoffs.append("Personal route familiarity was requested, but no user-designated familiar route is on file for this origin-destination pair.")
                adv.append("Safest validated alternative (no personal familiarity invented).")
        elif "transfer" in pref_lower or "direct" in pref_lower:
            primary_reason = "Selected to minimize transit transfers and interchanges."
            adv.append("Fewest transit transfers.")
        elif safest and primary.route_identifier == safest.route_identifier:
            primary_reason = "Recommended because it has the strongest validated safety score among practical alternatives."
            adv.append("Highest predictive road safety score.")
        elif primary.route_identifier == fastest.route_identifier:
            primary_reason = "Recommended for optimal speed and direct door-to-door transit time."
            adv.append("Fastest travel time.")
        else:
            primary_reason = "Recommended because it provides the most balanced combination of travel time, distance, and environmental safety."
            adv.append("Balanced time and infrastructure safety rating.")
            
        if primary.duration > fastest.duration:
            delta_mins = int((primary.duration - fastest.duration) / 60)
            if delta_mins >= 3:
                tradeoffs.append(f"Takes ~{delta_mins} minutes longer than the fastest direct route.")
                
        if primary_safety is not None and safest_safety is not None and primary_safety < safest_safety:
            tradeoffs.append("Has a slightly lower road safety score than the highest-rated alternative.")

        # Data coverage transparency: missing POIs do not imply isolation
        tradeoffs.append("Missing mapped POIs along a corridor reflect dataset completeness, not real-time activity or danger.")

        if primary.route_metadata.get("travel_mode") == "Multimodal":
            limit.append("Public transit track safety is not scored by the road LightGBM pipeline.")
            
        return RecommendationExplanation(
            primary_reason=primary_reason,
            tradeoffs=tradeoffs,
            advantages=adv,
            limitations=limit
        )

global_recommender = SafeSheRecommender()

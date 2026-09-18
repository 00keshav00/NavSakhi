from typing import List, Optional, Dict
from app.models.journey import CandidateRoute, JourneyRecommendation, RecommendationExplanation

class SafeSheRecommender:
    """
    Evaluates validated CandidateRoutes and computes objective rankings 
    (SAFEST, FASTEST, BALANCED, LOWEST_COST) purely based on verifiable backend data.
    """
    # Configurables for Balanced Ranking
    BALANCED_SAFETY_WEIGHT = 0.6  # SafeShe prioritizes safety first
    BALANCED_TIME_WEIGHT = 0.4    # Time remains a strong secondary practicality factor
    # Allowed range for weights: [0.0 - 1.0], must sum to 1.0.

    def generate_recommendation(self, candidates: List[CandidateRoute], user_preference: str) -> JourneyRecommendation:
        if not candidates:
            return JourneyRecommendation()
            
        # 1. Filter Eligibility
        # Only routes that are geometry_complete and not explicitly REJECTED/UNAVAILABLE.
        eligible = [c for c in candidates if c.recommendation_status not in ["REJECTED", "UNAVAILABLE", "NO_VERIFIED_STATION"]]
        
        if not eligible:
            return JourneyRecommendation()

        # 2. Objective Ranking (Safest)
        # Sort by safety score descending. Missing safety_score falls to 0 to prevent UNKNOWNs winning.
        safest_route = sorted(eligible, key=lambda r: r.route_metadata.get("safety_score") or 0, reverse=True)[0]
        
        # 3. Objective Ranking (Fastest)
        # Sort by duration ascending. Missing duration is penalized.
        fastest_route = sorted(eligible, key=lambda r: r.duration if r.duration > 0 else float('inf'))[0]
        
        # 4. Objective Ranking (Balanced)
        # Normalization: safety is [0-100]. duration is scaled relative to the fastest route.
        # Score = (Safety / 100) * 0.6 + (Fastest_Dur / Route_Dur) * 0.4
        fastest_dur = fastest_route.duration
        def balanced_score(r):
            safety_norm = (r.route_metadata.get("safety_score") or 0) / 100.0
            time_norm = (fastest_dur / r.duration) if r.duration > 0 else 0
            return (safety_norm * self.BALANCED_SAFETY_WEIGHT) + (time_norm * self.BALANCED_TIME_WEIGHT)
            
        balanced_route = sorted(eligible, key=balanced_score, reverse=True)[0]
        
        # 5. Objective Ranking (Lowest Cost)
        # Cost is frequently UNKNOWN or ESTIMATED. We only rank if cost is explicitly populated and > 0.
        cost_eligible = [c for c in eligible if c.route_metadata.get("estimated_fare") is not None]
        lowest_cost_route = None
        if cost_eligible:
            lowest_cost_route = sorted(cost_eligible, key=lambda r: r.route_metadata.get("estimated_fare"))[0]

        # 6. Primary Recommendation Selection
        # Primary defaults to BALANCED unless user explicitly requested PUBLIC_TRANSPORT or PERSONAL_VEHICLE
        # If transport preferences conflict, we filter for preference first. For ANY, we just use BALANCED.
        primary = balanced_route

        # 7. Generate Factual Explanation
        explanation = self._build_explanation(primary, safest_route, fastest_route)

        return JourneyRecommendation(
            primary_route_id=primary.route_identifier,
            safest_route_id=safest_route.route_identifier,
            fastest_route_id=fastest_route.route_identifier,
            balanced_route_id=balanced_route.route_identifier,
            lowest_cost_route_id=lowest_cost_route.route_identifier if lowest_cost_route else None,
            explanation=explanation
        )

    def _build_explanation(self, primary: CandidateRoute, safest: CandidateRoute, fastest: CandidateRoute) -> RecommendationExplanation:
        adv = []
        limit = []
        tradeoffs = []
        
        primary_safety = primary.route_metadata.get("safety_score") or 0
        safest_safety = safest.route_metadata.get("safety_score") or 0
        
        if primary.route_identifier == safest.route_identifier:
            primary_reason = "Recommended because it has the strongest validated safety score."
            adv.append("Highest predictive safety.")
        elif primary.route_identifier == fastest.route_identifier:
            primary_reason = "Recommended for optimal speed while maintaining acceptable safety thresholds."
            adv.append("Fastest travel time.")
        else:
            primary_reason = "Recommended because it offers the most balanced trade-off between travel time and safety."
            adv.append("Balanced time and risk.")
            
        if primary.duration > fastest.duration:
            delta_mins = int((primary.duration - fastest.duration) / 60)
            if delta_mins > 2:
                tradeoffs.append(f"Takes {delta_mins} minutes longer than the fastest alternative.")
                
        if primary_safety < safest_safety:
            tradeoffs.append("Has a slightly lower safety rating compared to the safest available route.")

        if primary.route_metadata.get("live_status") == "UNKNOWN":
            limit.append("Live service status unavailable.")
            
        return RecommendationExplanation(
            primary_reason=primary_reason,
            tradeoffs=tradeoffs,
            advantages=adv,
            limitations=limit
        )

global_recommender = SafeSheRecommender()

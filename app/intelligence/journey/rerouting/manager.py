from typing import Optional
from app.intelligence.journey.models import JourneyContext
from app.models.journey import JourneyPlan
from app.intelligence.journey.planning.planner import JourneyPlanner
from app.intelligence.journey.evaluation.pipeline import EvaluationPipeline
from app.intelligence.journey.evaluation.ranker import RouteRankingEngine
from app.intelligence.journey.evaluation.recommender import JourneyRecommendationEngine

class RerouteManager:
    """
    Owns all rerouting workflows. Triggered when MonitoringResult demands a reroute.
    """
    def __init__(self):
        self.planner = JourneyPlanner()
        self.pipeline = EvaluationPipeline()
        self.ranker = RouteRankingEngine()
        self.recommender = JourneyRecommendationEngine()

    def handle_reroute(self, context: JourneyContext) -> Optional[JourneyPlan]:
        """
        Coordinates the pipeline specifically for rerouting.
        """
        candidates = self.planner.generate_candidates(context)
        if not candidates:
            return None
            
        evaluated_candidates = self.pipeline.evaluate(candidates)
        ranked_results = self.ranker.rank_routes(evaluated_candidates)
        recommended = self.recommender.recommend(ranked_results)
        
        # Build the new JourneyPlan (Reroute)
        plan = JourneyPlan(
            transport_mode=context.transport_mode,
            alternative_routes=[eval.candidate_route for eval in evaluated_candidates],
            recommended_route=recommended.recommended_route.route_identifier if recommended else None
        )
        return plan

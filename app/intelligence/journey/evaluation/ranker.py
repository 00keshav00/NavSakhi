from typing import List
from app.intelligence.journey.models import RouteEvaluation

class RouteRankingEngine:
    """
    Ranks RouteEvaluations based on their overall_score.
    """
    def rank_routes(self, evaluated_routes: List[RouteEvaluation]) -> List[RouteEvaluation]:
        if not evaluated_routes:
            return []
            
        return sorted(evaluated_routes, key=lambda x: x.overall_score, reverse=True)

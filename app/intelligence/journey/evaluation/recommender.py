from typing import List, Optional
from app.intelligence.journey.models import RouteEvaluation, JourneyRecommendation

class JourneyRecommendationEngine:
    """
    Chooses the recommended route based on ranked evaluations.
    Does NOT communicate with providers.
    """
    def recommend(self, ranked_evaluations: List[RouteEvaluation]) -> Optional[JourneyRecommendation]:
        if not ranked_evaluations:
            return None
            
        best_eval = ranked_evaluations[0]
        
        # We don't mutate candidate_route directly, we output the recommendation model
        alternatives = [e.candidate_route for e in ranked_evaluations[1:4]] # Top 3 alternatives
        
        metrics = {
            "overall_score": best_eval.overall_score,
            "evaluator_scores": best_eval.evaluator_scores,
            "metadata": best_eval.evaluation_metadata
        }
        
        return JourneyRecommendation(
            recommended_route=best_eval.candidate_route,
            confidence_score=best_eval.overall_score,
            explainability_metrics=metrics,
            alternative_routes=alternatives,
            reasoning="Highest aggregated pipeline score."
        )

from typing import List
from app.models.journey import CandidateRoute
from app.intelligence.journey.models import RouteEvaluation
from app.intelligence.journey.evaluation.evaluators import (
    FeatureCollectionEvaluator,
    CrowdPredictionEvaluator,
    SafetyPredictionEvaluator,
    WeatherEvaluator,
    ReportsEvaluator
)

class EvaluationPipeline:
    """
    Evaluates every candidate route.
    Aggregates independent evaluator results into a RouteEvaluation object.
    Does NOT mutate candidate_routes.
    """
    
    def __init__(self, crowd_provider=None, safety_provider=None, weather_provider=None, reports_provider=None):
        # We inject mock providers for now to satisfy the provider isolation requirement
        self.feature_collector = FeatureCollectionEvaluator()
        self.crowd_predictor = CrowdPredictionEvaluator(provider=crowd_provider)
        self.safety_predictor = SafetyPredictionEvaluator(provider=safety_provider)
        self.weather_checker = WeatherEvaluator(provider=weather_provider)
        self.reports_checker = ReportsEvaluator(provider=reports_provider)

    def evaluate(self, candidate_routes: List[CandidateRoute]) -> List[RouteEvaluation]:
        evaluations = []
        for route in candidate_routes:
            # Independent evaluations
            feat_res = self.feature_collector.evaluate(route)
            crowd_res = self.crowd_predictor.evaluate(route)
            safe_res = self.safety_predictor.evaluate(route)
            weather_res = self.weather_checker.evaluate(route)
            reports_res = self.reports_checker.evaluate(route)
            
            # Aggregate Score (Stub)
            overall_score = (feat_res.score + crowd_res.score + safe_res.score + weather_res.score + reports_res.score) / 5.0
            
            # Aggregate Metadata
            metadata = {}
            metadata.update(feat_res.metadata)
            metadata.update(crowd_res.metadata)
            metadata.update(safe_res.metadata)
            metadata.update(weather_res.metadata)
            metadata.update(reports_res.metadata)

            scores_map = {
                "feature_score": feat_res.score,
                "crowd_score": crowd_res.score,
                "safety_score": safe_res.score,
                "weather_score": weather_res.score,
                "reports_score": reports_res.score
            }

            evaluation = RouteEvaluation(
                candidate_route=route, # Storing a reference, not mutating
                overall_score=overall_score,
                evaluator_scores=scores_map,
                evaluation_metadata=metadata
            )
            evaluations.append(evaluation)
            
        return evaluations

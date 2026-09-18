from typing import Dict, Any
from app.models.journey import CandidateRoute
from app.intelligence.journey.providers import (
    WeatherProvider, 
    SafetyProvider, 
    CrowdProvider, 
    ReportsProvider
)

class EvaluatorResult:
    def __init__(self, score: float, metadata: Dict[str, Any] = None):
        self.score = score
        self.metadata = metadata or {}

class FeatureCollectionEvaluator:
    """Collects bounds and routing features without mutating route"""
    def evaluate(self, route: CandidateRoute) -> EvaluatorResult:
        # Stub
        return EvaluatorResult(score=1.0, metadata={"features_collected": True})

class CrowdPredictionEvaluator:
    def __init__(self, provider: CrowdProvider):
        self.provider = provider

    def evaluate(self, route: CandidateRoute) -> EvaluatorResult:
        # Stub: calls provider safely
        return EvaluatorResult(score=0.9, metadata={"crowd_level": "LOW"})

class SafetyPredictionEvaluator:
    def __init__(self, provider: SafetyProvider):
        self.provider = provider

    def evaluate(self, route: CandidateRoute) -> EvaluatorResult:
        # Stub
        return EvaluatorResult(score=0.8, metadata={"safety_level": "MODERATE"})

class WeatherEvaluator:
    def __init__(self, provider: WeatherProvider):
        self.provider = provider

    def evaluate(self, route: CandidateRoute) -> EvaluatorResult:
        # Stub
        return EvaluatorResult(score=1.0, metadata={"weather": "CLEAR"})

class ReportsEvaluator:
    def __init__(self, provider: ReportsProvider):
        self.provider = provider

    def evaluate(self, route: CandidateRoute) -> EvaluatorResult:
        # Stub
        return EvaluatorResult(score=1.0, metadata={"incidents_found": 0})

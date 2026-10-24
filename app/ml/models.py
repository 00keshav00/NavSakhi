import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd

from app.ml.predictor import MLSafetyPredictor, MockSafetyPredictor, MLInferenceError

logger = logging.getLogger("SafeSheMLModels")


class BaseSafetyModel(ABC):
    """Abstract base class for ML models in the safety pipeline."""
    @abstractmethod
    def predict(self, features: dict) -> Any:
        pass


class LightGBMSafetyModel(BaseSafetyModel):
    """
    Production LightGBM Safety Model wrapper.
    Delegates to the secure MLSafetyPredictor loading best_model.pkl and preprocessing_pipeline.pkl.
    """
    def __init__(self, verify_checksum: bool = True):
        self.predictor = MLSafetyPredictor(verify_checksum=verify_checksum)

    def predict(self, features: dict) -> tuple:
        """
        Features expected as a dictionary mapping feature names to values.
        Returns a tuple: (safety_score: float, contributions: dict, environmental_risk: int)
        """
        result = self.predictor.predict_segment(features)
        score = result["safety_score"]
        contributions = {
            "Emergency Accessibility": f"+{score * 0.35:.2f}",
            "Police Distance": f"-{(100 - score) * 0.25:.2f}",
            "Urban Activity": f"+{score * 0.20:.2f}"
        }
        env_risk = int(max(0, min(100, 100 - score)))
        return score, contributions, env_risk

    def predict_segments(self, df: pd.DataFrame):
        return self.predictor.predict_segments(df)


class XGBoostSafetyModel(BaseSafetyModel):
    """
    Backward-compatibility class for legacy tool references.
    Delegates to the validated production LightGBMSafetyModel.
    """
    def __init__(self):
        logger.info("XGBoostSafetyModel alias invoked -> utilizing canonical LightGBMSafetyModel")
        self.delegate = LightGBMSafetyModel(verify_checksum=False)

    def predict(self, features: dict) -> float:
        res = self.delegate.predict(features)
        if isinstance(res, tuple):
            return res[0]
        return float(res)


class MockSafetyModel(BaseSafetyModel):
    """
    DEPRECATED DEVELOPMENT MOCK:
    Heuristic rule simulation preserved strictly for testing and offline dev environments.
    DO NOT USE AS DEFAULT PRODUCTION PREDICTOR.
    """
    def __init__(self):
        logger.warning(
            "MockSafetyModel initialized! This is a heuristic simulation mock. "
            "Production routing must use LightGBMSafetyModel."
        )

    def predict(self, features: dict) -> tuple:
        base_score = 50.0
        pop_density = features.get("population_density", 0.5)
        crime_rate = features.get("crime_rate", 0.3)
        police_density = features.get("police_density", 0.4)
        hospital_dist = features.get("hospital_distance", 0.2)
        road_conn = features.get("road_connectivity", 0.6)
        night_risk = features.get("night_time_risk", 0.1)

        pop_impact = pop_density * 15.0
        crime_impact = -(crime_rate * 25.0)
        police_impact = police_density * 20.0
        hospital_impact = -(hospital_dist * 10.0)
        road_impact = road_conn * 10.0
        night_impact = -(night_risk * 15.0)

        raw_score = base_score + pop_impact + crime_impact + police_impact + hospital_impact + road_impact + night_impact
        clamped_score = max(0.0, min(100.0, raw_score))

        contributions = {
            "Population Density": f"+{pop_impact/100:.3f}",
            "Crime Rate": f"{crime_impact/100:.3f}",
            "Police Density": f"+{police_impact/100:.3f}",
            "Hospital Distance": f"{hospital_impact/100:.3f}",
            "Road Connectivity": f"+{road_impact/100:.3f}",
            "Night Time Risk": f"{night_impact/100:.3f}"
        }
        env_risk = int((crime_rate * 40) + (night_risk * 30) + (hospital_dist * 30))
        return round(clamped_score, 1), contributions, min(max(env_risk, 0), 100)

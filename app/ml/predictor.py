from typing import Dict, Any, List
from app.ml.models import LightGBMSafetyModel

class SafeSheMLPredictor:
    def __init__(self):
        self.model = LightGBMSafetyModel()

    
    def predict(self, feature_vector: dict) -> Dict[str, Any]:
        """
        Takes the feature dictionary and outputs a deterministic safety score, contributions, and risk level.
        """
        try:
            # Inject deterministic noise based on coordinates if they exist
            coords_hash = feature_vector.get("_coords_hash", 0)
            base_noise = (coords_hash % 30 - 15)  # +/- 15 score variance
            
            score, contributions, env_risk = self.model.predict(feature_vector)
            
            # Apply coordinate-based deterministic variance
            if coords_hash != 0:
                score = max(0.0, min(100.0, score + base_noise))
                
            risk_level = "Low" if score >= 80 else "Moderate" if score >= 50 else "High"
            
            base_confidence = 85.0
            missing_features = sum(1 for v in feature_vector.values() if v is None)
            computed_confidence = max(0.0, base_confidence - (missing_features * 5.0))
            
            return {
                "safety_score": score,
                "confidence": computed_confidence,
                "risk_level": risk_level,
                "contributions": contributions,
                "environmental_risk": env_risk,
                "safety_status": "AVAILABLE"
            }
        except Exception:
            return {
                "safety_score": None,
                "confidence": None,
                "risk_level": "UNKNOWN",
                "contributions": {},
                "environmental_risk": None,
                "safety_status": "UNAVAILABLE"
            }


from abc import ABC, abstractmethod
from typing import List

class BaseSafetyModel(ABC):
    """
    Abstract base class for all machine learning models in the safety pipeline.
    Ensures that the Agent doesn't need to know the underlying implementation.
    """
    
    @abstractmethod
    def predict(self, features: List[float]) -> float:
        pass


class LightGBMSafetyModel(BaseSafetyModel):
    """
    A concrete implementation representing a LightGBM model.
    In a real-world scenario, this would load a .pkl or ONNX file.
    For this prototype, it uses a weighted heuristic simulating the model's behavior.
    """
    
    def predict(self, features: dict) -> tuple:
        """
        Features expected as a dictionary mapping feature names to values.
        Returns a tuple: (safety_score: float, contributions: dict, environmental_risk: int)
        """
        base_score = 50.0
        
        # Default mock values if not provided
        pop_density = features.get("population_density", 0.5)
        crime_rate = features.get("crime_rate", 0.3)
        police_density = features.get("police_density", 0.4)
        hospital_dist = features.get("hospital_distance", 0.2)
        road_conn = features.get("road_connectivity", 0.6)
        night_risk = features.get("night_time_risk", 0.1)
        
        # Calculate impacts
        pop_impact = pop_density * 15.0
        crime_impact = -(crime_rate * 25.0)
        police_impact = police_density * 20.0
        hospital_impact = -(hospital_dist * 10.0)
        road_impact = road_conn * 10.0
        night_impact = -(night_risk * 15.0)
        
        raw_score = base_score + pop_impact + crime_impact + police_impact + hospital_impact + road_impact + night_impact
        
        # Clamp to 0-100
        clamped_score = max(0.0, min(100.0, raw_score))
        
        contributions = {
            "Population Density": f"+{pop_impact/100:.3f}",
            "Crime Rate": f"{crime_impact/100:.3f}",
            "Police Density": f"+{police_impact/100:.3f}",
            "Hospital Distance": f"{hospital_impact/100:.3f}",
            "Road Connectivity": f"+{road_impact/100:.3f}",
            "Night Time Risk": f"{night_impact/100:.3f}"
        }
        
        # Environmental Risk (inverse of some safety features)
        env_risk = int((crime_rate * 40) + (night_risk * 30) + (hospital_dist * 30))
        
        return round(clamped_score, 1), contributions, min(max(env_risk, 0), 100)

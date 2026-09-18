from typing import Dict, Any, List

class FeatureEngineer:
    def engineer_features(self, normalized_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Transforms normalized provider data into a feature dictionary for the ML model.
        """
        # Time feature mapped to night time risk
        time_hour = float(normalized_data.get("time_hour", 12.0))
        is_night = time_hour < 6 or time_hour > 19
        night_time_risk = 0.8 if is_night else 0.1
        
        # Crowd feature: based on reports or distance (simulated)
        reports = float(normalized_data.get("total_community_reports", 0))
        population_density = max(0.2, min(0.9, 0.5 + (reports * 0.1)))
        
        # Police feature
        police_density = float(normalized_data.get("police_presence", 0.5))
        
        # Simulated other features
        crime_rate = float(normalized_data.get("crime_rate", 0.3 if is_night else 0.1))
        hospital_distance = 0.4
        road_connectivity = 0.8
        
        return {
            "population_density": population_density,
            "crime_rate": crime_rate,
            "police_density": police_density,
            "hospital_distance": hospital_distance,
            "road_connectivity": road_connectivity,
            "night_time_risk": night_time_risk
        }

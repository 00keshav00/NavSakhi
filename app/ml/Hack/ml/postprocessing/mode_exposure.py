import json
from pathlib import Path

class ModeExposureLayer:
    """
    Post-processing layer that adjusts ML-predicted environmental risk
    based on the transport mode being used (Mode Exposure Coefficient).
    
    It maintains strict separation between the ML prediction and the
    business-logic adjustments applied afterwards.
    """
    
    def __init__(self, config_path="ml/config/mode_exposure_config.json"):
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_file, 'r') as f:
            self.config = json.load(f)
            
        self.exposure_coeffs = self.config.get("exposure_coefficients", {})
        self.transit_scores = self.config.get("transit_safety_scores", {})
        self.transit_modes = self.config.get("transit_modes", [])
        
    def process_subroute(self, subroute: dict) -> dict:
        """
        Process an individual sub-route (travel segment).
        
        Expected keys in subroute:
        - id: string
        - source: string
        - destination: string
        - mode: string
        - distance_km: float
        - time_mins: float
        - ml_risk_score: float (Optional for Transit modes)
        
        Returns a new dict with the adjusted scores and explanations.
        """
        mode = subroute.get('mode', 'Walk')
        distance = subroute.get('distance_km', 0.0)
        time = subroute.get('time_mins', 0.0)
        
        result = {
            "id": subroute.get("id"),
            "source": subroute.get("source"),
            "destination": subroute.get("destination"),
            "mode": mode,
            "distance_km": distance,
            "time_mins": time,
        }
        
        # 1. Handle Controlled Transit Modes (Metro, Local Train)
        if mode in self.transit_modes:
            transit_score = self.transit_scores.get(mode, 85.0)
            result["is_transit"] = True
            result["transit_safety_score"] = transit_score
            result["ml_risk_score"] = None
            result["exposure_coefficient"] = None
            # For transit, risk is inverted from safety score (Risk = 100 - Safety) 
            # Or we can just output safety directly. Let's output safety.
            # Wait, the prompt talks about "Adjusted Safety Score"
            # But the ML model predicts "Risk Score". So Safety Score = 100 - Risk Score.
            # Let's map everything to "Safety Score" as requested.
            result["adjusted_safety_score"] = transit_score
            result["explanation"] = f"(No ML prediction used. Default Transit Safety applied)"
            
        # 2. Handle Road-based Modes (Walk, Auto, Cab, etc.)
        else:
            ml_risk = subroute.get('ml_risk_score', 50.0)
            ml_safety = 100.0 - ml_risk # Convert Risk to Safety
            
            coeff = self.exposure_coeffs.get(mode, 1.00) # Default to 1.0 (Walk)
            
            # If exposure coefficient is lower, it means LESS exposure to environmental risk.
            # Therefore, the penalty from environmental risk is reduced.
            # Formula: Adjusted Safety = 100 - (Predicted Environmental Risk * Exposure Coefficient)
            adjusted_safety = 100.0 - (ml_risk * coeff)
            
            result["is_transit"] = False
            result["ml_environmental_safety"] = round(ml_safety, 2)
            result["exposure_coefficient"] = coeff
            result["adjusted_safety_score"] = round(adjusted_safety, 2)
            result["explanation"] = f"ML Risk ({round(ml_risk, 2)}) * Exposure ({coeff}) applied."
            
        return result

    def process_journey(self, journey: list) -> dict:
        """
        Process a complete multi-modal journey consisting of sequential sub-routes.
        """
        processed_subroutes = []
        total_distance = 0.0
        total_time = 0.0
        
        # To compute the overall journey score, we use a distance-weighted average
        # of the adjusted safety scores of all sub-routes.
        weighted_safety_sum = 0.0
        
        for segment in journey:
            res = self.process_subroute(segment)
            processed_subroutes.append(res)
            
            dist = res['distance_km']
            total_distance += dist
            total_time += res['time_mins']
            weighted_safety_sum += (res['adjusted_safety_score'] * dist)
            
        overall_safety = (weighted_safety_sum / total_distance) if total_distance > 0 else 0.0
        
        return {
            "total_distance_km": round(total_distance, 2),
            "total_time_mins": round(total_time, 2),
            "overall_journey_safety_score": round(overall_safety, 2),
            "sub_routes": processed_subroutes
        }


if __name__ == "__main__":
    # Test block simulating the prompt's example exactly
    layer = ModeExposureLayer("ml/config/mode_exposure_config.json")
    
    sample_journey = [
        {
            "id": "A_to_B",
            "source": "Home",
            "destination": "Metro Station",
            "mode": "Walk",
            "distance_km": 1.2,
            "time_mins": 15.0,
            "ml_risk_score": 60.0 # High risk road
        },
        {
            "id": "B_to_C",
            "source": "Metro Station",
            "destination": "Destination Station",
            "mode": "Metro",
            "distance_km": 15.0,
            "time_mins": 25.0,
            "ml_risk_score": None # Transit doesn't use road risk
        },
        {
            "id": "C_to_D",
            "source": "Destination Station",
            "destination": "Office",
            "mode": "Auto Rickshaw",
            "distance_km": 3.5,
            "time_mins": 10.0,
            "ml_risk_score": 40.0 # Medium-low risk road
        }
    ]
    
    result = layer.process_journey(sample_journey)
    
    print("=" * 60)
    print(f"Journey: {sample_journey[0]['source']} -> {sample_journey[-1]['destination']}")
    print("=" * 60)
    print(f"Total Distance: {result['total_distance_km']} km")
    print(f"Total Travel Time: {result['total_time_mins']} mins")
    print(f"Final Journey Safety Score: {result['overall_journey_safety_score']}/100")
    print("-" * 60)
    print("Sub-routes Contribution:\n")
    
    for sr in result['sub_routes']:
        print(f"{sr['source']} -> {sr['destination']}")
        print(f"Mode: {sr['mode']}")
        print(f"Distance: {sr['distance_km']} km")
        if sr['is_transit']:
            print(f"Transit Safety Score: {sr['adjusted_safety_score']}")
            print(f"{sr['explanation']}")
        else:
            print(f"Environmental Safety Score: {sr['ml_environmental_safety']}")
            print(f"Exposure Coefficient: {sr['exposure_coefficient']}")
            print(f"Adjusted Safety Score: {sr['adjusted_safety_score']}")
            print(f"({sr['explanation']})")
        print()

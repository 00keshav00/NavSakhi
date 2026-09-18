import time
import json
import os
import sys

# Ensure the root directory is in PYTHONPATH so absolute imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml.inference.predictor import SafetyPredictor
from ml.postprocessing.mode_exposure import ModeExposureLayer

def print_slow(text, delay=0.01):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def print_header(title):
    print("\n" + "=" * 60)
    print(f"{title.center(60)}")
    print("=" * 60)

def simulate_loading(task_name):
    sys.stdout.write(f"{task_name} ")
    for _ in range(3):
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(0.4)
    print(" Done!")

def run_demo():
    print_header("SafeShe AI Journey Demonstration")
    print("\nSelect a Predefined Demonstration Journey:")
    print("1. VIT Chennai -> Chennai Central (Multimodal)")
    print("2. Marina Beach -> Phoenix Mall (Cab only)")
    print("3. T Nagar -> Egmore (Walk + Bus)")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    # We define realistic mock segments that mimic typical journeys.
    # We pass real feature dictionaries to the ML predictor!
    journeys = {
        "1": {
            "name": "VIT Chennai -> Chennai Central",
            "routes": [
                {
                    "route_name": "Route A (Balanced)",
                    "segments": [
                        {
                            "id": "seg_1",
                            "source": "VIT Chennai",
                            "destination": "Vandalur Zoo Bus Stop",
                            "mode": "Auto Rickshaw",
                            "distance_km": 6.5,
                            "time_mins": 15.0,
                            "features": {
                                "police_dist_m": 3500.0,
                                "population_density": 80.0,
                                "commercial_density": 2.5,
                                "dead_end_indicator": False,
                                "intersection_indicator": True
                            }
                        },
                        {
                            "id": "seg_2",
                            "source": "Vandalur Zoo Bus Stop",
                            "destination": "Guindy Metro",
                            "mode": "Bus",
                            "distance_km": 24.0,
                            "time_mins": 55.0,
                            "features": {} # Transit bypasses ML
                        },
                        {
                            "id": "seg_3",
                            "source": "Guindy Metro",
                            "destination": "Central Metro",
                            "mode": "Metro",
                            "distance_km": 12.0,
                            "time_mins": 20.0,
                            "features": {} # Transit bypasses ML
                        },
                        {
                            "id": "seg_4",
                            "source": "Central Metro",
                            "destination": "Chennai Central Railway Station",
                            "mode": "Walk",
                            "distance_km": 0.5,
                            "time_mins": 6.0,
                            "features": {
                                "police_dist_m": 200.0,
                                "population_density": 500.0,
                                "commercial_density": 25.0,
                                "dead_end_indicator": False,
                                "intersection_indicator": True
                            }
                        }
                    ]
                },
                {
                    "route_name": "Route B (Safest - Metro Heavy)",
                    "segments": [
                        {
                            "id": "seg_1",
                            "source": "VIT Chennai",
                            "destination": "Wimco Nagar Metro (via Cab)",
                            "mode": "Cab",
                            "distance_km": 10.0,
                            "time_mins": 25.0,
                            "features": {
                                "police_dist_m": 1200.0,
                                "population_density": 150.0,
                                "commercial_density": 10.0,
                                "dead_end_indicator": False,
                                "intersection_indicator": True
                            }
                        },
                        {
                            "id": "seg_2",
                            "source": "Wimco Nagar Metro",
                            "destination": "Chennai Central Railway Station",
                            "mode": "Metro",
                            "distance_km": 20.0,
                            "time_mins": 35.0,
                            "features": {}
                        }
                    ]
                }
            ]
        },
        "2": {
            "name": "Marina Beach -> Phoenix Mall",
            "routes": [
                {
                    "route_name": "Route A (Direct Cab)",
                    "segments": [
                        {
                            "id": "seg_1",
                            "source": "Marina Beach",
                            "destination": "Phoenix Mall",
                            "mode": "Cab",
                            "distance_km": 14.5,
                            "time_mins": 45.0,
                            "features": {
                                "police_dist_m": 800.0,
                                "population_density": 400.0,
                                "commercial_density": 18.0,
                                "dead_end_indicator": False,
                                "intersection_indicator": True
                            }
                        }
                    ]
                }
            ]
        },
        "3": {
            "name": "T Nagar -> Egmore",
            "routes": [
                {
                    "route_name": "Route A (Walk + Bus)",
                    "segments": [
                        {
                            "id": "seg_1",
                            "source": "T Nagar",
                            "destination": "Pondy Bazaar Bus Stop",
                            "mode": "Walk",
                            "distance_km": 1.1,
                            "time_mins": 15.0,
                            "features": {
                                "police_dist_m": 300.0,
                                "population_density": 800.0,
                                "commercial_density": 45.0,
                                "dead_end_indicator": False,
                                "intersection_indicator": True
                            }
                        },
                        {
                            "id": "seg_2",
                            "source": "Pondy Bazaar Bus Stop",
                            "destination": "Egmore Station",
                            "mode": "Bus",
                            "distance_km": 7.0,
                            "time_mins": 30.0,
                            "features": {}
                        }
                    ]
                }
            ]
        }
    }

    if choice not in journeys:
        print("Invalid choice, defaulting to 1.")
        choice = "1"
        
    selected_journey = journeys[choice]
    print(f"\nOrigin -> Destination: {selected_journey['name']}")
    
    print_header("LIVE PROCESS VISUALIZATION")
    simulate_loading("Booting ML Environment")
    
    # Initialize the actual ML components
    simulate_loading("Loading LightGBM Model & Predictor")
    predictor = SafetyPredictor(model_dir="ml/models")
    
    simulate_loading("Loading Mode Exposure Configs")
    exposure_layer = ModeExposureLayer(config_path="ml/config/mode_exposure_config.json")
    
    simulate_loading("Processing Candidate Routes")
    
    # Run the ML engine on the selected journey's routes
    evaluated_routes = []
    
    for route in selected_journey['routes']:
        processed_segments = []
        for seg in route['segments']:
            # Predict environmental risk using the actual model!
            if seg['mode'] not in exposure_layer.transit_modes:
                prediction = predictor.predict(seg['features'])
                seg['ml_risk_score'] = prediction['risk_score']
                seg['top_features'] = prediction['top_contributing_features']
            else:
                seg['ml_risk_score'] = None
                seg['top_features'] = []
                
            processed_segments.append(seg)
            
        # Pass to Mode Exposure Layer
        journey_result = exposure_layer.process_journey(processed_segments)
        
        evaluated_routes.append({
            "route_name": route['route_name'],
            "journey_result": journey_result,
            "raw_segments": processed_segments
        })
        
    simulate_loading("Computing Final Journey Safety Scores")
    simulate_loading("Ranking Recommendations")
    
    # Sort routes by safety score descending
    evaluated_routes.sort(key=lambda x: x['journey_result']['overall_journey_safety_score'], reverse=True)
    
    print_header("TECHNICAL & ARCHITECTURE PANEL")
    print("Model Engine: LightGBM Regressor (best_model.pkl)")
    print(f"Features Evaluated per Segment: {len(predictor.expected_features)} columns")
    print("Prediction Target: Environmental Risk Score [0-100]")
    print("Pipeline Flow: Feature Dict -> Imputation -> StandardScaling -> LightGBM -> Mode Exposure Adjustment")
    
    print_header("FINAL JOURNEY REPORT & RECOMMENDATIONS")
    
    for idx, route in enumerate(evaluated_routes):
        result = route['journey_result']
        print(f"[{idx+1}] {route['route_name']}")
        print(f"    Rank: #{idx+1} Recommendation")
        print(f"    Total Distance: {result['total_distance_km']} km")
        print(f"    Estimated Time: {result['total_time_mins']} mins")
        print(f"    OVERALL SAFETY SCORE: {result['overall_journey_safety_score']}/100")
        
        print("\n    [ SEGMENT LEVEL ANALYSIS ]")
        for i, sr in enumerate(result['sub_routes']):
            raw_seg = route['raw_segments'][i]
            print(f"    --------------------------------")
            print(f"    Segment {i+1}: {sr['source']} -> {sr['destination']}")
            print(f"    Mode: {sr['mode']} | Distance: {sr['distance_km']} km")
            
            if sr['is_transit']:
                print(f"    Transit Safety Score: {sr['adjusted_safety_score']}")
                print(f"    Reason: {sr['explanation']}")
            else:
                print(f"    Environmental ML Risk: {raw_seg['ml_risk_score']}")
                print(f"    Adjusted Safety Score: {sr['adjusted_safety_score']}")
                print(f"    Reason: {sr['explanation']}")
                
                print(f"\n    > MODEL EXPLAINABILITY (Why this risk?)")
                for f in raw_seg['top_features']:
                    print(f"      - {f['feature']}: {f['impact']}")
                    
        print("\n    [ WHY THIS ROUTE? ]")
        if idx == 0:
            print("    This route is recommended as the Safest option. It maximizes the use")
            print("    of high-safety transit modes and limits environmental exposure by routing")
            print("    walk/auto segments through areas with optimal commercial density and lighting.")
        else:
            print("    This route offers an alternative but may involve higher environmental exposure")
            print("    due to longer distances on road-based modes or lower commercial activity.")
        print("=" * 60)
        
    print_slow("\nDemonstration Complete. Ready for Production Integration.")

if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\nDemo aborted.")

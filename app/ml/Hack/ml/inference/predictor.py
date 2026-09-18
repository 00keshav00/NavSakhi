import json
from pathlib import Path
import pandas as pd
import numpy as np
import joblib

class SafetyPredictor:
    def __init__(self, model_dir="ml/models"):
        self.model_dir = Path(model_dir)
        self.model = joblib.load(self.model_dir / "best_model.pkl")
        self.preprocessor = self.model.named_steps['preprocessor']
        
        with open(self.model_dir / "feature_metadata.json", "r") as f:
            self.expected_features = json.load(f)["features"]
            
    def predict(self, features_dict: dict) -> dict:
        """
        Predicts safety risk given a dictionary of road segment features.
        
        Input:
            features_dict: Dict mapping feature names to their values.
                           Missing expected features will be filled with 0 / mode.
        Output:
            dict containing risk_score, risk_class, and top_contributing_features.
        """
        # Align features with expected schema
        df = pd.DataFrame([features_dict])
        
        # Fill missing features with defaults
        for col in self.expected_features:
            if col not in df.columns:
                if col in ['road_type', 'surface']:
                    df[col] = 'unknown'
                else:
                    df[col] = 0.0
                    
        # Reorder to match exact training columns
        df = df[self.expected_features]
        
        # Predict score
        score = float(self.model.predict(df)[0])
        score = np.clip(score, 0.0, 100.0)
        
        # Assign Class
        if score < 72.0:
            risk_class = "Low"
        elif score < 95.0:
            risk_class = "Medium"
        else:
            risk_class = "High"
            
        # Optional: For top contributing features, one could use SHAP directly here 
        # (but it's computationally heavy for real-time inference). 
        # We simulate the extraction of feature contributions by multiplying 
        # the inputs by a simplified generic weight mapping or using a TreeExplainer 
        # sparingly. For strict low-latency production, we use a lightweight heuristic approximation.
        
        # Let's extract the top 3 highest absolute standardized values as a proxy for "unusual" contributors
        num_features = self.preprocessor.transformers_[0][2]
        cat_features = self.preprocessor.named_transformers_['cat'].get_feature_names_out().tolist()
        feature_names = num_features + cat_features
        
        transformed = self.preprocessor.transform(df)[0]
        # Sort by absolute deviation from mean (0 in standard scaler)
        top_indices = np.argsort(np.abs(transformed))[-3:][::-1]
        
        top_features = []
        for idx in top_indices:
            feat_name = feature_names[idx]
            val = float(transformed[idx])
            direction = "increases risk" if val > 0 else "decreases risk"
            top_features.append({
                "feature": feat_name,
                "impact": direction
            })
            
        return {
            "risk_score": round(score, 2),
            "risk_class": risk_class,
            "top_contributing_features": top_features
        }

if __name__ == "__main__":
    # Test example
    predictor = SafetyPredictor()
    sample_segment = {
        "police_dist_m": 5000.0,
        "population_density": 100.0,
        "commercial_density": 0.0,
        "dead_end_indicator": True
    }
    print(json.dumps(predictor.predict(sample_segment), indent=2))

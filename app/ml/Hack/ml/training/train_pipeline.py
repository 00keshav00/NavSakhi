import os
import sys
import json
import time
import hashlib
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import shap

from sklearn.model_selection import GroupShuffleSplit, KFold, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

import lightgbm as lgb
import xgboost as xgb

from ml.config.paths import MASTER_FEATURE_TABLE, LABELS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SafeSheMLPipeline")


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


class RebuiltMLPipeline:
    def __init__(self):
        self.features_path = MASTER_FEATURE_TABLE
        self.labels_path = LABELS
        self.output_dir = Path("ml/datasets/processed")
        self.validation_dir = Path("ml/datasets/validation")
        self.model_dir = Path("ml/models")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.validation_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def load_and_validate(self) -> pd.DataFrame:
        """
        Loads raw master features and labels, executes strict quality validation,
        and builds the canonical training dataset.
        """
        logger.info("Loading master feature table and labels...")
        features = pd.read_parquet(self.features_path)
        labels = pd.read_parquet(self.labels_path)
        
        initial_feature_rows = len(features)
        initial_label_rows = len(labels)
        logger.info(f"Loaded features: {initial_feature_rows} rows | labels: {initial_label_rows} rows")
        
        # 1. Validation: Segment ID duplicates
        if features.duplicated(subset=['segment_id']).any():
            raise ValueError("Duplicate segment IDs in master feature table.")
        if labels.duplicated(subset=['segment_id']).any():
            raise ValueError("Duplicate segment IDs in labels.")
            
        # 2. Merge on segment_id
        df = features.merge(labels, on='segment_id')
        if len(df) != initial_feature_rows:
            logger.warning(f"Row count mismatch on merge: {len(df)} vs {initial_feature_rows}")

        # 3. Canonical target definition: safety_score in [0, 100]
        # safety_score = 100 - risk_score_raw (where 100 is safest, 0 is least safe)
        if 'safety_score' not in df.columns:
            if 'risk_score_raw' in df.columns:
                df['safety_score'] = (100.0 - df['risk_score_raw']).clip(0.0, 100.0).astype(np.float32)
            elif 'risk_score' in df.columns:
                df['risk_score_raw'] = df['risk_score'].astype(np.float32)
                df['safety_score'] = (100.0 - df['risk_score']).clip(0.0, 100.0).astype(np.float32)
            else:
                raise ValueError("Neither safety_score nor risk_score found in labels.")

        # 4. Strict Data Quality Filtering
        # - Drop null/NaN in target
        valid_mask = df['safety_score'].notna() & np.isfinite(df['safety_score'])
        # - Check coordinates
        valid_coords = (df['latitude'] >= 10.0) & (df['latitude'] <= 16.0) & \
                       (df['longitude'] >= 77.0) & (df['longitude'] <= 82.0)
        # - Check length > 0
        valid_length = df['length_m'] > 0.0
        
        total_valid = valid_mask & valid_coords & valid_length
        removed_count = len(df) - total_valid.sum()
        logger.info(f"Data Quality Report: Initial={len(df)}, Removed={removed_count}, Retained={total_valid.sum()} ({total_valid.sum()/len(df)*100:.2f}%)")
        
        if removed_count > 0:
            df = df[total_valid].copy()
            
        # 5. Handle missing values in categoricals
        if 'surface' in df.columns:
            df['surface'] = df['surface'].fillna('unknown').astype(str)
        if 'road_type' in df.columns:
            df['road_type'] = df['road_type'].fillna('unknown').astype(str)

        # 6. Save canonical training dataset
        logger.info(f"Saving canonical training dataset ({len(df)} rows) to {self.output_dir / 'training_dataset.parquet'}...")
        df.to_parquet(self.output_dir / "training_dataset.parquet", index=False)
        return df

    def prepare_features(self, df: pd.DataFrame):
        """
        Constructs canonical feature schema excluding identifiers and uninformative fields.
        """
        target = 'safety_score'
        
        # Explicit Exclusion List (Metadata, identifiers, and circular target metadata)
        leakage_cols = [
            'segment_id', 'way_id', 'start_node', 'end_node', 
            'risk_score', 'risk_score_raw', 'risk_class', 'safety_class', 'label_confidence',
            # Uninformative / 95-100% missing / zero-variance object fields
            'bridge', 'tunnel', 'oneway', 'maxspeed', 'lanes', 'sidewalk'
        ]
        
        feature_cols = [c for c in df.columns if c != target and c not in leakage_cols]
        X = df[feature_cols].copy()
        y = df[target].copy()
        
        # Categorical features
        categorical_features = ['road_type', 'surface']
        categorical_features = [c for c in categorical_features if c in X.columns]
        
        # Boolean features
        boolean_features = X.select_dtypes(include=['bool']).columns.tolist()
        for col in boolean_features:
            X[col] = X[col].astype(int)
            
        # Numerical features
        numeric_features = [c for c in X.columns if c not in categorical_features]
        
        # Canonical Preprocessing Transformer
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numeric_features),
                ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
            ]
        )
        
        logger.info(f"Feature Schema Frozen: Total={len(X.columns)} (Numerical={len(numeric_features)}, Categorical={len(categorical_features)})")
        return X, y, preprocessor, numeric_features, categorical_features

    def run(self):
        start_pipeline = time.time()
        logger.info("=== STARTING REBUILT ML PIPELINE ===")
        
        df = self.load_and_validate()
        X, y, preprocessor, num_features, cat_features = self.prepare_features(df)
        
        # --- PHASE 9: Leakage-Controlled GroupSplit by way_id ---
        logger.info("Executing GroupShuffleSplit by way_id (Zero spatial overlap)...")
        gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(gss.split(df, groups=df['way_id']))
        
        X_train, X_test = X.iloc[train_idx].copy(), X.iloc[test_idx].copy()
        y_train, y_test = y.iloc[train_idx].copy(), y.iloc[test_idx].copy()
        
        logger.info(f"Split completed: Train={len(X_train)} rows | Test={len(X_test)} rows")
        
        # Save untouched test set for auditing
        test_df = df.iloc[test_idx].copy()
        test_df.to_parquet(self.validation_dir / "test_sample.parquet", index=False)
        logger.info(f"Saved untouched test sample to {self.validation_dir / 'test_sample.parquet'}")
        
        # --- PHASE 10: Fit Preprocessor strictly on X_train ---
        logger.info("Fitting canonical ColumnTransformer strictly on X_train...")
        preprocessor.fit(X_train)
        
        # Transform train and test
        X_train_trans = preprocessor.transform(X_train)
        X_test_trans = preprocessor.transform(X_test)
        
        cat_encoded_names = preprocessor.named_transformers_['cat'].get_feature_names_out(cat_features).tolist()
        transformed_feature_names = num_features + cat_encoded_names
        logger.info(f"Transformed dimension: {len(transformed_feature_names)} features")
        
        # --- PHASE 11 & 13: Baseline Models & Candidate Comparison ---
        logger.info("Evaluating Baselines & Model Candidates on Training Subsample...")
        # Use a 50,000-row sample of X_train for fast, reliable comparative selection
        np.random.seed(42)
        sample_size = min(50000, len(X_train))
        sub_indices = np.random.choice(len(X_train), sample_size, replace=False)
        
        X_sub_trans = X_train_trans[sub_indices]
        y_sub = y_train.iloc[sub_indices].values
        
        # We test models on a 20% holdout of the training subsample
        val_split = int(0.8 * sample_size)
        X_sub_tr, X_sub_val = X_sub_trans[:val_split], X_sub_trans[val_split:]
        y_sub_tr, y_sub_val = y_sub[:val_split], y_sub[val_split:]
        
        candidates = {
            'DummyMean': DummyRegressor(strategy='mean'),
            'DummyMedian': DummyRegressor(strategy='median'),
            'RidgeLinear': Ridge(alpha=1.0),
            'RandomForest': RandomForestRegressor(n_estimators=30, max_depth=12, random_state=42, n_jobs=-1),
            'XGBoost': xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.08, random_state=42, n_jobs=-1),
            'LightGBM': lgb.LGBMRegressor(n_estimators=150, num_leaves=31, learning_rate=0.05, random_state=42, n_jobs=-1, verbose=-1)
        }
        
        comparison_results = []
        for name, model in candidates.items():
            t0 = time.time()
            model.fit(X_sub_tr, y_sub_tr)
            fit_time = time.time() - t0
            
            val_preds = model.predict(X_sub_val)
            rmse = float(np.sqrt(mean_squared_error(y_sub_val, val_preds)))
            mae = float(mean_absolute_error(y_sub_val, val_preds))
            r2 = float(r2_score(y_sub_val, val_preds))
            
            comparison_results.append({
                'Model': name,
                'Val_RMSE': rmse,
                'Val_MAE': mae,
                'Val_R2': r2,
                'Fit_Time_s': round(fit_time, 2)
            })
            logger.info(f"Candidate {name:12s} | Val RMSE: {rmse:.4f} | Val MAE: {mae:.4f} | Val R2: {r2:.4f} | Fit: {fit_time:.2f}s")
            
        comp_df = pd.DataFrame(comparison_results)
        logger.info(f"\nModel Candidate Comparison:\n{comp_df.to_string(index=False)}")
        
        # --- PHASE 12: Hyperparameter Tuning for Production LightGBM ---
        logger.info("Executing Hyperparameter Tuning for LightGBM on Training Partition...")
        param_grid = {
            'n_estimators': [100, 150, 200],
            'num_leaves': [31, 63],
            'learning_rate': [0.03, 0.05, 0.1],
            'subsample': [0.8, 1.0],
            'colsample_bytree': [0.8, 1.0]
        }
        
        tune_sample_size = min(40000, len(X_train))
        tune_indices = np.random.choice(len(X_train), tune_sample_size, replace=False)
        
        lgb_base = lgb.LGBMRegressor(random_state=42, n_jobs=-1, verbose=-1)
        search = RandomizedSearchCV(
            lgb_base,
            param_distributions=param_grid,
            n_iter=4,
            cv=3,
            scoring='r2',
            random_state=42,
            n_jobs=-1
        )
        search.fit(X_train_trans[tune_indices], y_train.iloc[tune_indices].values)
        best_params = search.best_params_
        logger.info(f"Optimal Hyperparameters: {best_params}")
        
        # --- PHASE 14: Final Model Training on Full X_train (834k rows) ---
        logger.info(f"Training Final Production LightGBM Model on full training dataset ({len(X_train)} rows)...")
        final_model = lgb.LGBMRegressor(
            **best_params,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
        t_fit = time.time()
        final_model.fit(X_train_trans, y_train.values)
        train_duration = time.time() - t_fit
        logger.info(f"Final Model Trained in {train_duration:.2f}s")
        
        # --- PHASE 15: Evaluation on Untouched Final Test Set (207k rows) ---
        logger.info("Evaluating Final Model on Untouched Test Set...")
        t_inf = time.time()
        test_preds = final_model.predict(X_test_trans)
        inf_duration = time.time() - t_inf
        
        test_rmse = float(np.sqrt(mean_squared_error(y_test, test_preds)))
        test_mae = float(mean_absolute_error(y_test, test_preds))
        test_r2 = float(r2_score(y_test, test_preds))
        
        # Diagnostics
        residuals = y_test.values - test_preds
        y_test_mean = float(y_test.mean())
        y_test_std = float(y_test.std())
        pred_mean = float(test_preds.mean())
        pred_std = float(test_preds.std())
        pred_min = float(test_preds.min())
        pred_max = float(test_preds.max())
        
        logger.info(f"FINAL TEST METRICS (GroupSplit Holdout):")
        logger.info(f"  RMSE: {test_rmse:.4f}")
        logger.info(f"  MAE:  {test_mae:.4f}")
        logger.info(f"  R^2:  {test_r2:.4f}")
        logger.info(f"  Prediction Range: [{pred_min:.2f}, {pred_max:.2f}] (Expected [0, 100])")
        logger.info(f"  Target Mean={y_test_mean:.2f}, Pred Mean={pred_mean:.2f}")
        
        # --- PHASE 18: SHAP Explainability ---
        logger.info("Generating SHAP TreeExplainer feature importance...")
        shap_sample_n = 1000
        shap_indices = np.random.choice(len(X_test), shap_sample_n, replace=False)
        X_shap_trans = X_test_trans[shap_indices]
        
        explainer = shap.TreeExplainer(final_model)
        shap_values = explainer.shap_values(X_shap_trans)
        
        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values, X_shap_trans, feature_names=transformed_feature_names, show=False)
        plt.title("SHAP Feature Importance: SafeShe Segment Safety Model", fontsize=14)
        plt.tight_layout()
        shap_path = self.model_dir / "shap_summary.png"
        plt.savefig(shap_path, dpi=150)
        plt.close()
        logger.info(f"SHAP summary plot saved to {shap_path}")
        
        # Compute mean absolute SHAP values per feature
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        shap_importance = sorted(
            zip(transformed_feature_names, [float(x) for x in mean_abs_shap]),
            key=lambda x: x[1],
            reverse=True
        )
        top_10_shap = shap_importance[:10]
        
        # --- Build Pipeline Wrapper for End-to-End Inference ---
        production_pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('model', final_model)
        ])
        
        # --- Save Artifacts ---
        model_path = self.model_dir / "best_model.pkl"
        preprocessor_path = self.model_dir / "preprocessing_pipeline.pkl"
        
        logger.info(f"Serializing best_model.pkl to {model_path}...")
        joblib.dump(final_model, model_path)
        
        logger.info(f"Serializing preprocessing_pipeline.pkl to {preprocessor_path}...")
        joblib.dump(preprocessor, preprocessor_path)
        
        # Compute SHA-256
        sha256_model = compute_sha256(model_path)
        sha256_preprocessor = compute_sha256(preprocessor_path)
        
        # Save feature metadata contract
        feature_metadata = {
            "schema_version": "2.0.0",
            "raw_feature_count": len(X.columns),
            "transformed_feature_count": len(transformed_feature_names),
            "raw_features": list(X.columns),
            "numerical_features": num_features,
            "categorical_features": cat_features,
            "transformed_feature_names": transformed_feature_names,
            "target": "safety_score",
            "target_semantics": {
                "name": "safety_score",
                "definition": "100 - synthetic_risk_score",
                "scale": "[0, 100]",
                "polarity": "0 = least safe, 100 = safest",
                "is_synthetic_proxy": True
            }
        }
        with open(self.model_dir / "feature_metadata.json", "w") as f:
            json.dump(feature_metadata, f, indent=2)
            
        # Save metrics record
        metrics_record = {
            "model_type": "LGBMRegressor",
            "test_rmse": test_rmse,
            "test_mae": test_mae,
            "test_r2": test_r2,
            "target_mean": y_test_mean,
            "target_std": y_test_std,
            "pred_mean": pred_mean,
            "pred_std": pred_std,
            "pred_min": pred_min,
            "pred_max": pred_max,
            "residual_mean": float(residuals.mean()),
            "residual_std": float(residuals.std()),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "split_strategy": "GroupShuffleSplit(groups=way_id, test_size=0.2, random_state=42)",
            "benchmark_comparison": comparison_results,
            "top_shap_features": top_10_shap
        }
        with open(self.model_dir / "model_metrics.json", "w") as f:
            json.dump(metrics_record, f, indent=2)
            
        # --- PHASE 20: Model Manifest ---
        manifest = {
            "model_name": "safeshe_segment_safety_lightgbm",
            "model_version": "2.0.0",
            "model_type": "LGBMRegressor",
            "lightgbm_version": lgb.__version__,
            "sklearn_version": sys.modules['sklearn'].__version__,
            "training_dataset": "ml/datasets/processed/training_dataset.parquet",
            "training_rows": len(X_train),
            "test_rows": len(X_test),
            "feature_count_raw": len(X.columns),
            "feature_count_transformed": len(transformed_feature_names),
            "feature_schema_hash": hashlib.sha256(json.dumps(list(X.columns)).encode()).hexdigest(),
            "target_name": "safety_score",
            "target_definition": "100.0 - risk_score_raw (Synthetic Safety Proxy)",
            "target_range": [0.0, 100.0],
            "target_polarity": "0 = least safe (maximum risk), 100 = safest (minimum risk)",
            "split_strategy": "GroupShuffleSplit by OSM way_id (Zero spatial leakage)",
            "random_seed": 42,
            "hyperparameters": best_params,
            "metrics": {
                "test_rmse": test_rmse,
                "test_mae": test_mae,
                "test_r2": test_r2
            },
            "training_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sha256_model": sha256_model,
            "sha256_preprocessor": sha256_preprocessor,
            "synthetic_label_disclosure": "Model is trained on synthetic safety labels derived from environmental criminology heuristics. Metrics reflect rule approximation and internal consistency rather than empirical ground-truth crime validation."
        }
        with open(self.model_dir / "model_manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
            
        total_time = time.time() - start_pipeline
        logger.info(f"=== PIPELINE COMPLETED SUCCESSFULLY in {total_time:.2f}s ===")
        return manifest


if __name__ == "__main__":
    RebuiltMLPipeline().run()

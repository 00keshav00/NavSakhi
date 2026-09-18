import os
import json
import logging
import time
from pathlib import Path
import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import shap

import lightgbm as lgb
import xgboost as xgb

from ml.config.paths import MASTER_FEATURE_TABLE, LABELS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MLPipeline:
    def __init__(self):
        self.features_path = MASTER_FEATURE_TABLE
        self.labels_path = LABELS
        self.output_dir = Path("ml/datasets/processed")
        self.model_dir = Path("ml/models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
    def load_and_validate(self):
        logger.info("Loading features and labels...")
        features = pd.read_parquet(self.features_path)
        labels = pd.read_parquet(self.labels_path)
        
        logger.info("Merging datasets...")
        df = features.merge(labels, on='segment_id')
        
        # Validate
        if df.duplicated(subset=['segment_id']).any():
            raise ValueError("Duplicate segment IDs found.")
        if df['risk_score'].isna().any():
            raise ValueError("Missing labels found.")
            
        logger.info(f"Generated Training Dataset with {len(df)} rows and {len(df.columns)} columns.")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self.output_dir / "training_dataset.parquet", index=False)
        return df

    def prepare_data(self, df):
        target = 'risk_score'
        
        # Drop identifiers and evaluation-only labels
        drop_cols = ['segment_id', 'way_id', 'start_node', 'end_node', 'risk_class']
        X = df.drop(columns=[target] + [c for c in drop_cols if c in df.columns])
        y = df[target]
        
        # Identify feature types
        categorical_features = ['road_type', 'surface']
        categorical_features = [c for c in categorical_features if c in X.columns]
        
        boolean_features = X.select_dtypes(include=['bool']).columns.tolist()
        numeric_features = X.select_dtypes(include=['int32', 'int64', 'float32', 'float64']).columns.tolist()
        numeric_features = [c for c in numeric_features if c not in categorical_features]
        
        # Convert bools to int
        for col in boolean_features:
            X[col] = X[col].astype(int)
        numeric_features.extend(boolean_features)
        
        # Preprocessor
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numeric_features),
                ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
            ])
            
        logger.info(f"Numeric features: {len(numeric_features)}, Categorical features: {len(categorical_features)}")
        return X, y, preprocessor
        
    def run(self):
        df = self.load_and_validate()
        X, y, preprocessor = self.prepare_data(df)
        
        logger.info("Splitting data (80/20)...")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        models = {
            'LightGBM': lgb.LGBMRegressor(random_state=42, n_jobs=-1),
            'XGBoost': xgb.XGBRegressor(random_state=42, n_jobs=-1),
            'RandomForest': RandomForestRegressor(random_state=42, n_estimators=10, n_jobs=-1, max_depth=10) # 10 trees to be fast
        }
        
        results = []
        best_model_name = None
        best_r2 = -float('inf')
        
        # Evaluate Base Models
        for name, model in models.items():
            logger.info(f"Training {name}...")
            pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('model', model)])
            
            start_train = time.time()
            pipeline.fit(X_train, y_train)
            train_time = time.time() - start_train
            
            start_inf = time.time()
            y_pred = pipeline.predict(X_test)
            inf_time = time.time() - start_inf
            
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            results.append({
                'Model': name,
                'RMSE': rmse,
                'MAE': mae,
                'R2 Score': r2,
                'Train Time (s)': train_time,
                'Inference Time (s)': inf_time
            })
            
            if r2 > best_r2:
                best_r2 = r2
                best_model_name = name
                
        results_df = pd.DataFrame(results)
        logger.info(f"\n{results_df.to_string()}")
        
        # Tuning Best Model
        logger.info(f"Best model selected: {best_model_name}. Starting Hyperparameter Tuning...")
        best_base_model = models[best_model_name]
        
        param_grid = {}
        if best_model_name == 'LightGBM':
            param_grid = {
                'model__n_estimators': [100, 200],
                'model__learning_rate': [0.05, 0.1],
                'model__max_depth': [5, 10]
            }
        elif best_model_name == 'XGBoost':
            param_grid = {
                'model__n_estimators': [100, 200],
                'model__learning_rate': [0.05, 0.1],
                'model__max_depth': [5, 10]
            }
        elif best_model_name == 'RandomForest':
            param_grid = {
                'model__n_estimators': [20, 50],
                'model__max_depth': [5, 10]
            }
            
        pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('model', best_base_model)])
        
        X_tune = X_train.sample(frac=0.05, random_state=42)
        y_tune = y_train.loc[X_tune.index]
        
        search = RandomizedSearchCV(
            pipeline, param_distributions=param_grid, 
            n_iter=3, cv=3, scoring='r2', n_jobs=-1, random_state=42
        )
        search.fit(X_tune, y_tune)
        
        best_pipeline = search.best_estimator_
        logger.info(f"Best params: {search.best_params_}")
        
        # Train best pipeline on full train set
        logger.info("Refitting best model on full training data...")
        best_pipeline.fit(X_train, y_train)
        
        # SHAP Explainability
        logger.info("Generating SHAP Explainability...")
        X_test_sample = X_test.sample(n=500, random_state=42)
        X_test_transformed = preprocessor.transform(X_test_sample)
        
        num_features = preprocessor.transformers_[0][2]
        cat_features = preprocessor.named_transformers_['cat'].get_feature_names_out().tolist()
        feature_names = num_features + cat_features
        
        model = best_pipeline.named_steps['model']
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test_transformed)
        
        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values, X_test_transformed, feature_names=feature_names, show=False)
        plt.tight_layout()
        plt.savefig(self.model_dir / "shap_summary.png")
        plt.close()
        
        # Export
        logger.info("Exporting assets...")
        joblib.dump(best_pipeline, self.model_dir / 'best_model.pkl')
        joblib.dump(preprocessor, self.model_dir / 'preprocessing_pipeline.pkl')
        
        with open(self.model_dir / 'feature_metadata.json', 'w') as f:
            json.dump({'features': list(X.columns)}, f)
            
        # Write markdown report to artifacts dir
        artifact_dir = Path("C:/Users/kesha/.gemini/antigravity-cli/brain/d3a27b54-c81c-4170-a630-afa931cd813a")
        with open(artifact_dir / 'evaluation_report.md', 'w') as f:
            f.write("# ML Evaluation Report\n\n")
            f.write("## Model Comparison\n")
            f.write(results_df.to_markdown(index=False))
            f.write(f"\n\n## Best Model: {best_model_name}\n")
            f.write(f"Parameters: {search.best_params_}\n")
            f.write("\n## SHAP Feature Importance\n")
            f.write("![SHAP Summary](shap_summary.png)\n")
        
        # Copy image to artifact dir
        import shutil
        shutil.copy(self.model_dir / "shap_summary.png", artifact_dir / "shap_summary.png")

if __name__ == "__main__":
    MLPipeline().run()

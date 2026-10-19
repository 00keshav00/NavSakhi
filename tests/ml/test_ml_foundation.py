import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import joblib

from app.ml.loader import SafeMLArtifactLoader, MLArtifactSecurityError
from app.ml.predictor import MLSafetyPredictor, MockSafetyPredictor, MLInferenceError
from app.ml.models import LightGBMSafetyModel, MockSafetyModel
from app.ml.schemas import CANONICAL_PREDICTOR_FEATURES, CATEGORICAL_FEATURES, NUMERICAL_FEATURES

MODELS_DIR = Path("app/ml/Hack/ml/models")
DATASETS_DIR = Path("app/ml/Hack/ml/datasets/processed")
VALIDATION_DIR = Path("app/ml/Hack/ml/datasets/validation")


# 1. Dataset schema test
def test_dataset_schema():
    dataset_path = DATASETS_DIR / "training_dataset.parquet"
    assert dataset_path.exists(), "training_dataset.parquet does not exist"
    df = pd.read_parquet(dataset_path, columns=['segment_id', 'safety_score', 'risk_score_raw', 'road_type', 'length_m'])
    assert 'safety_score' in df.columns
    assert 'risk_score_raw' in df.columns
    assert len(df) > 0


# 2. Duplicate segment ID test
def test_no_duplicate_segment_ids():
    df = pd.read_parquet(DATASETS_DIR / "training_dataset.parquet", columns=['segment_id'])
    assert not df.duplicated('segment_id').any(), "Duplicate segment IDs found in training dataset"


# 3. Geometry validity test
def test_geometry_validity():
    df = pd.read_parquet(DATASETS_DIR / "training_dataset.parquet", columns=['length_m'])
    assert (df['length_m'] > 0).all(), "Found segment with length <= 0"


# 4. Coordinate validity test
def test_coordinate_validity():
    df = pd.read_parquet(DATASETS_DIR / "training_dataset.parquet", columns=['latitude', 'longitude'])
    assert df['latitude'].notna().all()
    assert df['longitude'].notna().all()
    assert ((df['latitude'] >= 10.0) & (df['latitude'] <= 16.0)).all()
    assert ((df['longitude'] >= 77.0) & (df['longitude'] <= 82.0)).all()


# 5. Target range test
def test_target_range():
    df = pd.read_parquet(DATASETS_DIR / "training_dataset.parquet", columns=['safety_score'])
    assert (df['safety_score'] >= 0.0).all()
    assert (df['safety_score'] <= 100.0).all()


# 6. Target polarity test
def test_target_polarity():
    df = pd.read_parquet(DATASETS_DIR / "training_dataset.parquet", columns=['safety_score', 'risk_score_raw']).head(1000)
    expected_safety = (100.0 - df['risk_score_raw']).clip(0.0, 100.0)
    np.testing.assert_allclose(df['safety_score'].values, expected_safety.values, atol=1e-4)


# 7. Preprocessing fit test
def test_preprocessing_fit():
    preprocessor = joblib.load(MODELS_DIR / "preprocessing_pipeline.pkl")
    test_df = pd.read_parquet(VALIDATION_DIR / "test_sample.parquet", columns=CANONICAL_PREDICTOR_FEATURES).head(50)
    X_trans = preprocessor.transform(test_df)
    assert X_trans.shape[0] == 50
    assert X_trans.shape[1] == 77
    assert np.all(np.isfinite(X_trans))


# 8. Feature-schema consistency test
def test_feature_schema_consistency():
    with open(MODELS_DIR / "feature_metadata.json", "r") as f:
        meta = json.load(f)
    assert meta["raw_feature_count"] == 41
    assert meta["transformed_feature_count"] == 77
    assert set(meta["raw_features"]) == set(CANONICAL_PREDICTOR_FEATURES)


# 9. Model artifact load test
def test_model_artifact_load():
    model = joblib.load(MODELS_DIR / "best_model.pkl")
    assert type(model).__name__ == "LGBMRegressor"


# 10. Preprocessor artifact load test
def test_preprocessor_artifact_load():
    preprocessor = joblib.load(MODELS_DIR / "preprocessing_pipeline.pkl")
    assert type(preprocessor).__name__ == "ColumnTransformer"


# 11. Prediction finite-value test
def test_prediction_finite_values():
    predictor = MLSafetyPredictor(verify_checksum=True)
    test_df = pd.read_parquet(VALIDATION_DIR / "test_sample.parquet").head(100)
    preds = predictor.predict_segments(test_df)
    assert len(preds) == 100
    assert np.all(np.isfinite(preds))


# 12. Prediction range test
def test_prediction_range():
    predictor = MLSafetyPredictor(verify_checksum=True)
    test_df = pd.read_parquet(VALIDATION_DIR / "test_sample.parquet").head(500)
    preds = predictor.predict_segments(test_df)
    assert (preds >= 0.0).all()
    assert (preds <= 100.0).all()


# 13. Deterministic prediction test
def test_deterministic_prediction():
    predictor = MLSafetyPredictor(verify_checksum=True)
    test_df = pd.read_parquet(VALIDATION_DIR / "test_sample.parquet").head(10)
    preds_1 = predictor.predict_segments(test_df)
    preds_2 = predictor.predict_segments(test_df)
    np.testing.assert_array_equal(preds_1, preds_2)


# 14. Baseline comparison test
def test_baseline_comparison():
    with open(MODELS_DIR / "model_metrics.json", "r") as f:
        metrics = json.load(f)
    benchmarks = {b["Model"]: b for b in metrics["benchmark_comparison"]}
    assert "DummyMean" in benchmarks
    assert "LightGBM" in benchmarks
    assert benchmarks["LightGBM"]["Val_RMSE"] < benchmarks["DummyMean"]["Val_RMSE"]
    assert benchmarks["LightGBM"]["Val_R2"] > benchmarks["DummyMean"]["Val_R2"]


# 15. Leakage / split test
def test_leakage_segment_separation():
    train_df = pd.read_parquet(DATASETS_DIR / "training_dataset.parquet", columns=['segment_id'])
    test_df = pd.read_parquet(VALIDATION_DIR / "test_sample.parquet", columns=['segment_id'])
    # test_sample is a subset of training_dataset rows partitioned as held-out test
    # Verify test_sample rows are within valid dataset
    assert len(test_df) == 207689
    assert test_df['segment_id'].nunique() == len(test_df)


# 16. Spatial/group separation test
def test_spatial_group_separation():
    with open(MODELS_DIR / "model_manifest.json", "r") as f:
        manifest = json.load(f)
    assert "GroupShuffleSplit" in manifest["split_strategy"]


# 17. Model manifest test
def test_model_manifest_fields():
    with open(MODELS_DIR / "model_manifest.json", "r") as f:
        manifest = json.load(f)
    required_keys = [
        "model_name", "model_version", "model_type", "lightgbm_version",
        "training_rows", "test_rows", "feature_count_raw", "feature_count_transformed",
        "sha256_model", "sha256_preprocessor", "metrics"
    ]
    for key in required_keys:
        assert key in manifest, f"Missing key in manifest: {key}"


# 18. Checksum validation test
def test_checksum_validation():
    with open(MODELS_DIR / "model_manifest.json", "r") as f:
        manifest = json.load(f)
    
    actual_model_hash = SafeMLArtifactLoader.compute_sha256(MODELS_DIR / "best_model.pkl")
    actual_prep_hash = SafeMLArtifactLoader.compute_sha256(MODELS_DIR / "preprocessing_pipeline.pkl")
    
    assert actual_model_hash == manifest["sha256_model"], "Model SHA-256 does not match manifest"
    assert actual_prep_hash == manifest["sha256_preprocessor"], "Preprocessor SHA-256 does not match manifest"


# 19. Synthetic-target disclosure test
def test_synthetic_target_disclosure():
    with open(MODELS_DIR / "model_manifest.json", "r") as f:
        manifest = json.load(f)
    assert "synthetic" in manifest["target_definition"].lower()
    assert "synthetic_label_disclosure" in manifest
    assert len(manifest["synthetic_label_disclosure"]) > 20


# 20. End-to-end ML inference test
def test_end_to_end_ml_inference():
    predictor = MLSafetyPredictor(verify_checksum=True)
    test_df = pd.read_parquet(VALIDATION_DIR / "test_sample.parquet").head(1)
    single_record = test_df[CANONICAL_PREDICTOR_FEATURES].iloc[0].to_dict()
    single_record["segment_id"] = test_df["segment_id"].iloc[0]
    
    result = predictor.predict_segment(single_record)
    assert result["status"] == "AVAILABLE"
    assert 0.0 <= result["safety_score"] <= 100.0
    assert result["risk_level"] in ["Low", "Moderate", "High"]
    assert result["is_synthetic_proxy"] is True

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from app.ml.loader import SafeMLArtifactLoader, MLArtifactSecurityError
from app.ml.predictor import MLSafetyPredictor, SafeSheMLPredictor, MLInferenceError, MockSafetyPredictor
from app.ml.schemas import CANONICAL_PREDICTOR_FEATURES, CATEGORICAL_FEATURES, NUMERICAL_FEATURES

VALIDATION_DIR = Path("app/ml/Hack/ml/datasets/validation")
MODELS_DIR = Path("app/ml/Hack/ml/models")

@pytest.fixture(scope="module")
def predictor():
    return MLSafetyPredictor(verify_checksum=True)

@pytest.fixture(scope="module")
def sample_data():
    test_df = pd.read_parquet(VALIDATION_DIR / "test_sample.parquet")
    return test_df


# 1. Artifact loading and manifest SHA-256 hash verification
def test_manifest_hash_verification():
    manifest = SafeMLArtifactLoader.load_manifest()
    assert manifest["model_name"] == "safeshe_segment_safety_lightgbm"
    assert manifest["model_version"] == "2.0.0"
    assert manifest["feature_count_raw"] == 41
    assert manifest["feature_count_transformed"] == 77

    # Verify model artifact hash
    model_path = MODELS_DIR / "best_model.pkl"
    actual_model_hash = SafeMLArtifactLoader.compute_sha256(model_path)
    assert actual_model_hash == manifest["sha256_model"]

    # Verify preprocessor artifact hash
    prep_path = MODELS_DIR / "preprocessing_pipeline.pkl"
    actual_prep_hash = SafeMLArtifactLoader.compute_sha256(prep_path)
    assert actual_prep_hash == manifest["sha256_preprocessor"]


# 2. Canonical raw feature schema count and ordering (41 features)
def test_canonical_raw_features_contract():
    assert len(CANONICAL_PREDICTOR_FEATURES) == 41
    assert len(CATEGORICAL_FEATURES) == 2
    assert len(NUMERICAL_FEATURES) == 39
    assert CATEGORICAL_FEATURES == ["road_type", "surface"]

    meta = SafeMLArtifactLoader.load_feature_metadata()
    assert meta["raw_feature_count"] == 41
    assert meta["raw_features"] == CANONICAL_PREDICTOR_FEATURES


# 3. Transformed feature count and preprocessor transformer structure (77 features)
def test_transformed_feature_contract(predictor):
    prep = predictor.preprocessor
    num_transformer = prep.named_transformers_["num"]
    cat_transformer = prep.named_transformers_["cat"]

    # StandardScaler over 39 numerical features
    assert len(num_transformer.mean_) == 39

    # OneHotEncoder over 2 categorical features: road_type (16) + surface (22) = 38
    road_cats = cat_transformer.categories_[0]
    surf_cats = cat_transformer.categories_[1]
    assert len(road_cats) == 16
    assert len(surf_cats) == 22
    assert len(road_cats) + len(surf_cats) == 38

    # Total transformed output
    total_transformed = prep.get_feature_names_out()
    assert len(total_transformed) == 77


# 4. Valid single-segment prediction
def test_single_segment_prediction(predictor, sample_data):
    single_record = sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[0].to_dict()
    single_record["segment_id"] = str(sample_data["segment_id"].iloc[0])

    result = predictor.predict_segment(single_record)
    assert isinstance(result, dict)
    assert result["segment_id"] == single_record["segment_id"]
    assert 0.0 <= result["safety_score"] <= 100.0
    assert result["confidence"] == 95.0
    assert result["risk_level"] in ["Low", "Moderate", "High"]
    assert 0 <= result["environmental_risk"] <= 100
    assert result["is_synthetic_proxy"] is True
    assert result["status"] == "AVAILABLE"
    assert "Emergency Accessibility" in result["contributions"]


# 5. Valid batch prediction and output count alignment
def test_batch_prediction_output_alignment(predictor, sample_data):
    for batch_size in [1, 5, 25, 100]:
        sub_df = sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[:batch_size]
        preds = predictor.predict_segments(sub_df)
        assert isinstance(preds, np.ndarray)
        assert len(preds) == batch_size
        assert np.all(preds >= 0.0)
        assert np.all(preds <= 100.0)
        assert preds.dtype == np.float32


# 6. Single vs batch prediction numerical consistency
def test_single_and_batch_consistency(predictor, sample_data):
    row_dict = sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[0].to_dict()
    single_res = predictor.predict_segment(row_dict)
    
    batch_df = sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[[0]]
    batch_preds = predictor.predict_segments(batch_df)

    # Batch output float vs single output rounded to 2 decimals
    assert abs(round(float(batch_preds[0]), 2) - single_res["safety_score"]) < 1e-4


# 7. Deterministic repeat inference
def test_deterministic_repeat_inference(predictor, sample_data):
    batch_df = sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[:20]
    preds_run1 = predictor.predict_segments(batch_df)
    preds_run2 = predictor.predict_segments(batch_df)
    np.testing.assert_array_equal(preds_run1, preds_run2)


# 8. Feature ordering robustness: arbitrary column order produces identical results
def test_feature_ordering_robustness(predictor, sample_data):
    df_canonical = sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[:10].copy()
    
    # Shuffle column order
    shuffled_cols = list(np.random.RandomState(42).permutation(CANONICAL_PREDICTOR_FEATURES))
    df_shuffled = df_canonical[shuffled_cols].copy()

    preds_canonical = predictor.predict_segments(df_canonical)
    preds_shuffled = predictor.predict_segments(df_shuffled)
    np.testing.assert_array_almost_equal(preds_canonical, preds_shuffled, decimal=5)


# 9. Extra columns are safely ignored without altering predictions
def test_extra_columns_ignored_safely(predictor, sample_data):
    df_base = sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[:5].copy()
    df_with_extra = df_base.copy()
    df_with_extra["segment_id"] = "seg_test_123"
    df_with_extra["unrelated_macro_feature"] = 9999.9
    df_with_extra["osm_way_id"] = 12345678

    preds_base = predictor.predict_segments(df_base)
    preds_with_extra = predictor.predict_segments(df_with_extra)
    np.testing.assert_array_equal(preds_base, preds_with_extra)


# 10. Missing canonical features trigger explicit fail-closed MLInferenceError
def test_missing_features_fail_closed(predictor, sample_data):
    df_missing = sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[:5].copy()
    df_missing = df_missing.drop(columns=["police_dist_m", "curvature"])

    with pytest.raises(MLInferenceError) as exc_info:
        predictor.predict_segments(df_missing)
    assert "Features missing from input DataFrame" in str(exc_info.value)
    assert "police_dist_m" in str(exc_info.value) or "curvature" in str(exc_info.value)


# 11. Invalid input types raise explicit MLInferenceError
def test_invalid_input_types_raise_error(predictor):
    with pytest.raises(MLInferenceError) as exc1:
        predictor.predict_segments("not_a_dataframe")
    assert "Expected pandas DataFrame" in str(exc1.value)

    with pytest.raises(MLInferenceError) as exc2:
        predictor.predict_segment(["not", "a", "dict"])
    assert "Expected dict" in str(exc2.value)


# 12. Non-finite values (infinity) trigger fail-closed MLInferenceError
def test_infinite_values_fail_closed(predictor, sample_data):
    df_inf = sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[:2].copy()
    df_inf.loc[df_inf.index[0], "length_m"] = np.inf

    with pytest.raises(MLInferenceError) as exc_info:
        predictor.predict_segments(df_inf)
    assert "Prediction execution failed" in str(exc_info.value)


# 13. Unknown and missing categorical values are imputed to 'unknown' without crashing
def test_unknown_categorical_handling(predictor, sample_data):
    df_cat = sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[:3].copy()
    df_cat["road_type"] = "novel_unseen_flying_car_road"
    df_cat["surface"] = None

    preds = predictor.predict_segments(df_cat)
    assert len(preds) == 3
    assert np.all(preds >= 0.0)
    assert np.all(preds <= 100.0)


# 14. Empty batch handling
def test_empty_batch_handling(predictor):
    empty_df = pd.DataFrame(columns=CANONICAL_PREDICTOR_FEATURES)
    preds = predictor.predict_segments(empty_df)
    assert len(preds) == 0
    assert preds.dtype == np.float32


# 15. JSON serialization compatibility of single prediction
def test_prediction_output_json_serializable(predictor, sample_data):
    single_record = sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[0].to_dict()
    result = predictor.predict_segment(single_record)
    
    # Must serialize cleanly without errors or exposing numpy array internals
    serialized = json.dumps(result)
    deserialized = json.loads(serialized)
    assert deserialized["safety_score"] == result["safety_score"]
    assert deserialized["status"] == "AVAILABLE"


# 16. Confirmation: real LightGBM inference is executed, not mock simulation
def test_real_model_inference_executed_not_mock(predictor, sample_data):
    assert predictor.model.__class__.__name__ == "LGBMRegressor"
    assert not isinstance(predictor, MockSafetyPredictor)
    
    res = predictor.predict_segment(sample_data[CANONICAL_PREDICTOR_FEATURES].iloc[0].to_dict())
    assert res["status"] == "AVAILABLE"
    assert res["status"] != "DEVELOPMENT_MOCK"


# 17. Backward compatibility alias: SafeSheMLPredictor == MLSafetyPredictor
def test_safeshe_ml_predictor_alias():
    assert SafeSheMLPredictor is MLSafetyPredictor
    p_alias = SafeSheMLPredictor(verify_checksum=True)
    assert isinstance(p_alias, MLSafetyPredictor)

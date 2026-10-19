# SafeShe Machine Learning Subsystem (v2.0.0)

## Overview
This directory houses the Machine Learning subsystem for SafeShe. The core engine is a trained **LightGBM Regressor (`best_model.pkl`)** paired with a canonical **Scikit-Learn ColumnTransformer (`preprocessing_pipeline.pkl`)**.

> **CRITICAL ARCHITECTURAL NOTICE:**
> The trained ML model is now technically validated and packaged for online inference, but is **NOT YET CONNECTED** to the live SafeShe journey coordinator. Online integration will occur in a subsequent phase.

---

## 1. Dataset & Semantic Unit
- **Dataset Size**: 1,042,651 road segment rows.
- **Semantic Unit**: Each row represents an individual, physical OpenStreetMap (OSM) road way segment bounded by two network nodes in the Chennai Metropolitan Area.
- **Storage**: Lightweight, column-typed Parquet files under `app/ml/Hack/ml/datasets/processed/`:
  - `master_feature_table.parquet`: 1,042,651 rows x 51 columns.
  - `training_dataset.parquet`: 1,042,651 rows x 53 columns (includes canonical `safety_score` and `risk_score_raw`).
  - `labels.parquet`: 1,042,651 rows (canonical labels).
  - `app/ml/Hack/ml/datasets/validation/test_sample.parquet`: 207,689 rows (held-out test split).

---

## 2. Canonical Target Definition
- **Target Name**: `safety_score`
- **Definition**: `safety_score = 100.0 - risk_score_raw`
- **Scale**: `[0.0, 100.0]`
- **Polarity**: `0.0 = least safe (maximum risk)`, `100.0 = safest (minimum risk)`.
- **Raw Risk Preservation**: Preserved as `risk_score_raw` for transparency.
- **Limitation & Disclosure**: The target is a **Synthetic Safety Proxy** derived from environmental criminology heuristics (CPTED, Jane Jacobs' *Eyes on the Street*). Metrics reflect internal consistency and rule approximation, **NOT** real-world police incident validation.

---

## 3. Feature Schema (41 Predictors)
Defined in `app/ml/schemas.py` and `app/ml/Hack/ml/models/feature_metadata.json`:

- **Categoricals (2)**: `road_type`, `surface`.
- **Booleans (5)**: `crossing`, `high_density_indicator`, `low_density_indicator`, `population_missing_coverage`, `urban_indicator`.
- **Numericals (34)**:
  - Spatial: `latitude`, `longitude`, `length_m`, `curvature`, `road_width`, `speed`.
  - POI Density & Distance: `atm_count_50m`, `bank_count_100m`, `bus_stop_count_50m`, `cafe_count_100m`, `college_count_250m`, `commercial_density`, `fuel_count_250m`, `hotel_count_250m`, `mall_count_250m`, `metro_count_500m`, `park_count_250m`, `pharmacy_count_100m`, `restaurant_count_100m`, `school_count_250m`, `hospital_dist_m`, `police_dist_m`, `essential_services_density`.
  - Population & Accessibility: `population_count_100m`, `population_density`, `population_percentile`, `accessibility_score`, `transit_density`, `emergency_accessibility`, `walkability`, `isolation_index`, `road_complexity`, `human_activity_score`, `desertion_score`.
- **Excluded Non-Predictors (Leakage Prevention)**:
  - `segment_id`, `way_id`, `start_node`, `end_node` (identifiers).
  - `risk_score`, `risk_score_raw`, `risk_class`, `safety_class` (target variants).
  - `bridge`, `tunnel`, `oneway`, `maxspeed`, `lanes`, `sidewalk` (>95% missing or zero-variance object columns).

---

## 4. Leakage-Controlled Validation Split
- **Split Strategy**: `GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)` grouped by `way_id`.
- **Train Rows**: 834,962 (80.08%).
- **Untouched Test Rows**: 207,689 (19.92%).
- **Way Overlap**: **0 ways** across train and test partitions. Eliminates spatial autocorrelation leakage from adjacent road segments.

---

## 5. Model Evaluation & Baseline Comparison

### Candidate Benchmarking (Training Subsample Holdout)
| Model | Val RMSE | Val MAE | Val R² | Fit Time (s) |
| :--- | :--- | :--- | :--- | :--- |
| `DummyMean` (Baseline) | 15.1128 | 13.5615 | -0.0010 | 0.00s |
| `DummyMedian` (Baseline) | 17.1366 | 13.1367 | -0.2870 | 0.00s |
| `RidgeLinear` (Baseline) | 2.7086 | 2.0156 | 0.9678 | 0.05s |
| `RandomForest` | 1.7324 | 1.1148 | 0.9868 | 1.87s |
| `XGBoost` | 1.6837 | 1.0962 | 0.9876 | 2.67s |
| **`LightGBM` (Winner)** | **1.6770** | **1.0955** | **0.9877** | **0.34s** |

### Untouched Held-Out Test Evaluation (207,689 segments)
- **Algorithm**: `LGBMRegressor` (`n_estimators=150, num_leaves=63, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8`)
- **Test RMSE**: **1.6344**
- **Test MAE**: **1.0513**
- **Test R²**: **0.9880**
- **Prediction Range**: `[0.0, 48.69]` (Target scale: `[0.0, 100.0]`)
- **Residual Mean**: `-0.0073` (Zero-centered residuals)

---

## 6. Model Artifacts & Security
All production model assets reside in `app/ml/Hack/ml/models/`:
- `best_model.pkl`: LightGBM Regressor artifact.
- `preprocessing_pipeline.pkl`: Scikit-Learn ColumnTransformer artifact.
- `model_manifest.json`: Cryptographic manifest containing metadata, schema hash, and SHA-256 checksums:
  - `sha256_model`: `bb8e6b04895caf1ca6efcaf37a7994b42690bb8b6237114507f7fa0ba8070dde`
  - `sha256_preprocessor`: `c1ad4c28ae5ef5a7c3867535c16d9e6fdf0729a34027a18f463c0a1b79c550cd`
- `shap_summary.png`: SHAP TreeExplainer feature importance visualization.
- `archive_v1/`: Backup directory preserving all legacy pre-audit model artifacts.

### Loading Security (`app/ml/loader.py`)
- Artifact paths are hardcoded and non-user-controllable.
- Enforces SHA-256 verification against `model_manifest.json` before deserialization.
- Fails closed (`MLArtifactSecurityError`) on tampering or mismatch.

---

## 7. Measured Performance
*Measured on Python 3.10 AMD64 via tracemalloc and performance counters:*
- **Cold Load Time**: ~2,623 ms (includes unpickling and SHA-256 calculation).
- **RAM Footprint**: ~39.39 MB.
- **10 Segments Inference**: 6.69 ms (668.9 µs/segment).
- **100 Segments (Typical Route)**: 7.31 ms (73.1 µs/segment).
- **1,000 Segments (Long Route)**: 11.25 ms (11.3 µs/segment).

---

## 8. Exact Reproduction Commands
From the project root:

```bash
# 1. Regenerate canonical labels with deterministic seed
python -m ml.data_engineering.generators.safety_label_generator

# 2. Execute end-to-end training, GroupShuffleSplit, evaluation, and artifact packaging
python -m ml.training.train_pipeline

# 3. Run the comprehensive ML test suite
python -m pytest tests/ml/test_ml_foundation.py -v
```

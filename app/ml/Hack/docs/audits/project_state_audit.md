# SafeShe — Project State Audit Report

**Generated:** 2026-07-30
**Auditor:** Antigravity AI
**Repository root:** `C:\Users\kesha\OneDrive\Desktop\Hack`
**Audit scope:** Full repository — all source files, datasets, and documentation.

---

## 1. Executive Summary

### Project Purpose

SafeShe is an **AI-powered women's safety intelligence platform**. Its stated mission is to predict the **safety level** and **crowd level** of a location or route by fusing multiple heterogeneous data sources — crime records, population density, OpenStreetMap spatial data, weather conditions, community reports, and road infrastructure signals.

The system is ultimately intended to serve a backend API and a frontend application that provide real-time safety intelligence to end users.

### Current Development Phase

The project is **in the early Dataset Engineering phase**. Two of the eight planned pipeline stages have substantive implementation:

- ✅ **Crime Loader** — fully implemented (~750 LOC)
- ✅ **Population Loader** — fully implemented (~285 LOC)
- ⚠️ **Data Engineering Skeleton** — pipeline, builders, features, labels, schemas, sources, validation, export, and preprocessing are **stubbed or partially implemented** (code exists, but no end-to-end execution path is wired up)
- ❌ **OSM Loader** — not implemented (only a protocol stub in `sources.py`)
- ❌ **Weather Generator** — not implemented
- ❌ **Community Report Generator** — not implemented
- ❌ **ML Models** — no implemented models (empty directories)
- ❌ **Backend API** — not present
- ❌ **Frontend** — not present

### Overall Architecture

The system is structured as a Python monorepo under the `ml/` package:

```
ml/                        ← Python package root (SafeShe ML)
  config/                  ← Typed config dataclasses + JSON files
  data_engineering/        ← Dataset engineering layer
    loaders/               ← Crime Loader, Population Loader
  preprocessing/           ← Tabular ML preprocessing pipeline
  utils/                   ← Shared IO, validation, config helpers
  datasets/                ← Data store (raw, processed, external, synthetic)
  models/                  ← (empty) saved model artifacts
  metrics/                 ← (empty) evaluation results
  feature_importance/      ← (empty) feature importance artifacts
  inference/               ← (empty) inference schemas and services
  training/                ← (empty) training pipelines and evaluation
  notebooks/               ← (empty) exploration and experiment notebooks
docs/                      ← Architecture specification documents
```

---

## 2. Repository Structure

### Complete Folder Tree

```
C:\Users\kesha\OneDrive\Desktop\Hack\
│
├── docs/
│   ├── dataset_engineering.md      ← Pipeline architecture specification
│   ├── dataset_schema.md           ← Full feature & dataset schema spec
│   ├── feature_engineering.md      ← Feature transformation spec
│   ├── label_generation.md         ← Label construction strategy
│   ├── osm_features.md             ← OSM tag-to-feature mapping spec
│   └── audits/
│       └── project_state_audit.md  ← This file
│
└── ml/
    ├── __init__.py                  ← Package declaration ("SafeShe ML package.")
    │
    ├── config/
    │   ├── __init__.py             ← Re-exports paths + settings
    │   ├── paths.py                ← Canonical path constants
    │   ├── settings.py             ← Typed config dataclasses
    │   ├── inference/
    │   │   └── inference_config.json
    │   └── training/
    │       ├── crowd_config.json
    │       └── safety_config.json
    │
    ├── data_engineering/
    │   ├── __init__.py             ← Re-exports loaders
    │   ├── builders.py             ← build_crowd_dataset, build_safety_dataset
    │   ├── export.py               ← export_dataset helper
    │   ├── features.py             ← build_crowd_features, build_safety_features
    │   ├── labels.py               ← generate_crowd_score, generate_safety_score
    │   ├── pipeline.py             ← DataEngineeringPipeline orchestrator
    │   ├── schemas.py              ← CrowdFeatureRow, SafetyFeatureRow dataclasses
    │   ├── sources.py              ← TabularSource protocol + source adapters
    │   ├── validation.py           ← Dataset validation helpers
    │   └── loaders/
    │       ├── __init__.py         ← Re-exports both loaders
    │       ├── crime_loader.py     ← Crime Loader (fully implemented, 744 lines)
    │       └── population_loader.py ← Population Loader (fully implemented, 285 lines)
    │
    ├── preprocessing/
    │   ├── __init__.py
    │   ├── cleaning.py             ← Imputation, deduplication, IQR clipping
    │   ├── encoders.py             ← One-hot encoding
    │   ├── scalers.py              ← StandardScaler wrapper
    │   ├── splits.py               ← Train/test split utilities
    │   ├── pipeline.py             ← TabularPreprocessor (fit/transform/save/load)
    │   ├── encoders/               ← (empty directory)
    │   ├── scalers/                ← (empty directory)
    │   ├── splits/                 ← (empty directory)
    │   └── transformers/           ← (empty directory)
    │
    ├── utils/
    │   ├── __init__.py
    │   ├── config.py               ← JSON config IO, ConfigIOMixin
    │   ├── io.py                   ← save/load JSON, joblib artifacts
    │   ├── validation.py           ← DataFrame validators
    │   ├── io/                     ← (empty directory)
    │   ├── logging/                ← (empty directory)
    │   └── validation/             ← (empty directory)
    │
    ├── datasets/
    │   ├── raw/
    │   │   ├── tamil_nadu_crime_stats_2014_2024.csv
    │   │   ├── tn_2023_crimes_against_women.csv
    │   │   ├── NCRB_CII_2023_Table_5A.4A_0.csv
    │   │   ├── NCRB_CII_2023_Table_5A.4B_0.csv
    │   │   └── 7c1dfb74-70a9-45a3-939b-1f5bf949c10a.csv
    │   ├── processed/
    │   │   └── crime_score.csv     ← Only processed dataset produced so far
    │   ├── external/               ← (empty — WorldPop GeoTIFF not present)
    │   └── synthetic/              ← (empty)
    │
    ├── models/crowd/, safety/, exports/           ← (all empty)
    ├── metrics/crowd/, safety/                    ← (all empty)
    ├── feature_importance/crowd/, safety/         ← (all empty)
    ├── inference/schemas/, services/              ← (all empty)
    ├── training/evaluation/, pipelines/, scripts/ ← (all empty)
    └── notebooks/experiments/, exploration/       ← (all empty)
```

### Folder Responsibility Summary

| Folder | Responsibility |
|---|---|
| `docs/` | Architecture specifications — pipeline, schema, features, labels, OSM |
| `ml/config/` | Typed config dataclasses + serialized JSON training/inference configs |
| `ml/data_engineering/` | Dataset engineering layer — loaders, builders, schemas, labels, validation |
| `ml/data_engineering/loaders/` | Concrete source-specific data loaders (Crime, Population) |
| `ml/preprocessing/` | Reusable tabular ML preprocessing — cleaning, encoding, scaling, splits |
| `ml/utils/` | Shared infrastructure — IO, validation, config helpers |
| `ml/datasets/raw/` | Unprocessed source CSVs |
| `ml/datasets/processed/` | Pipeline-generated output datasets |
| `ml/datasets/external/` | External raster or third-party data (empty — WorldPop not yet placed) |
| `ml/datasets/synthetic/` | Placeholder for synthetic / generated datasets |
| `ml/models/` | Trained model artifacts (.pkl files) — currently empty |
| `ml/metrics/` | Evaluation JSON metrics per model — currently empty |
| `ml/feature_importance/` | Feature importance JSON outputs — currently empty |
| `ml/inference/` | Inference-time schemas and services — currently empty |
| `ml/training/` | Training pipelines, scripts, and evaluation — currently empty |
| `ml/notebooks/` | Jupyter notebooks for exploration and experiments — currently empty |

---

## 3. Implemented Components

### 3.1 Crime Loader

**Purpose:** Discovers all crime CSV files in the repository, auto-detects their schemas, maps each to a unified internal schema, and computes a bounded `crime_score` for each record. Outputs a consolidated `crime_score.csv`.

**Status:** ✅ **Fully implemented and executed** — `crime_score.csv` (255 data rows) is present in `datasets/processed/`.

**Files:** `ml/data_engineering/loaders/crime_loader.py` — 744 lines

**Public Interfaces:**

| Symbol | Type | Description |
|---|---|---|
| `CrimeLoaderConfig` | dataclass | Configuration (discovery roots, output path, district aliases, score weights, year overrides) |
| `CrimeLoader` | class | Main loader — `build()`, `discover_files()` |
| `CrimeLoaderReport` | dataclass | Run audit summary returned by `build()` |
| `CrimeFileReport` | dataclass | Per-file audit details |
| `CrimeLoaderError` | exception | Base error |
| `CrimeSchemaError` | exception | Unsupported schema |
| `CrimeDatasetAdapter` | class | Base class for schema-specific adapters |
| `TNOverallAdapter` | class | Adapter for `tamil_nadu_crime_stats_2014_2024.csv` |
| `TNWomenAdapter` | class | Adapter for `tn_2023_crimes_against_women.csv` |
| `NCRBJuvenileAdapterA` | class | Adapter for `NCRB_CII_2023_Table_5A.4A_0.csv` |
| `NCRBJuvenileAdapterB` | class | Adapter for `NCRB_CII_2023_Table_5A.4B_0.csv` |
| `ComplaintReportsAdapter` | class | Adapter for `7c1dfb74-...csv` (district complaints) |

**Key Behaviors:**
- Auto-discovers CSVs under `datasets/raw/`, falls back to project root if empty.
- Schema detection is header-based: each adapter exposes `required_columns` + optional `file_name_matches()`.
- District names are normalized (Unicode NFKC, punctuation stripping, suffix removal, alias mapping, title-casing).
- `crime_score` is a min-max normalized, field-weighted, invertible score per record, clamped to 0–100.
- Writes a unified CSV with a superset-of-columns schema (column union across all processed files).

**Dependencies:** Standard library only (`csv`, `logging`, `math`, `re`, `unicodedata`, `statistics`) + `ml.config.paths`.

---

### 3.2 Population Loader

**Purpose:** Opens a WorldPop GeoTIFF raster file and provides GPS-coordinate-based population density lookups. Validates CRS, raster metadata, and coordinate bounds before serving queries.

**Status:** ⚠️ **Implementation complete — but non-functional due to missing data.** The `worldpop.tif` file is expected at `ml/datasets/raw/population/worldpop.tif` but is **not present**. The loader raises `PopulationDataLoadError` on instantiation.

**Files:** `ml/data_engineering/loaders/population_loader.py` — 285 lines

**Public Interfaces:**

| Symbol | Type | Description |
|---|---|---|
| `PopulationLoaderConfig` | dataclass | Config (raster path, nodata value, cache flag, bounds default) |
| `PopulationLoader` | class | Main loader — `load()`, `close()`, `get_population_density(lat, lon)` |
| `PopulationRasterMetadata` | dataclass | CRS, width, height, count, transform, dtype, nodata |
| `PopulationLoaderError` | exception | Base error |
| `PopulationSchemaError` | exception | Invalid raster metadata |
| `PopulationDataLoadError` | exception | File not found / cannot open |
| `PopulationLookupError` | exception | Bad coordinates or read failure |

**Key Behaviors:** Context manager support; in-memory coordinate cache (6 decimal precision); WGS84 → raster CRS projection via rasterio; configurable NoData fallback.

**Dependencies:** `numpy`, `rasterio`, `ml.config.paths`

---

### 3.3 Data Engineering Layer (Skeleton)

**Purpose:** Provides orchestration glue between loaders and the final ML-ready datasets.

**Status:** ⚠️ **Partially implemented — structural skeleton only.** Code exists and is internally consistent, but the pipeline cannot run end-to-end due to missing source data (OSM, weather, community reports).

**Files and responsibilities:**

| File | Responsibility |
|---|---|
| `builders.py` | `build_crowd_dataset()`, `build_safety_dataset()` — joins features and labels |
| `export.py` | `export_dataset()` — saves DataFrame to CSV, returns `DatasetExportResult` |
| `features.py` | `build_crowd_features()`, `build_safety_features()` — validates required columns |
| `labels.py` | `generate_crowd_score()`, `generate_safety_score()`, `safety_band()` |
| `pipeline.py` | `DataEngineeringPipeline` — orchestrates build + validate + export |
| `schemas.py` | `CrowdFeatureRow`, `SafetyFeatureRow` dataclasses; `TransportMode`, `RoadType` literals |
| `sources.py` | `TabularSource` protocol; `OsmSource`, `CrimeSource`, `PopulationSource`, `EnvironmentalSource`, `MobilitySource`, `CommunityReportsSource`, `DataSourceBundle` |
| `validation.py` | `validate_crowd_dataset()`, `validate_safety_dataset()` — column presence checks |

**Label Formulas (implemented in `labels.py`):**

```
crowd_score  = 0.30 * commercial_density + 0.20 * office_density
             + 0.15 * restaurant_count   + 0.10 * bus_stop_count
             + 0.10 * metro_count        + 0.05 * school_college_density
             + 0.05 * market_density     + 0.05 * time_weight
             → clamped to [0, 100]

safety_score = 0.35 * crime_score      + 0.20 * crowd_score
             + 0.10 * lighting_score   + 0.10 * police_distance
             + 0.10 * community_reports + 0.05 * weather_risk
             + 0.05 * hospital_distance + 0.05 * road_type_risk
             → clamped to [0, 100]
```

**Dependencies:** `pandas`

---

### 3.4 Preprocessing Pipeline

**Purpose:** Reusable tabular ML preprocessing — fit-once, reuse-many pattern.

**Status:** ✅ **Fully implemented** — but untested (no training, no notebooks, no test suite).

| File | Key Exports |
|---|---|
| `cleaning.py` | `MissingValueArtifacts`, `OutlierClipArtifacts`, fit/apply functions, `drop_duplicate_rows()`, `infer_column_types()` |
| `encoders.py` | `CategoricalEncodingArtifacts`, `fit_categorical_encoder()`, `apply_categorical_encoder()` |
| `scalers.py` | `NumericScalingArtifacts`, `fit_scaler()`, `apply_scaler()` |
| `splits.py` | `split_features_target()`, `train_test_split_tabular()` |
| `pipeline.py` | `TabularPreprocessor` — composable fit/transform/save/load |

**Pipeline stages:** deduplication → type inference → median/mode imputation → IQR clipping → one-hot encoding → StandardScaler → joblib serialization.

**Dependencies:** `numpy`, `pandas`, `sklearn`, `joblib`

---

### 3.5 Configuration System

**Status:** ✅ **Fully implemented.** All paths resolved relative to `__file__` (portable). Typed dataclasses with JSON serialization. Three JSON config files committed to source control.

**Key config classes:** `BaseConfig`, `TrainingConfig`, `CrowdTrainingConfig`, `SafetyTrainingConfig`, `InferenceConfig`.

---

### 3.6 Utility Layer

**Status:** ✅ **Fully implemented.**

Provides `save_json/load_json`, `save_joblib_artifact/load_joblib_artifact`, `ConfigIOMixin`, `save_json_config/load_json_config`, `resolve_project_path`, and four DataFrame assertion helpers.

---

## 4. Dataset Inventory

| File | Location | Source | Format | Size | Status | Used By |
|---|---|---|---|---|---|---|
| `tamil_nadu_crime_stats_2014_2024.csv` | `datasets/raw/` | TN state crime records 2014–2024, 11 data rows, 14 cols | CSV | 1,013 B | ✅ Active | Crime Loader → TNOverallAdapter |
| `tn_2023_crimes_against_women.csv` | `datasets/raw/` | TN district women crime 2023, ~57 rows | CSV | 6,448 B | ✅ Active | Crime Loader → TNWomenAdapter |
| `NCRB_CII_2023_Table_5A.4A_0.csv` | `datasets/raw/` | NCRB juvenile crime by category 2023, ~63 rows | CSV | 5,815 B | ✅ Active | Crime Loader → NCRBJuvenileAdapterA |
| `NCRB_CII_2023_Table_5A.4B_0.csv` | `datasets/raw/` | NCRB juvenile crime by age/gender 2023, ~63 rows | CSV | 7,441 B | ✅ Active | Crime Loader → NCRBJuvenileAdapterB |
| `7c1dfb74-70a9-45a3-939b-1f5bf949c10a.csv` | `datasets/raw/` | TN district complaint reports, ~49 rows | CSV | 3,915 B | ✅ Active | Crime Loader → ComplaintReportsAdapter |
| `crime_score.csv` | `datasets/processed/` | Merged, scored crime output from Crime Loader | CSV | ~90 KB | ✅ Generated | Future: Feature Engineering |
| `worldpop.tif` | `datasets/raw/population/` | WorldPop population density raster | GeoTIFF | **MISSING** | ❌ Absent | Population Loader |
| `crowd_dataset.csv` | `datasets/processed/` | Crowd training dataset | CSV | **MISSING** | ❌ Not generated | Crowd Model training |
| `safety_dataset.csv` | `datasets/processed/` | Safety training dataset | CSV | **MISSING** | ❌ Not generated | Safety Model training |

**Notes on `crime_score.csv`:** 255 rows, **97 columns** (highly sparse — wide column union of all source schemas). Absolute Windows paths embedded in `source_path` column. District-level only — no GPS coordinates. No schema version recorded.

---

## 5. Documentation Review

| File | Summary | Status |
|---|---|---|
| `docs/dataset_engineering.md` (11,550 B) | 8-stage pipeline architecture spec. Defines stage responsibilities, I/O contracts, and validation rules. No code. | ✅ Accurate — matches implemented skeleton |
| `docs/dataset_schema.md` (17,631 B) | Frozen master schema — 37 features with types, sources, transformations, validation rules, versioning. | ✅ Comprehensive. Code in `schemas.py` partially matches (missing `weekend`, `time_weight`, `route_corridor_*`) |
| `docs/feature_engineering.md` (16,991 B) | How raw inputs become ML-ready features across 9 categories. Mermaid diagram included. Specs only. | ✅ Accurate spec. Not yet implemented in code |
| `docs/label_generation.md` (5,454 B) | Two-label strategy — `crowd_score` and `safety_score`. Explicitly states no formula is included. | ⚠️ **Outdated:** `labels.py` already implements specific weighted formulas — contradicts the spec |
| `docs/osm_features.md` (13,342 B) | Comprehensive OSM tag-to-feature mapping — safety, crowd, road features. Extraction radii and assumptions. | ✅ Complete spec. Not yet implemented in code |

**Outdated documentation:** `label_generation.md` states "No exact mathematical formula is defined here" but concrete formulas are already coded in `labels.py`. This is the only identified documentation drift.

---

## 6. Code Architecture

### Package Structure

```
ml/
  config/            ← Pure configuration — no business logic
  data_engineering/  ← Business logic for data loading and assembly
    loaders/         ← Source-specific loading
  preprocessing/     ← ML preprocessing — pure transformations
  utils/             ← Cross-cutting infrastructure
  datasets/          ← Data artifacts (not Python code)
  models/            ← Model artifacts (empty)
  metrics/           ← Evaluation artifacts (empty)
  feature_importance/ ← Feature importance artifacts (empty)
  inference/         ← Inference-time code (stub)
  training/          ← Training-time code (stub)
  notebooks/         ← Notebooks (stub)
```

### Dependency Graph

```
ml.config.paths
  └─ consumed by → crime_loader, population_loader, pipeline, config.settings

ml.config.settings
  └─ consumed by → config.__init__

ml.utils
  └─ consumed by → data_engineering.pipeline, data_engineering.validation

ml.preprocessing
  └─ will be consumed by → training (not implemented)

ml.data_engineering.loaders
  └─ consumed by → data_engineering.__init__
                 → (no run scripts exist)

ml.data_engineering.builders
  └─ consumed by → pipeline
  └─ depends on → features, labels

ml.data_engineering.features
  └─ depends on → schemas

ml.data_engineering.validation
  └─ depends on → ml.utils.validation
```

### Data Flow

```
[Raw CSVs in datasets/raw/]
    ↓
CrimeLoader.build()
    ↓
[datasets/processed/crime_score.csv]  ← Only live output today
    ↓ (future)
[OSM Loader — NOT IMPLEMENTED]
    ↓
[Weather Generator — NOT IMPLEMENTED]
    ↓
[Community Generator — NOT IMPLEMENTED]
    ↓
DataEngineeringPipeline.build_crowd/build_safety(assembled_frame)
    ↓
[crowd_dataset.csv + safety_dataset.csv — NOT GENERATED]
    ↓
[TabularPreprocessor.fit_transform() — NOT INVOKED]
    ↓
[Model Training — NOT IMPLEMENTED]
    ↓
[crowd_model.pkl, safety_model.pkl — NOT GENERATED]
    ↓
[Inference Services — NOT IMPLEMENTED]
    ↓
[Backend API — NOT IMPLEMENTED]
    ↓
[Frontend Application — NOT IMPLEMENTED]
```

---

## 7. Current Dataset Engineering Pipeline

### Pipeline Status

```
Stage                   Status         Output
────────────────────────────────────────────────────────────
Raw Data                ✅ Present     5 CSVs in datasets/raw/
    ↓
Crime Loader            ✅ Complete    datasets/processed/crime_score.csv
    ↓
Population Loader       ⚠️  Blocked    worldpop.tif MISSING
    ↓
OSM Loader              ❌ Missing     not implemented
    ↓
Weather Generator       ❌ Missing     not implemented
    ↓
Community Generator     ❌ Missing     not implemented
    ↓
Feature Engineering     ⚠️  Skeleton   validates columns, no assembly code
    ↓
Label Generation        ✅ Formula     formulas coded in labels.py
    ↓
Dataset Builder         ⚠️  Skeleton   pipeline.py exists, cannot run
    ↓
crowd_dataset.csv       ❌ Missing     not generated
safety_dataset.csv      ❌ Missing     not generated
```

### Stage Explanations

| Stage | What it does | Current state |
|---|---|---|
| Raw Data | Source crime CSVs available | Partial — no OSM, WorldPop, weather |
| Crime Loader | Discover, adapt, score, merge crime CSVs | ✅ Runs, produces output |
| Population Loader | Open WorldPop raster, serve density lookups | ❌ Blocked — raster absent |
| OSM Loader | Query OSM for POIs, roads, amenities | ❌ Not implemented |
| Weather Generator | Fetch / simulate weather risk | ❌ Not implemented |
| Community Report Generator | Aggregate MongoDB safety reports | ❌ Not implemented |
| Feature Engineering | Assemble canonical feature rows | ⚠️ Column validation only |
| Label Generation | Weighted formula → crowd_score / safety_score | ✅ Formula coded |
| Dataset Builder | Orchestrate build + validate + export | ⚠️ Code exists, no data |

---

## 8. Configuration

### Path Constants (`config/paths.py`)

All derived relative to `__file__` — portable across machines.

| Constant | Purpose |
|---|---|
| `PACKAGE_ROOT` | `ml/` package directory |
| `PROJECT_ROOT` | Root `Hack/` directory |
| `RAW_DATASETS_DIR` | `ml/datasets/raw/` |
| `PROCESSED_DATASETS_DIR` | `ml/datasets/processed/` |
| `MODELS_DIR` | `ml/models/` |
| `TRAINING_CONFIG_DIR` | `ml/config/training/` |
| `INFERENCE_CONFIG_DIR` | `ml/config/inference/` |

### Training Configuration (`settings.py`)

| Class | Key Defaults |
|---|---|
| `TrainingConfig` | `test_size=0.2`, `validation_size=0.1`, `n_splits=5`, `scoring=neg_mean_absolute_error`, `cv_jobs=-1` |
| `CrowdTrainingConfig` | `dataset_filename=crowd_dataset.csv`, `target_column=crowd_score` |
| `SafetyTrainingConfig` | `dataset_filename=safety_dataset.csv`, `target_column=safety_score` |
| `InferenceConfig` | `crowd_model_filename=crowd_model.pkl`, `safety_model_filename=safety_model.pkl` |

### Environment Variables

**None used anywhere in the codebase.** No `.env` file, no `os.getenv()`. No secrets management for API keys (OpenWeather, MongoDB, OSRM).

### Hardcoded Values

| Location | Value | Concern |
|---|---|---|
| `CrimeLoaderConfig` | `neutral_score = 50.0` | Reasonable default |
| `PopulationLoaderConfig` | `raster_path = .../population/worldpop.tif` | No env override |
| `labels.py` | Crowd weights (0.30, 0.20, 0.15...) | Not runtime-configurable |
| `labels.py` | Safety weights (0.35, 0.20, 0.10...) | Not runtime-configurable |

---

## 9. Implemented Features

Complete list of every functioning capability:

1. Crime CSV discovery — recursive glob of `datasets/raw/`, with project-root fallback
2. Schema auto-detection — header-based adapter matching across 5 schema types
3. District name normalization — Unicode NFKC, punctuation stripping, suffix removal (`district`, `dist`, `dt`), alias mapping, title-casing
4. Robust value coercion — handles commas, `%`, `na`, `null`, `-`
5. Crime scoring — min-max normalized, field-weighted, invertible `crime_score` per record
6. Crime CSV export — unified schema with preferred-column ordering
7. Crime manifest export — optional JSON audit report (controlled by `save_manifest`)
8. Population raster validation — CRS, dimensions, band count, transform presence
9. Population coordinate validation — finite, in-range geographic bounds check
10. Population GPS-to-raster projection — WGS84 to raster CRS via rasterio
11. Population cell sampling — single-cell read with NoData handling
12. Population coordinate caching — dict-based, keyed by 6-decimal-rounded coordinates
13. Crowd feature validation — required column presence
14. Safety feature validation — required column presence
15. Crowd label formula — 8-component weighted, clamped 0–100
16. Safety label formula — 8-component weighted, clamped 0–100
17. Safety band classification — unsafe / moderate / safe / very_safe
18. Tabular preprocessing — deduplication
19. Tabular preprocessing — numeric/categorical type inference
20. Tabular preprocessing — median/most_frequent imputation
21. Tabular preprocessing — IQR outlier clipping
22. Tabular preprocessing — one-hot encoding (sklearn version-tolerant)
23. Tabular preprocessing — StandardScaler
24. Tabular preprocessing — train/test split
25. Preprocessor serialization — joblib save/load
26. JSON config serialization — to_json() / from_json()
27. Source bundle protocol — DataSourceBundle.fetch_all()
28. Pipeline manifest — JSON summary of generated dataset metadata

---

## 10. Pending Features

### 10.1 OSM Loader

**Expected responsibility:** Query OpenStreetMap (via osmnx / Overpass API / local extract) for POIs, roads, and amenities around a GPS coordinate. Extract crowd features (restaurant count, bus stops, metro stations, office density, commercial density) and safety features (police distance, hospital distance, lighting score, road type). Aggregate road-corridor features for route-level queries.

**Current state:** `OsmSource` data-holder in `sources.py` only — no query, geometry, or feature extraction logic exists.

### 10.2 Weather Generator

**Expected responsibility:** Fetch live weather from OpenWeather API or use a cached snapshot. Convert conditions to a canonical category (`weather` feature) and a numeric `weather_risk` score.

**Current state:** `EnvironmentalSource` stub in `sources.py`. No API client, no caching, no risk mapping.

### 10.3 Community Report Generator

**Expected responsibility:** Query MongoDB for recent user safety reports near a location. Deduplicate, weight by recency and type, and aggregate to a `community_reports` float signal.

**Current state:** `CommunityReportsSource` stub in `sources.py`. No MongoDB client.

### 10.4 Feature Engineering Integration

**Expected responsibility:** Assemble outputs of all loaders/generators into canonical `CrowdFeatureRow` / `SafetyFeatureRow` DataFrames ready for `DataEngineeringPipeline`.

**Current state:** `features.py` validates that a DataFrame has the right columns, but there is no code that assembles those columns from raw loader outputs. The assembly bridge is entirely missing.

### 10.5 Training Pipelines

**Expected responsibility:** Orchestrate `TabularPreprocessor.fit_transform()` → model training (RandomForest, XGBoost, or similar regression) → evaluation → artifact serialization.

**Current state:** `training/pipelines/`, `training/evaluation/`, `training/scripts/` — all empty directories.

### 10.6 Model Evaluation

**Expected responsibility:** Compute MAE, RMSE, R², cross-validation scores, feature importance. Save to `metrics/crowd/` and `metrics/safety/`.

**Current state:** `training/evaluation/` — empty.

### 10.7 Inference Services

**Expected responsibility:** Load trained models and preprocessors. Accept a feature payload and return a `crowd_score` or `safety_score`.

**Current state:** `inference/schemas/` and `inference/services/` — empty.

### 10.8 Backend API

**Expected responsibility:** REST API exposing safety and crowd prediction endpoints. Accept GPS coordinates, timestamp, and route data. Integrate all real-time sources.

**Current state:** Not present anywhere in the repository.

### 10.9 Frontend Application

**Expected responsibility:** User-facing map interface for visualizing safety scores and route guidance.

**Current state:** Not present.

### 10.10 Notebooks

**Expected responsibility:** Exploratory data analysis, prototype experiments, and feature validation.

**Current state:** `notebooks/exploration/` and `notebooks/experiments/` — empty.

---

## 11. Technical Debt

### Critical

| ID | Issue | Location | Description |
|---|---|---|---|
| TD-001 | Absolute paths embedded in output | `crime_score.csv` | `source_path` stores `C:\Users\kesha\...` — dataset is non-portable; breaks on any other machine or OS |
| TD-002 | WorldPop raster absent | `datasets/raw/population/` | Population Loader is dead code until placed. No download instructions or placeholder exist |
| TD-003 | No environment variable support | All config | API keys for OpenWeather, MongoDB, OSRM have no defined injection path |

### High

| ID | Issue | Location | Description |
|---|---|---|---|
| TD-004 | No run scripts or tests | Entire `ml/` | Crime Loader produced output once but there are no scripts, notebooks, or tests to reproduce or validate it |
| TD-005 | Hardcoded label weights | `data_engineering/labels.py` | Formula weights are constants, not config-driven — tuning requires code changes |
| TD-006 | Schema drift: code vs docs | `features.py` vs `dataset_schema.md` | `build_crowd_features()` missing `weekend`, `time_weight`; `build_safety_features()` missing `weather`, `weather_risk`, `population_density`, `road_type`, `weekend`, route corridor features |
| TD-007 | Parallel file + directory pattern | `preprocessing/`, `utils/` | Both `encoders.py` and `encoders/` exist (and analogues), with subdirectories empty — structural confusion |
| TD-008 | 12 empty subdirectories | Multiple | `preprocessing/encoders/`, `scalers/`, `splits/`, `transformers/`, `utils/io/`, `utils/logging/`, `utils/validation/`, etc. |

### Medium

| ID | Issue | Location | Description |
|---|---|---|---|
| TD-009 | Crime score not spatial | `crime_loader.py` | Output is district-level; feature layer needs GPS-to-district join logic (absent) |
| TD-010 | `CrimeDataLoadError` not exported | `data_engineering/__init__.py` | Exception inaccessible without direct module import |
| TD-011 | `generate_crowd_score` parameter mismatch | `builders.py` vs `features.py` | `school_college_density` and `market_density` always default to 0.0 because `build_crowd_features()` does not include them in required columns |
| TD-012 | No dataset versioning implementation | `data_engineering/` | Schema/feature/OSM version metadata specified in docs but not written to any output |
| TD-013 | `from_json()` Path type coercion | `config/settings.py` | JSON deserialization produces `str` for `Path`-typed fields — silently breaks path operations |

### Low

| ID | Issue | Location | Description |
|---|---|---|---|
| TD-014 | UUID filename | `datasets/raw/` | `7c1dfb74-...csv` is opaque — origin undocumented |
| TD-015 | Duplicate JSON IO | `config/settings.py` + `utils/config.py` | `BaseConfig.to_json()` and `save_json_config()` overlap; `ConfigIOMixin` redundant with `BaseConfig` |
| TD-016 | No logging configuration | Entire `ml/` | `getLogger(__name__)` used but no formatter, level, or handler configured |
| TD-017 | `__pycache__` in repo | `ml/__pycache__/` etc. | Compiled bytecache visible — likely no `.gitignore` |

---

## 12. Data Quality

### Crime Datasets

| Dataset | Quality Assessment |
|---|---|
| `tamil_nadu_crime_stats_2014_2024.csv` | 11 rows, 14 cols. State-level aggregate 2014–2024. No missing values. Conviction_Rate inverted in scoring (by design). |
| `tn_2023_crimes_against_women.csv` | ~57 rows, district-level, 2023. Multi-line headers create CSV complexity. High column count. |
| `NCRB_CII_2023_Table_5A.4A_0.csv` | ~63 rows, **national-level** (India). Collapses to `district="India"` — no spatial granularity. |
| `NCRB_CII_2023_Table_5A.4B_0.csv` | ~63 rows, national juvenile crime by age/gender. Very wide schema (17+ cols). |
| `7c1dfb74-...csv` | ~49 rows, TN district complaints. No year column — `year` is None in output. UUID name undocumented. |

### Processed Dataset (`crime_score.csv`)

| Aspect | Observation |
|---|---|
| Rows | 255 |
| Columns | **97** — severely sparse; most columns empty for most rows |
| Spatial granularity | District-level only — no GPS coordinates |
| Portability | Absolute Windows paths in `source_path` |
| District coverage | TN districts + "India" (NCRB) + "Tamil Nadu State" |
| Missing year | Complaint reports rows have empty `year` |
| Schema version | Not recorded |

### Validation Coverage Gaps

- `validate_crowd_dataset()` and `validate_safety_dataset()` check **column presence only**
- No range validation (0–100 for scores, non-negative for distances)
- No null rate checking, no type enforcement, no schema version verification

---

## 13. ML Readiness

### Assessment: Not Ready — Early Stage

| Requirement | Status |
|---|---|
| Crime feature available | ⚠️ Partial — district-level, no spatial join to GPS |
| Population density available | ❌ WorldPop raster absent |
| OSM features available | ❌ OSM Loader not implemented |
| Weather features available | ❌ Weather Generator not implemented |
| Community report features | ❌ Not implemented |
| `crowd_dataset.csv` generated | ❌ Not generated |
| `safety_dataset.csv` generated | ❌ Not generated |
| Preprocessing pipeline ready | ✅ Implemented, untested |
| Model training pipeline ready | ❌ Not implemented |
| Dataset schema fully enforced | ⚠️ Column presence only |
| Dataset versioning implemented | ❌ Not implemented |
| Train/test split logic ready | ✅ Implemented |
| Label formulas coded | ✅ Implemented |

### What Is Still Missing Before ML Training

1. Place WorldPop GeoTIFF at `ml/datasets/raw/population/worldpop.tif`
2. Implement OSM Loader — POI counts, distances, road features for sample coordinates
3. Implement Weather Generator — `weather` category + `weather_risk` score
4. Implement Community Report Generator — `community_reports` signal
5. Write Feature Assembly code — bridge loader outputs into `CrowdFeatureRow` / `SafetyFeatureRow`
6. Define seed coordinate grid — (lat, lon, timestamp) sample points covering Tamil Nadu
7. Generate `crowd_dataset.csv` and `safety_dataset.csv` via `DataEngineeringPipeline`
8. Implement Training Pipeline — TabularPreprocessor → model → evaluation → artifact serialization
9. Strengthen validation — range checks, null checks, type enforcement
10. Wire crime score to GPS — spatial join from coordinates to district-level crime score

---

## 14. Risks

### Data Quality Risks

| Risk | Severity | Description |
|---|---|---|
| R-001 Crime data is district-level only | **High** | ML model needs point-level features. Spatial join from GPS to district boundary required but absent |
| R-002 Synthetic label quality | **High** | Labels are entirely rule-based, not calibrated against observed ground truth. Accuracy bounded by formula fidelity |
| R-003 NCRB data adds noise | **Medium** | All NCRB rows map to `district="India"` — merging with TN district data corrupts spatial signal |
| R-004 WorldPop raster unavailable | **High** | Population Loader cannot run; population density required in both datasets |
| R-005 No real community reports | **Medium** | Community report feature unavailable; MongoDB not connected |

### Architecture Risks

| Risk | Severity | Description |
|---|---|---|
| R-006 Train-inference feature skew | **High** | Feature engineering not yet codified; same spatial radii and normalization must be used at train time and inference time |
| R-007 No testing infrastructure | **High** | No pytest config, no CI, no test files — Crime Loader complexity entirely untested |
| R-008 Label weight rigidity | **Medium** | Formula weights hardcoded; tuning requires code changes |
| R-009 No secrets management | **High** | When Weather / MongoDB / OSRM APIs are integrated, no secrets injection mechanism exists |

### Scalability Risks

| Risk | Severity | Description |
|---|---|---|
| R-010 Unbounded population cache | **Low** | `_lookup_cache` grows without limit in large batch runs |
| R-011 Crime CSV column explosion | **Medium** | 97 columns from 5 sources; adding more sources will grow this further |

### Maintainability Risks

| Risk | Severity | Description |
|---|---|---|
| R-012 No run scripts | **High** | No entry points — developers must write their own scripts to run any module |
| R-013 Empty directories | **Low** | ~12 empty dirs create structural confusion |

---

## 15. Recommendations

> These are recommendations only. No implementation is included.

### Immediate Priority

1. **Place WorldPop GeoTIFF** — obtain from worldpop.org and place at `ml/datasets/raw/population/worldpop.tif`. Without this, the Population Loader is dead code.
2. **Create run script for Crime Loader** — add `ml/scripts/run_crime_loader.py` so the pipeline is reproducible.
3. **Fix schema drift in `features.py`** — add `weekend` and `time_weight` to `build_crowd_features()`; add missing columns to `build_safety_features()`.
4. **Add GPS-to-district crime lookup** — implement spatial join so a (lat, lon) resolves to a `crime_score`.
5. **Remove absolute paths from `crime_score.csv`** — store `source_path` as relative path from project root.

### Short-term

6. **Implement OSM Loader** — use `osmnx` or Overpass API; start with crowd features (simpler, unblocks crowd dataset generation first).
7. **Generate synthetic coordinate grid** — create sample (lat, lon, timestamp) points for Tamil Nadu to enable dataset generation.
8. **Strengthen dataset validation** — add range checks (0–100 for scores, non-negative for distances, null rates).
9. **Write minimal training script** — connect `TabularPreprocessor` to a sklearn regressor on crowd dataset.
10. **Add `.gitignore`** — exclude `__pycache__`, `.pyc`, `*.pkl`, large raster files.

### Medium-term

11. **Implement Weather Generator** — OpenWeather API with neutral fallback; define `weather` vocabulary in config.
12. **Make label weights configurable** — move formula weights into `CrowdTrainingConfig` / `SafetyTrainingConfig`.
13. **Fix `BaseConfig.from_json()` Path coercion** — explicitly cast `Path`-typed fields after JSON deserialization.
14. **Implement dataset versioning** — write `schema_version`, `feature_version`, `osm_version` to output manifests.
15. **Resolve file+directory anti-pattern** — remove empty `encoders/`, `scalers/`, `splits/`, `transformers/`, `io/`, `logging/`, `validation/` subdirectories.
16. **Add environment variable support** — use `python-dotenv` for API keys before integrating Weather + MongoDB.
17. **Write unit tests** — minimum: `crime_loader.py` adapters, `labels.py` boundary cases, `preprocessing/pipeline.py` fit/transform round-trip.

---

## 16. Project Timeline

### Per-Layer Completion Estimate

| Layer | Completed % | Blocking issues |
|---|---|---|
| Crime Loader | ~90% | Absolute paths, no spatial join, no tests |
| Population Loader | ~60% | WorldPop raster absent |
| OSM Loader | ~5% | Protocol stub only |
| Weather Generator | ~0% | Not started |
| Community Report Generator | ~0% | Not started |
| Feature Assembly | ~20% | Column validation coded, no assembly |
| Label Generation | ~80% | Formulas coded, validation limited |
| Dataset Builder | ~30% | Orchestration coded, cannot run |
| Preprocessing Pipeline | ~85% | Implemented, untested |
| Configuration System | ~90% | Path deserialization bug |
| Utility Layer | ~90% | Minor config IO duplication |
| ML Model Training | ~0% | Not started |
| ML Model Evaluation | ~0% | Not started |
| Inference Services | ~0% | Not started |
| Backend API | ~0% | Not started |
| Frontend Application | ~0% | Not started |

### Overall Completion

| Tier | Completion |
|---|---|
| Dataset Engineering | ~30% |
| ML / Modelling | ~0% |
| Backend | ~0% |
| Frontend | ~0% |
| **Overall** | **~12–15%** |

### Major Milestones Remaining

| Milestone | Prerequisites |
|---|---|
| M1 — `crowd_dataset.csv` generated | OSM Loader + WorldPop raster + Feature Assembly + Crime spatial join |
| M2 — `safety_dataset.csv` generated | M1 + Weather Generator + Community Generator |
| M3 — First trained crowd model | M1 + Training Pipeline |
| M4 — First trained safety model | M2 + Training Pipeline |
| M5 — Inference service operational | M3 + M4 + Inference Services |
| M6 — Backend API operational | M5 + API framework |
| M7 — Frontend operational | M6 + Frontend application |
| M8 — End-to-end system | M7 + integration testing |

---

*End of audit report. Repository state as of 2026-07-30.*

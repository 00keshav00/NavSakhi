# SafeShe ML Pipeline - Project Handoff

## 1. Current Project Status
**Architecture Phase:** Frozen and stable.
**Completed Modules:**
- Core Data Engineering (OSM, Population, Crime Loaders, Road Segment Generator)
- Synthetic Feature Generator
- Feature Engineering Module
- Feature Validation Module
- Label Generation Module
- Dataset Validation Profiler
- Environment Preflight Checker
- Pipeline Orchestrator (`run_pipeline.py`)
**Pending Modules:**
- Dataset Splitting & Builder Module
- Model Training & Evaluation
**Current Architecture:** Pure sequential execution strictly coupled through canonical parquet file outputs. Configuration-driven with robust read-only logging and pre-validation.

## 2. Folder Structure
```text
C:\Users\kesha\OneDrive\Desktop\Hack
├── datasets/                 # Base dataset storage
│   └── validation/           # Manual ground truth sets (e.g. chennai_ground_truth.csv)
├── docs/                     # Architecture and design documentation (audits, schemas)
├── ml/                       # Root machine learning codebase
│   ├── analysis/             # Dataset profilers and post-generation analytics
│   ├── config/               # Constants and path management (paths.py)
│   ├── data_engineering/     # Generators and Loaders (OSM, Crime, Population)
│   ├── feature_engineering/  # Complex spatial and algorithmic feature derivations
│   ├── labeling/             # Target label generation (V2 Logic)
│   ├── preflight/            # Environment validation checks
│   ├── validation/           # Pre-label dataset integrity validation
│   └── run_pipeline.py       # Sequential orchestrator
├── PROJECT_HANDOFF.md        # This document
├── README.md                 # Setup and run instructions
└── requirements.txt          # Python dependency specifications
```

## 3. Pipeline Flow
1. **Preflight Check:** Validates Python packages, input directories, and raw file existence.
2. **Road Segment Generator:** Parses raw OSM road geometry into discrete segments.
3. **OSM Loader:** Buffers segments and computes distance/density properties of urban POIs.
4. **Population Loader:** Extracts high-res demographics from WorldPop GeoTIFFs using spatial stencils.
5. **Crime Loader:** Harmonizes messy historic CSV formats into standardized geographical crime scores.
6. **Synthetic Generator:** Calculates deterministic proxy variables (lighting, CCTV) from foundational datasets to stand in for physical IoT sensors.
7. **Feature Engineering:** Joins all previous outputs to derive high-level sociological and urban metrics (walkability, human activity).
8. **Feature Validator:** Strictly asserts that the merged multi-dimensional dataset adheres to configured ranges (0-100) and schema types before labels are touched.
9. **Label Generator:** Outputs canonical targets (`safety_score`, `crowd_score`) using the fully verified master table.
10. **Dataset Profiler:** Generates HTML-based visual summaries (heatmaps, IQR outliers, distributions).

## 4. Features
* **human_activity_score (0-100)**: Derived from population density, commercial density, transit stops, and leisure hotspots (cafes/restaurants).
* **desertion_score (0-100)**: A direct inverse of the human activity score; heavily penalizes community safety metrics.
* **essential_services_density (0-100)**: Distance-based aggregation of police, hospitals, pharmacies, banks, ATMs, and malls.
* **synth_lighting (0-100)**: Deterministic projection based on road hierarchy (motorways vs tracks), commercial presence, and human activity levels.
* **synth_cctv (0-100)**: Probability metric anchored to bank, ATM, mall counts, and essential services density.
* **synth_night_activity (0-100)**: Correlated with ambient human activity and leisure POIs.
* **synth_community_safety (0-100)**: Sentiment proxy modulated by historical crime priors and penalized by high desertion scores.
* **Label Generation (safety_score & crowd_score)**: Rule-based mapping combining physical hazard structures, ambient visibility (lighting/CCTV), and statistical priors (crime/population). It relies on deterministic caps (e.g. severe crime strictly caps safety below 30).

## 5. Datasets
- **Raw Datasets:** 
  - OSM (`chennai_v1.osm.pbf`)
  - Population (`population.tif`)
  - Crime (Multiple raw CSVs spanning TN jurisdictions)
- **Processed Datasets:** Stored entirely as lightweight, column-typed `.parquet` files.
- **Validation Dataset:** `datasets/validation/chennai_ground_truth.csv` (25 human-vetted locations across Chennai for sanity checking outputs).
- **Expected Outputs:** `master_feature_table.parquet`, `labels.parquet`, HTML analytics profile.

## 6. Configuration
- **Important Files:** `ml/config/paths.py` controls absolute directory resolution and enforces canonical naming structures.
- **Environment:** Relies on robust disk permissions; the workspace directory must be fully writable for intermediate caches.

## 7. Dependencies
- **Python Version**: 3.10+ (64-bit Windows AMD64)
- **Python Packages**: `pandas`, `geopandas`, `rasterio`, `pyrosm`, `shapely`, `numpy`, `pyarrow`, `matplotlib`, `seaborn`, `scikit-learn`
- **External Software**: **Microsoft Visual C++ 14.0+ Build Tools** (Desktop C++ workload) is MANDATORY to compile the `cykhash` dependency required by `pyrosm`.

## 8. Remaining Work
1. **Finish environment setup**: Install Microsoft C++ Build Tools and successfully build `pyrosm`.
2. **Run pipeline**: Execute `python ml/run_pipeline.py`.
3. **Review profiler**: Analyze the `dataset_profile.html` output to verify feature variance.
4. **Train model**: Build `ml/models/trainer.py` to learn against the deterministic labels.
5. **Evaluate model**: Validate the model against the `chennai_ground_truth.csv` set.

## 9. Known Issues
- **`pyrosm` compilation failure:** Because the internal dependency `cykhash` lacks a pre-compiled Windows wheel on PyPI, `pip install` fails out of the box unless the host machine has native MSVC build tools.
- **Empty Datasets Assumption:** `population.tif` is currently a 0-byte placeholder created solely to satisfy the preflight check. It must be replaced by a real GeoTIFF before pipeline execution.

## 10. Design Decisions
- **Synthetic Features**: Employed out of necessity to emulate variables (like exact street lamp lux or specific CCTV camera views) that cannot be pulled directly from OSM tags but fundamentally govern urban safety algorithms. They act as deterministic proxies until physical IoT streams are available.
- **Validation Dataset (Ground Truth)**: The ML models will be trained on synthetically derived target labels. The 25-location ground truth set exists strictly to validate that the synthetic assumptions conceptually map to human urban reality in Chennai.
- **Strict Orchestration**: The modular structure uses file-system handoffs (`.parquet` dumps) between stages rather than massive in-memory pipelines to guarantee memory safety and debuggability at every intermediate step.

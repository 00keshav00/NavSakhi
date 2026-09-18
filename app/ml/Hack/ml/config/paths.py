"""Canonical project paths for SafeShe ML.
Acts as the single source of truth for dataset and module locations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

# --- Base Directories ---
PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
PROJECT_ROOT: Final[Path] = PACKAGE_ROOT.parent

# --- Configuration Directories ---
CONFIG_DIR: Final[Path] = PACKAGE_ROOT / "config"
TRAINING_CONFIG_DIR: Final[Path] = CONFIG_DIR / "training"
INFERENCE_CONFIG_DIR: Final[Path] = CONFIG_DIR / "inference"

# --- Core Dataset Directories ---
DATASETS_DIR: Final[Path] = PACKAGE_ROOT / "datasets"
RAW_DATASETS_DIR: Final[Path] = DATASETS_DIR / "raw"
INTERIM_DATASETS_DIR: Final[Path] = DATASETS_DIR / "interim"
PROCESSED_DATASETS_DIR: Final[Path] = DATASETS_DIR / "processed"
EXTERNAL_DATASETS_DIR: Final[Path] = DATASETS_DIR / "external"
SYNTHETIC_DATASETS_DIR: Final[Path] = DATASETS_DIR / "synthetic"

# --- Module Directories ---
MODELS_DIR: Final[Path] = PACKAGE_ROOT / "models"
METRICS_DIR: Final[Path] = PACKAGE_ROOT / "metrics"
FEATURE_IMPORTANCE_DIR: Final[Path] = PACKAGE_ROOT / "feature_importance"
PREPROCESSING_DIR: Final[Path] = PACKAGE_ROOT / "preprocessing"

# --- Raw Data Sources (Sub-directories) ---
RAW_OSM_DIR: Final[Path] = RAW_DATASETS_DIR / "osm"
RAW_POPULATION_DIR: Final[Path] = RAW_DATASETS_DIR / "population"
RAW_CRIME_DIR: Final[Path] = RAW_DATASETS_DIR / "crime"
CRIME_DIRECTORY: Final[Path] = RAW_CRIME_DIR

# --- Dataset Selection ---
DEFAULT_REGION: Final[str] = "chennai_v1"

# --- Raw Data Files ---
OSM_PBF_FILE: Final[Path] = RAW_OSM_DIR / f"{DEFAULT_REGION}.osm.pbf"
POPULATION_RASTER: Final[Path] = RAW_POPULATION_DIR / "ind_pd_2016_1km.tif"
POPULATION_TIF: Final[Path] = POPULATION_RASTER  # Maintained for backward compatibility

# --- Processed ML Feature Sets ---
ROAD_SEGMENTS: Final[Path] = PROCESSED_DATASETS_DIR / "road_segments.parquet"
OSM_ROAD_FEATURES: Final[Path] = PROCESSED_DATASETS_DIR / "osm_road_features.parquet"
OSM_POI_FEATURES: Final[Path] = PROCESSED_DATASETS_DIR / "osm_poi_features.parquet"
OSM_DISTANCE_FEATURES: Final[Path] = PROCESSED_DATASETS_DIR / "osm_distance_features.parquet"
POPULATION_FEATURES: Final[Path] = PROCESSED_DATASETS_DIR / "population_features.parquet"
CRIME_FEATURES: Final[Path] = PROCESSED_DATASETS_DIR / "crime_features.parquet"
SYNTHETIC_FEATURES: Final[Path] = PROCESSED_DATASETS_DIR / "synthetic_features.parquet"
MASTER_FEATURE_TABLE: Final[Path] = PROCESSED_DATASETS_DIR / "master_feature_table.parquet"
LABELS: Final[Path] = PROCESSED_DATASETS_DIR / "labels.parquet"

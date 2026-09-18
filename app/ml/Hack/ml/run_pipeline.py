"""SafeShe ML Pipeline Orchestrator.

Executes the end-to-end data engineering and feature extraction pipeline sequentially.
Strictly restricted to pure orchestration logic without implementing any ML directly.
"""

import logging
import sys
import time

# Canonical Path Constants
from ml.config.paths import (
    PROJECT_ROOT,
    OSM_PBF_FILE,
    POPULATION_RASTER,
    CRIME_DIRECTORY,
    ROAD_SEGMENTS,
    OSM_ROAD_FEATURES,
    OSM_POI_FEATURES,
    OSM_DISTANCE_FEATURES,
    POPULATION_FEATURES,
    CRIME_FEATURES,
    SYNTHETIC_FEATURES,
    MASTER_FEATURE_TABLE,
    LABELS,
)

# Pipeline Modules
from ml.data_engineering.generators.road_segment_generator import RoadSegmentGenerator, GeneratorConfig
from ml.data_engineering.loaders.osm_loader import OSMLoader, OSMLoaderConfig
from ml.data_engineering.loaders.population_loader import PopulationLoader, PopulationLoaderConfig
from ml.data_engineering.loaders.crime_loader import CrimeLoader, CrimeLoaderConfig
from ml.data_engineering.generators.synthetic_generator import SyntheticGenerator, SyntheticGeneratorConfig
from ml.feature_engineering.feature_engineering import FeatureEngineer, FeatureEngineeringConfig
from ml.validation.feature_validator import FeatureValidator, FeatureValidatorConfig
from ml.labeling.label_generator import LabelGenerator, LabelGeneratorConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_road_segment_generator() -> None:
    """Stage 1: Road Segment anchoring."""
    config = GeneratorConfig(output_path=ROAD_SEGMENTS)
    generator = RoadSegmentGenerator(config)
    generator.build(osm_pbf_path=OSM_PBF_FILE)


def run_osm_loader() -> None:
    """Stage 2: Spatial OSM feature extraction."""
    config = OSMLoaderConfig(
        pbf_path=OSM_PBF_FILE,
        segments_path=ROAD_SEGMENTS,
        output_dir=ROAD_SEGMENTS.parent
    )
    loader = OSMLoader(config)
    loader.build()


def run_population_loader() -> None:
    """Stage 3: High-resolution demographic mapping."""
    config = PopulationLoaderConfig(
        raster_path=POPULATION_RASTER,
        segments_path=ROAD_SEGMENTS,
        output_path=POPULATION_FEATURES
    )
    loader = PopulationLoader(config)
    loader.build()


def run_crime_loader() -> None:
    """Stage 4: Unified crime data normalization."""
    config = CrimeLoaderConfig(
        discovery_roots=[CRIME_DIRECTORY],
        output_path=CRIME_FEATURES
    )
    loader = CrimeLoader(config)
    loader.build()


def run_synthetic_generator() -> None:
    """Stage 5: Rule-based IoT feature synthesis."""
    config = SyntheticGeneratorConfig(
        output_path=SYNTHETIC_FEATURES,
        road_features_path=OSM_ROAD_FEATURES,
        poi_features_path=OSM_POI_FEATURES,
        dist_features_path=OSM_DISTANCE_FEATURES,
        pop_features_path=POPULATION_FEATURES
    )
    generator = SyntheticGenerator(config)
    generator.build()


def run_feature_engineer() -> None:
    """Stage 6: Master feature combination and derivation."""
    config = FeatureEngineeringConfig(
        segments_path=ROAD_SEGMENTS,
        crime_path=CRIME_FEATURES,
        road_features_path=OSM_ROAD_FEATURES,
        poi_features_path=OSM_POI_FEATURES,
        dist_features_path=OSM_DISTANCE_FEATURES,
        pop_features_path=POPULATION_FEATURES,
        synth_features_path=SYNTHETIC_FEATURES,
        output_path=MASTER_FEATURE_TABLE
    )
    engineer = FeatureEngineer(config)
    engineer.build()


def run_feature_validator() -> None:
    """Stage 7: Production boundary validation."""
    reports_dir = PROJECT_ROOT / "docs" / "reports"
    config = FeatureValidatorConfig(
        input_path=MASTER_FEATURE_TABLE,
        report_md_path=reports_dir / "feature_validation_report.md",
        report_json_path=reports_dir / "feature_validation_summary.json"
    )
    validator = FeatureValidator(config)
    validator.validate()
    
    # Enforce strict pipeline failure if validation reports an error state
    if validator.report.get('status') == "FAILED":
        raise ValueError("Feature Validation FAILED. Check docs/reports/feature_validation_report.md for details.")


def run_label_generator() -> None:
    """Stage 8: ML Target label bootstrapping."""
    config = LabelGeneratorConfig(
        input_path=MASTER_FEATURE_TABLE,
        output_path=LABELS
    )
    generator = LabelGenerator(config)
    generator.build()


def main() -> None:
    """Orchestrates the entire SafeShe sequential ML pipeline."""
    start_time = time.time()
    
    stages = [
        ("Road Segment Generator", run_road_segment_generator),
        ("OSM Loader", run_osm_loader),
        ("Population Loader", run_population_loader),
        ("Crime Loader", run_crime_loader),
        ("Synthetic Generator", run_synthetic_generator),
        ("Feature Engineer", run_feature_engineer),
        ("Feature Validator", run_feature_validator),
        ("Label Generator", run_label_generator)
    ]
    
    logger.info("Starting SafeShe ML Pipeline Orchestration...")
    
    for stage_name, stage_func in stages:
        logger.info(f"--- STARTING STAGE: {stage_name} ---")
        stage_start = time.time()
        
        try:
            stage_func()
        except Exception as e:
            logger.error(f"FATAL ERROR in stage '{stage_name}': {e}", exc_info=True)
            # Stop immediately and exit with non-zero code as required
            sys.exit(1)
            
        stage_duration = time.time() - stage_start
        logger.info(f"--- COMPLETED STAGE: {stage_name} in {stage_duration:.2f} seconds ---\n")
        
    total_time = time.time() - start_time
    logger.info(f"PIPELINE COMPLETED SUCCESSFULLY in {total_time:.2f} seconds.")


if __name__ == "__main__":
    main()

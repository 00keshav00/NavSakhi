"""Preflight Check for the SafeShe ML Pipeline.

Validates the environment, dependencies, dataset availability, and permissions
before executing any heavy pipeline stages.
"""

import sys
import os
import importlib
import logging
from pathlib import Path
from typing import List

# Import canonical paths safely (should not rely on heavy ML packages)
try:
    from ml.config.paths import (
        RAW_DATASETS_DIR,
        PROCESSED_DATASETS_DIR,
        OSM_PBF_FILE,
        POPULATION_RASTER,
        CRIME_DIRECTORY,
    )
except ImportError as e:
    print(f"[FAIL] Could not import ML config paths. Ensure you are running from the project root. Error: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class PreflightChecker:
    """Orchestrates environment validation checks."""
    def __init__(self):
        self.passed_checks = 0
        self.failed_checks = 0
        self.failures: List[str] = []

    def _pass(self, msg: str) -> None:
        logger.info(f"  [PASS] {msg}")
        self.passed_checks += 1

    def _fail(self, msg: str) -> None:
        logger.error(f"  [FAIL] {msg}")
        self.failed_checks += 1
        self.failures.append(msg)

    def check_packages(self) -> None:
        """Verifies all required heavy-lifting packages are installed."""
        logger.info("\n--- Checking Required Python Packages ---")
        packages = [
            "pandas", 
            "geopandas", 
            "rasterio", 
            "pyrosm", 
            "shapely", 
            "numpy", 
            "pyarrow"
        ]
        
        for pkg in packages:
            try:
                importlib.import_module(pkg)
                self._pass(f"Package installed: {pkg}")
            except ImportError:
                self._fail(f"Missing required package: {pkg}. Run pip install {pkg}")

    def check_directories(self) -> None:
        """Verifies core structural directories exist."""
        logger.info("\n--- Checking Base Directories ---")
        
        # Raw must exist. Processed can be created if it doesn't exist.
        if RAW_DATASETS_DIR.exists() and RAW_DATASETS_DIR.is_dir():
            self._pass(f"Raw directory exists: {RAW_DATASETS_DIR}")
        else:
            self._fail(f"Raw directory missing: {RAW_DATASETS_DIR}")

    def check_raw_datasets(self) -> None:
        """Verifies the core raw dataset files required for ML feature extraction."""
        logger.info("\n--- Checking Raw Datasets ---")
        
        # OSM PBF
        if OSM_PBF_FILE.exists() and OSM_PBF_FILE.is_file():
            self._pass(f"OSM PBF file found: {OSM_PBF_FILE.name}")
        else:
            self._fail(f"Missing OSM PBF file at {OSM_PBF_FILE}")
            
        # Population Raster
        if POPULATION_RASTER.exists() and POPULATION_RASTER.is_file():
            self._pass(f"Population raster found: {POPULATION_RASTER.name}")
        else:
            self._fail(f"Missing Population raster at {POPULATION_RASTER}")
            
        # Crime Directory & Supported CSV files
        if CRIME_DIRECTORY.exists() and CRIME_DIRECTORY.is_dir():
            csv_files = list(CRIME_DIRECTORY.glob("*.csv"))
            if csv_files:
                self._pass(f"Crime directory contains {len(csv_files)} CSV file(s).")
            else:
                self._fail(f"Crime directory exists but contains no CSV files: {CRIME_DIRECTORY}")
        else:
            self._fail(f"Missing Crime directory at {CRIME_DIRECTORY}")

    def check_writable(self) -> None:
        """Verifies that the pipeline can output Parquet files successfully."""
        logger.info("\n--- Checking Writable Outputs ---")
        out_dir = PROCESSED_DATASETS_DIR
        
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            test_file = out_dir / ".preflight_write_test"
            test_file.touch()
            test_file.unlink()
            self._pass(f"Output directory is writable: {out_dir}")
        except Exception as e:
            self._fail(f"Output directory is not writable: {out_dir} - Error: {e}")

    def run(self) -> bool:
        """Executes all checks and generates the PASS/FAIL report."""
        logger.info("=========================================")
        logger.info("      SafeShe ML Preflight Checks        ")
        logger.info("=========================================")
        
        self.check_packages()
        self.check_directories()
        self.check_raw_datasets()
        self.check_writable()
        
        logger.info("\n=========================================")
        logger.info("            Preflight Summary            ")
        logger.info("=========================================")
        logger.info(f"Total Checks Passed: {self.passed_checks}")
        logger.info(f"Total Checks Failed: {self.failed_checks}")
        
        if self.failed_checks == 0:
            logger.info("\n✅ PREFLIGHT PASSED. The environment is ready.")
            return True
        else:
            logger.error("\n❌ PREFLIGHT FAILED. Please resolve the following issues:")
            for fail in self.failures:
                logger.error(f"  - {fail}")
            return False

if __name__ == "__main__":
    checker = PreflightChecker()
    success = checker.run()
    if not success:
        sys.exit(1)
    sys.exit(0)

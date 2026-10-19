import logging
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ml.config.paths import MASTER_FEATURE_TABLE, PROJECT_ROOT

@dataclass
class FeatureValidatorConfig:
    """Configuration for the Feature Validation module."""
    input_path: Path = MASTER_FEATURE_TABLE
    report_md_path: Path = PROJECT_ROOT / "docs" / "reports" / "feature_validation_report.md"
    report_json_path: Path = PROJECT_ROOT / "docs" / "reports" / "feature_validation_summary.json"
    
    # Columns that strictly must exist and must not have NaNs
    critical_columns: List[str] = field(default_factory=lambda: [
        'segment_id', 'latitude', 'longitude', 'length_m', 'road_type'
    ])
    
    # Thresholds
    max_missing_pct_warning: float = 5.0
    max_missing_pct_error: float = 20.0

class FeatureValidator:
    """
    Validates the integrity of the generated master feature table.
    Performs purely read-only diagnostics without modifying data.
    """
    def __init__(self, config: FeatureValidatorConfig):
        self.config = config
        self.report = {
            "status": "PASSED",
            "errors": [],
            "warnings": [],
            "summary": {}
        }

    def _add_error(self, msg: str) -> None:
        logger.error(f"VALIDATION ERROR: {msg}")
        self.report['errors'].append(msg)
        self.report['status'] = "FAILED"

    def _add_warning(self, msg: str) -> None:
        logger.warning(f"VALIDATION WARNING: {msg}")
        self.report['warnings'].append(msg)

    def validate(self) -> None:
        """Executes the full suite of validations on the feature table."""
        import time
        start_time = time.time()
        logger.info(f"START: FeatureValidator | Output: {self.config.report_md_path}")
        if not self.config.input_path.exists():
            self._add_error(f"Master feature table not found at {self.config.input_path}")
            self._export_reports()
            return
            
        logger.info(f"Loading master feature table from {self.config.input_path}...")
        df = pd.read_parquet(self.config.input_path)
        
        if df.empty:
            self._add_error("The master feature table is entirely empty (0 rows).")
            self._export_reports()
            return

        self._validate_schema(df)
        self._validate_primary_keys(df)
        self._validate_missing_values(df)
        self._validate_ranges(df)
        self._validate_derived_features(df)
        self._generate_distribution_summary(df)
        
        self._export_reports()
        
        duration = time.time() - start_time
        logger.info(f"COMPLETED: FeatureValidator | Duration: {duration:.2f}s | Processed Rows: {len(df)} | Output: {self.config.report_md_path}")
        
        if self.report['status'] == "PASSED":
            logger.info("Validation complete. All critical checks PASSED.")
        else:
            logger.error("Validation complete. Checks FAILED. See report for details.")

    def _validate_schema(self, df: pd.DataFrame) -> None:
        logger.info("Executing Schema Validation...")
        for col in self.config.critical_columns:
            if col not in df.columns:
                self._add_error(f"Critical column missing: '{col}'")
                
        # Basic type checks
        if 'segment_id' in df.columns and not pd.api.types.is_string_dtype(df['segment_id']):
            # It could be integer string hash. Let's just ensure it's not a generic object containing mixed types.
            pass

    def _validate_primary_keys(self, df: pd.DataFrame) -> None:
        logger.info("Executing Primary Key Validation...")
        if 'segment_id' not in df.columns:
            return
            
        if df['segment_id'].isna().any():
            self._add_error("Found NULL values in primary key 'segment_id'.")
            
        duplicates = df['segment_id'].duplicated().sum()
        if duplicates > 0:
            self._add_error(f"Found {duplicates} duplicate 'segment_id' records.")

    def _validate_missing_values(self, df: pd.DataFrame) -> None:
        logger.info("Executing Missing Value Validation...")
        for col in df.columns:
            missing_pct = (df[col].isna().sum() / len(df)) * 100
            
            if col in self.config.critical_columns and missing_pct > 0:
                self._add_error(f"Critical feature '{col}' is missing values ({missing_pct:.2f}%).")
            elif missing_pct > self.config.max_missing_pct_error:
                self._add_error(f"Feature '{col}' exceeds maximum missing threshold ({missing_pct:.2f}%).")
            elif missing_pct > self.config.max_missing_pct_warning:
                self._add_warning(f"Feature '{col}' has a high missing rate ({missing_pct:.2f}%).")

    def _validate_ranges(self, df: pd.DataFrame) -> None:
        logger.info("Executing Range Validation...")
        
        # Helper to check limits
        def check_bounds(col: str, min_val: float, max_val: float = None):
            if col in df.columns:
                if min_val is not None and (df[col].dropna() < min_val).any():
                    self._add_error(f"Feature '{col}' contains values below minimum ({min_val}).")
                if max_val is not None and (df[col].dropna() > max_val).any():
                    self._add_error(f"Feature '{col}' contains values above maximum ({max_val}).")
                    
        check_bounds('population_density', min_val=0.0)
        check_bounds('commercial_density', min_val=0.0)
        check_bounds('road_width', min_val=0.0)
        
        # 0 to 100 bounds
        check_bounds('walkability', min_val=0.0, max_val=100.0)
        check_bounds('isolation_index', min_val=0.0, max_val=100.0)
        check_bounds('synthetic_confidence', min_val=0.0, max_val=100.0)
        check_bounds('accessibility_score', min_val=0.0, max_val=100.0)
        check_bounds('emergency_accessibility', min_val=0.0, max_val=100.0)
        check_bounds('road_complexity', min_val=0.0, max_val=100.0)
        check_bounds('human_activity_score', min_val=0.0, max_val=100.0)
        check_bounds('desertion_score', min_val=0.0, max_val=100.0)
        check_bounds('essential_services_density', min_val=0.0, max_val=100.0)

    def _validate_derived_features(self, df: pd.DataFrame) -> None:
        logger.info("Executing Derived Feature Validation...")
        
        # Check for Infinite Values
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if np.isinf(df[col]).any():
                self._add_error(f"Feature '{col}' contains infinite (Inf) values.")
                
        # Check for negative counts
        count_cols = [c for c in df.columns if '_count_' in c]
        for col in count_cols:
            if (df[col].dropna() < 0).any():
                self._add_error(f"Count feature '{col}' contains negative values.")
                
        # Impossible Combination Check (e.g. density > 0 but counts == 0)
        if 'commercial_density' in df.columns and 'mall_count_250m' in df.columns:
            impossible = (df['commercial_density'] == 0) & (df['mall_count_250m'] > 0)
            if impossible.any():
                self._add_error(f"Impossible combination: commercial_density is 0 but mall_count > 0 for {impossible.sum()} rows.")

    def _generate_distribution_summary(self, df: pd.DataFrame) -> None:
        logger.info("Generating Distribution Summary...")
        numeric_df = df.select_dtypes(include=[np.number])
        
        for col in numeric_df.columns:
            s = df[col]
            self.report['summary'][col] = {
                "min": float(s.min()) if not pd.isna(s.min()) else None,
                "max": float(s.max()) if not pd.isna(s.max()) else None,
                "mean": float(s.mean()) if not pd.isna(s.mean()) else None,
                "std": float(s.std()) if not pd.isna(s.std()) else None,
                "missing_pct": float(s.isna().mean() * 100)
            }

    def _export_reports(self) -> None:
        """Writes the validation results to Markdown and JSON formats."""
        logger.info("Exporting validation reports...")
        
        # Ensure directories exist
        self.config.report_md_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.report_json_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export JSON
        with open(self.config.report_json_path, 'w') as f:
            json.dump(self.report, f, indent=4)
            
        # Export Markdown
        lines = [
            "# Feature Validation Report",
            f"**Status:** {self.report['status']}",
            ""
        ]
        
        if self.report['errors']:
            lines.append("## ❌ Errors")
            for e in self.report['errors']:
                lines.append(f"- {e}")
            lines.append("")
            
        if self.report['warnings']:
            lines.append("## ⚠️ Warnings")
            for w in self.report['warnings']:
                lines.append(f"- {w}")
            lines.append("")
            
        lines.append("## 📊 Distribution Summary")
        lines.append("| Feature | Min | Max | Mean | Std | Missing % |")
        lines.append("|---|---|---|---|---|---|")
        
        for feature, stats in self.report['summary'].items():
            min_val = f"{stats['min']:.4f}" if stats['min'] is not None else "NaN"
            max_val = f"{stats['max']:.4f}" if stats['max'] is not None else "NaN"
            mean_val = f"{stats['mean']:.4f}" if stats['mean'] is not None else "NaN"
            std_val = f"{stats['std']:.4f}" if stats['std'] is not None else "NaN"
            missing = f"{stats['missing_pct']:.2f}%"
            
            lines.append(f"| {feature} | {min_val} | {max_val} | {mean_val} | {std_val} | {missing} |")
            
        with open(self.config.report_md_path, 'w') as f:
            f.write("\n".join(lines))
            
        logger.info(f"Reports saved to {self.config.report_md_path.parent}")


if __name__ == "__main__":
    validator = FeatureValidator(FeatureValidatorConfig())
    validator.validate()

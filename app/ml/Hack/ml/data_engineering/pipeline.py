"""High-level orchestration for SafeShe dataset engineering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..config.paths import PROCESSED_DATASETS_DIR
from ..utils.io import save_json
from .builders import build_crowd_dataset, build_safety_dataset
from .export import DatasetExportResult, export_dataset
from .validation import validate_crowd_dataset, validate_safety_dataset


@dataclass(slots=True)
class DataEngineeringPipeline:
    """Build and export SafeShe training datasets from prepared source frames."""

    processed_dir: Path = PROCESSED_DATASETS_DIR

    def build_crowd(self, source_frame: pd.DataFrame) -> tuple[pd.DataFrame, DatasetExportResult]:
        """Build and export the crowd dataset."""

        dataset = build_crowd_dataset(source_frame)
        validate_crowd_dataset(dataset)
        export_result = export_dataset(dataset, self.processed_dir / "crowd_dataset.csv")
        return dataset, export_result

    def build_safety(self, source_frame: pd.DataFrame) -> tuple[pd.DataFrame, DatasetExportResult]:
        """Build and export the safety dataset."""

        dataset = build_safety_dataset(source_frame)
        validate_safety_dataset(dataset)
        export_result = export_dataset(dataset, self.processed_dir / "safety_dataset.csv")
        return dataset, export_result

    def export_manifest(self, crowd_result: DatasetExportResult, safety_result: DatasetExportResult) -> Path:
        """Write a small JSON manifest describing generated datasets."""

        manifest = {
            "crowd_dataset": {
                "path": str(crowd_result.path),
                "rows": crowd_result.row_count,
                "columns": crowd_result.column_count,
            },
            "safety_dataset": {
                "path": str(safety_result.path),
                "rows": safety_result.row_count,
                "columns": safety_result.column_count,
            },
        }
        return save_json(manifest, self.processed_dir / "dataset_manifest.json")

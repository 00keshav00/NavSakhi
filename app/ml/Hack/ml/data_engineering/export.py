"""Dataset export helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(slots=True)
class DatasetExportResult:
    """Metadata describing an exported dataset."""

    path: Path
    row_count: int
    column_count: int


def export_dataset(df: pd.DataFrame, path: str | Path, index: bool = False) -> DatasetExportResult:
    """Persist a dataset to CSV and return export metadata."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destination, index=index)
    return DatasetExportResult(path=destination, row_count=len(df), column_count=len(df.columns))

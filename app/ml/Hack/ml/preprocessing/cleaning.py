"""Data cleaning helpers for tabular ML pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer


@dataclass(slots=True)
class MissingValueArtifacts:
    """Fitted imputers for numeric and categorical columns."""

    numeric_columns: list[str]
    categorical_columns: list[str]
    numeric_imputer: SimpleImputer | None
    categorical_imputer: SimpleImputer | None


@dataclass(slots=True)
class OutlierClipArtifacts:
    """Per-column clipping bounds derived from the IQR rule."""

    numeric_columns: list[str]
    lower_bounds: dict[str, float]
    upper_bounds: dict[str, float]


def infer_column_types(
    df: pd.DataFrame,
    target_column: str | None = None,
) -> tuple[list[str], list[str]]:
    """Infer numeric and categorical feature columns from a DataFrame."""

    feature_df = df.drop(columns=[target_column], errors="ignore") if target_column else df
    numeric_columns = feature_df.select_dtypes(include=[np.number, "bool"]).columns.tolist()
    categorical_columns = [
        column
        for column in feature_df.columns
        if column not in numeric_columns
    ]
    return numeric_columns, categorical_columns


def drop_duplicate_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the DataFrame without duplicate rows."""

    return df.drop_duplicates().copy()


def fit_missing_value_artifacts(
    df: pd.DataFrame,
    numeric_columns: Sequence[str],
    categorical_columns: Sequence[str],
    numeric_strategy: str = "median",
    categorical_strategy: str = "most_frequent",
    fill_value: str | float | int | None = None,
) -> MissingValueArtifacts:
    """Fit imputers for numeric and categorical columns."""

    numeric_imputer: SimpleImputer | None = None
    categorical_imputer: SimpleImputer | None = None

    if numeric_columns:
        numeric_imputer = SimpleImputer(strategy=numeric_strategy, fill_value=fill_value)
        numeric_imputer.fit(df[list(numeric_columns)])

    if categorical_columns:
        categorical_imputer = SimpleImputer(strategy=categorical_strategy, fill_value=fill_value)
        categorical_imputer.fit(df[list(categorical_columns)])

    return MissingValueArtifacts(
        numeric_columns=list(numeric_columns),
        categorical_columns=list(categorical_columns),
        numeric_imputer=numeric_imputer,
        categorical_imputer=categorical_imputer,
    )


def apply_missing_value_artifacts(
    df: pd.DataFrame,
    artifacts: MissingValueArtifacts,
) -> pd.DataFrame:
    """Apply fitted imputers to a DataFrame."""

    transformed = df.copy()

    if artifacts.numeric_columns and artifacts.numeric_imputer is not None:
        transformed.loc[:, artifacts.numeric_columns] = artifacts.numeric_imputer.transform(
            transformed[artifacts.numeric_columns]
        )

    if artifacts.categorical_columns and artifacts.categorical_imputer is not None:
        transformed.loc[:, artifacts.categorical_columns] = artifacts.categorical_imputer.transform(
            transformed[artifacts.categorical_columns]
        )

    return transformed


def fit_outlier_clip_artifacts(
    df: pd.DataFrame,
    numeric_columns: Sequence[str],
    multiplier: float = 1.5,
) -> OutlierClipArtifacts:
    """Fit IQR-based clipping bounds for numeric columns."""

    lower_bounds: dict[str, float] = {}
    upper_bounds: dict[str, float] = {}

    for column in numeric_columns:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            lower_bounds[column] = float("-inf")
            upper_bounds[column] = float("inf")
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower_bounds[column] = float(q1 - multiplier * iqr)
        upper_bounds[column] = float(q3 + multiplier * iqr)

    return OutlierClipArtifacts(
        numeric_columns=list(numeric_columns),
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
    )


def apply_outlier_clip_artifacts(
    df: pd.DataFrame,
    artifacts: OutlierClipArtifacts,
) -> pd.DataFrame:
    """Clip numeric values to the fitted IQR-based bounds."""

    transformed = df.copy()

    for column in artifacts.numeric_columns:
        lower_bound = artifacts.lower_bounds.get(column, float("-inf"))
        upper_bound = artifacts.upper_bounds.get(column, float("inf"))
        transformed[column] = pd.to_numeric(transformed[column], errors="coerce").clip(
            lower=lower_bound,
            upper=upper_bound,
        )

    return transformed

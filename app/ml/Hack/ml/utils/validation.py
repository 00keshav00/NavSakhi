"""Lightweight validation helpers for tabular ML workflows."""

from __future__ import annotations

from typing import Sequence

import pandas as pd


def assert_dataframe_not_empty(df: pd.DataFrame, name: str = "DataFrame") -> None:
    """Raise a ValueError if the DataFrame is empty."""

    if df.empty:
        raise ValueError(f"{name} cannot be empty.")


def assert_columns_present(df: pd.DataFrame, required_columns: Sequence[str], name: str = "DataFrame") -> None:
    """Ensure the requested columns exist in the DataFrame."""

    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise KeyError(f"{name} is missing columns: {missing_columns}")


def assert_target_present(df: pd.DataFrame, target_column: str) -> None:
    """Ensure the target column exists before training or splitting."""

    if target_column not in df.columns:
        raise KeyError(f"Target column '{target_column}' was not found.")


def assert_numeric_columns(df: pd.DataFrame, numeric_columns: Sequence[str]) -> None:
    """Ensure the provided columns are present and numeric-like."""

    assert_columns_present(df, numeric_columns, name="DataFrame")
    non_numeric = [column for column in numeric_columns if not pd.api.types.is_numeric_dtype(df[column])]
    if non_numeric:
        raise TypeError(f"Expected numeric columns, but these columns are not numeric: {non_numeric}")

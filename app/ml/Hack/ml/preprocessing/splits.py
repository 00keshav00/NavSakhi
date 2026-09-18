"""Train/test split utilities for tabular datasets."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split


def split_features_target(
    df: pd.DataFrame,
    target_column: str,
) -> tuple[pd.DataFrame, pd.Series]:
    """Split a tabular DataFrame into features and target."""

    if target_column not in df.columns:
        raise KeyError(f"Target column '{target_column}' not found in DataFrame.")

    features = df.drop(columns=[target_column]).copy()
    target = df[target_column].copy()
    return features, target


def train_test_split_tabular(
    features: pd.DataFrame,
    target: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42,
    shuffle: bool = True,
    stratify: Any = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Perform a standard train/test split for tabular ML tasks."""

    return train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_state,
        shuffle=shuffle,
        stratify=stratify,
    )

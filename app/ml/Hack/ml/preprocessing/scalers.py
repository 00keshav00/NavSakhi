"""Scaling helpers for numeric feature preparation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd
from sklearn.preprocessing import StandardScaler


@dataclass(slots=True)
class NumericScalingArtifacts:
    """Fitted scaler and its numeric feature names."""

    numeric_columns: list[str]
    scaler: StandardScaler | None


def fit_scaler(
    df: pd.DataFrame,
    numeric_columns: Sequence[str],
) -> NumericScalingArtifacts:
    """Fit a standard scaler for numeric columns."""

    numeric_columns = list(numeric_columns)
    if not numeric_columns:
        return NumericScalingArtifacts([], None)

    scaler = StandardScaler()
    scaler.fit(df[numeric_columns])
    return NumericScalingArtifacts(numeric_columns=numeric_columns, scaler=scaler)


def apply_scaler(
    df: pd.DataFrame,
    artifacts: NumericScalingArtifacts,
) -> pd.DataFrame:
    """Scale numeric columns using the fitted scaler."""

    if not artifacts.numeric_columns or artifacts.scaler is None:
        return pd.DataFrame(index=df.index)

    scaled_array = artifacts.scaler.transform(df[artifacts.numeric_columns])
    return pd.DataFrame(
        scaled_array,
        index=df.index,
        columns=artifacts.numeric_columns,
    )

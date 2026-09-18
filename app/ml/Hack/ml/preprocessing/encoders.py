"""Categorical encoding helpers for tabular ML pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd
from sklearn.preprocessing import OneHotEncoder


@dataclass(slots=True)
class CategoricalEncodingArtifacts:
    """Fitted encoder and its output column names."""

    categorical_columns: list[str]
    encoder: OneHotEncoder | None
    encoded_feature_names: list[str]


def _build_one_hot_encoder(
    drop_first: bool,
    handle_unknown: str,
) -> OneHotEncoder:
    """Create a version-tolerant OneHotEncoder instance."""

    drop = "first" if drop_first else None
    try:
        return OneHotEncoder(
            drop=drop,
            handle_unknown=handle_unknown,
            sparse_output=False,
        )
    except TypeError:
        return OneHotEncoder(
            drop=drop,
            handle_unknown=handle_unknown,
            sparse=False,
        )


def fit_categorical_encoder(
    df: pd.DataFrame,
    categorical_columns: Sequence[str],
    drop_first: bool = False,
    handle_unknown: str = "ignore",
) -> CategoricalEncodingArtifacts:
    """Fit a one-hot encoder for categorical columns."""

    categorical_columns = list(categorical_columns)
    if not categorical_columns:
        return CategoricalEncodingArtifacts([], None, [])

    encoder = _build_one_hot_encoder(drop_first=drop_first, handle_unknown=handle_unknown)
    encoder.fit(df[categorical_columns])

    try:
        feature_names = encoder.get_feature_names_out(categorical_columns).tolist()
    except AttributeError:
        feature_names = encoder.get_feature_names(categorical_columns).tolist()

    return CategoricalEncodingArtifacts(
        categorical_columns=categorical_columns,
        encoder=encoder,
        encoded_feature_names=feature_names,
    )


def apply_categorical_encoder(
    df: pd.DataFrame,
    artifacts: CategoricalEncodingArtifacts,
) -> pd.DataFrame:
    """Transform categorical columns into encoded numerical features."""

    if not artifacts.categorical_columns or artifacts.encoder is None:
        return pd.DataFrame(index=df.index)

    encoded_array = artifacts.encoder.transform(df[artifacts.categorical_columns])
    return pd.DataFrame(
        encoded_array,
        index=df.index,
        columns=artifacts.encoded_feature_names,
    )

"""Composable tabular preprocessing pipeline for SafeShe models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import pandas as pd

from .cleaning import (
    MissingValueArtifacts,
    OutlierClipArtifacts,
    apply_missing_value_artifacts,
    apply_outlier_clip_artifacts,
    drop_duplicate_rows,
    fit_missing_value_artifacts,
    fit_outlier_clip_artifacts,
    infer_column_types,
)
from .encoders import (
    CategoricalEncodingArtifacts,
    apply_categorical_encoder,
    fit_categorical_encoder,
)
from .scalers import NumericScalingArtifacts, apply_scaler, fit_scaler


@dataclass(slots=True)
class TabularPreprocessor:
    """Fit-once, reuse-many preprocessing pipeline for tabular data."""

    target_column: str | None = None
    numeric_columns: list[str] | None = None
    categorical_columns: list[str] | None = None
    numeric_strategy: str = "median"
    categorical_strategy: str = "most_frequent"
    outlier_multiplier: float | None = 1.5
    scale_numeric: bool = True
    encode_categorical: bool = True
    drop_first: bool = False
    handle_unknown: str = "ignore"
    fitted_: bool = field(default=False, init=False)
    feature_columns_: list[str] = field(default_factory=list, init=False)
    missing_value_artifacts_: MissingValueArtifacts | None = field(default=None, init=False)
    outlier_artifacts_: OutlierClipArtifacts | None = field(default=None, init=False)
    categorical_artifacts_: CategoricalEncodingArtifacts | None = field(default=None, init=False)
    scaler_artifacts_: NumericScalingArtifacts | None = field(default=None, init=False)
    output_feature_names_: list[str] = field(default_factory=list, init=False)

    def fit(self, df: pd.DataFrame) -> "TabularPreprocessor":
        """Fit all preprocessing steps on the provided DataFrame."""

        if df.empty:
            raise ValueError("Cannot fit preprocessing pipeline on an empty DataFrame.")

        working_df = drop_duplicate_rows(df)
        feature_df = (
            working_df.drop(columns=[self.target_column], errors="ignore")
            if self.target_column
            else working_df.copy()
        )

        numeric_columns = self.numeric_columns
        categorical_columns = self.categorical_columns
        if numeric_columns is None or categorical_columns is None:
            inferred_numeric, inferred_categorical = infer_column_types(
                feature_df,
                target_column=None,
            )
            numeric_columns = numeric_columns or inferred_numeric
            categorical_columns = categorical_columns or inferred_categorical

        numeric_columns = list(numeric_columns or [])
        categorical_columns = list(categorical_columns or [])

        self.feature_columns_ = feature_df.columns.tolist()
        self.missing_value_artifacts_ = fit_missing_value_artifacts(
            feature_df,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            numeric_strategy=self.numeric_strategy,
            categorical_strategy=self.categorical_strategy,
        )

        prepared_df = apply_missing_value_artifacts(feature_df, self.missing_value_artifacts_)

        if self.outlier_multiplier is not None and numeric_columns:
            self.outlier_artifacts_ = fit_outlier_clip_artifacts(
                prepared_df,
                numeric_columns=numeric_columns,
                multiplier=self.outlier_multiplier,
            )
            prepared_df = apply_outlier_clip_artifacts(prepared_df, self.outlier_artifacts_)

        if self.encode_categorical:
            self.categorical_artifacts_ = fit_categorical_encoder(
                prepared_df,
                categorical_columns=categorical_columns,
                drop_first=self.drop_first,
                handle_unknown=self.handle_unknown,
            )
        else:
            self.categorical_artifacts_ = CategoricalEncodingArtifacts([], None, [])

        if self.scale_numeric:
            self.scaler_artifacts_ = fit_scaler(prepared_df, numeric_columns=numeric_columns)
        else:
            self.scaler_artifacts_ = NumericScalingArtifacts([], None)

        self.output_feature_names_ = self._build_output_feature_names()
        self.fitted_ = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform a DataFrame using the fitted preprocessing pipeline."""

        if not self.fitted_:
            raise RuntimeError("Preprocessing pipeline must be fitted before calling transform().")

        feature_df = (
            df.drop(columns=[self.target_column], errors="ignore")
            if self.target_column
            else df.copy()
        )

        feature_df = feature_df.loc[:, self.feature_columns_].copy()
        feature_df = apply_missing_value_artifacts(feature_df, self.missing_value_artifacts_)

        if self.outlier_artifacts_ is not None:
            feature_df = apply_outlier_clip_artifacts(feature_df, self.outlier_artifacts_)

        parts: list[pd.DataFrame] = []

        if self.scaler_artifacts_ is not None and self.scaler_artifacts_.numeric_columns:
            parts.append(apply_scaler(feature_df, self.scaler_artifacts_))
        elif self.numeric_columns:
            parts.append(feature_df[self.numeric_columns].copy())

        if self.encode_categorical and self.categorical_artifacts_ is not None:
            parts.append(apply_categorical_encoder(feature_df, self.categorical_artifacts_))
        elif self.categorical_columns:
            parts.append(feature_df[self.categorical_columns].copy())

        if not parts:
            return pd.DataFrame(index=feature_df.index)

        transformed = pd.concat(parts, axis=1)
        if self.output_feature_names_:
            transformed = transformed.loc[:, self.output_feature_names_]
        return transformed

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit the pipeline and return the transformed feature matrix."""

        return self.fit(df).transform(df)

    def save(self, path: str | Path) -> Path:
        """Serialize the fitted preprocessor to disk."""

        if not self.fitted_:
            raise RuntimeError("Cannot save an unfitted preprocessing pipeline.")

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, destination)
        return destination

    @classmethod
    def load(cls, path: str | Path) -> "TabularPreprocessor":
        """Load a serialized preprocessing pipeline from disk."""

        return joblib.load(Path(path))

    def _build_output_feature_names(self) -> list[str]:
        feature_names: list[str] = []

        if self.scaler_artifacts_ is not None and self.scaler_artifacts_.numeric_columns:
            feature_names.extend(self.scaler_artifacts_.numeric_columns)
        elif self.numeric_columns:
            feature_names.extend(self.numeric_columns)

        if self.encode_categorical and self.categorical_artifacts_ is not None:
            feature_names.extend(self.categorical_artifacts_.encoded_feature_names)
        elif self.categorical_columns:
            feature_names.extend(self.categorical_columns)

        return feature_names

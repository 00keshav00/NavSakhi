"""Typed configuration objects for training and inference."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import json

from .paths import (
    DATASETS_DIR,
    FEATURE_IMPORTANCE_DIR,
    INFERENCE_CONFIG_DIR,
    METRICS_DIR,
    MODELS_DIR,
    TRAINING_CONFIG_DIR,
)


@dataclass(slots=True)
class BaseConfig:
    """Base configuration with serialization helpers."""

    project_name: str = "SafeShe"
    random_state: int = 42

    def to_dict(self) -> dict[str, Any]:
        """Convert the config to a plain dictionary."""

        return asdict(self)

    def to_json(self, path: str | Path) -> Path:
        """Persist the config as formatted JSON."""

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return destination

    @classmethod
    def from_json(cls, path: str | Path) -> "BaseConfig":
        """Load a config from JSON on disk."""

        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**payload)


@dataclass(slots=True)
class TrainingConfig(BaseConfig):
    """Shared training configuration for both regression models."""

    datasets_dir: Path = DATASETS_DIR
    models_dir: Path = MODELS_DIR
    metrics_dir: Path = METRICS_DIR
    feature_importance_dir: Path = FEATURE_IMPORTANCE_DIR
    test_size: float = 0.2
    validation_size: float = 0.1
    shuffle: bool = True
    n_splits: int = 5
    scoring: str = "neg_mean_absolute_error"
    cv_jobs: int = -1
    model_save_format: str = "pkl"
    preprocess_save_format: str = "pkl"


@dataclass(slots=True)
class CrowdTrainingConfig(TrainingConfig):
    """Configuration defaults for crowd density training."""

    dataset_filename: str = "crowd_dataset.csv"
    model_filename: str = "crowd_model.pkl"
    metrics_filename: str = "crowd_metrics.json"
    feature_importance_filename: str = "crowd_feature_importance.json"
    target_column: str = "crowd_score"


@dataclass(slots=True)
class SafetyTrainingConfig(TrainingConfig):
    """Configuration defaults for safety score training."""

    dataset_filename: str = "safety_dataset.csv"
    model_filename: str = "safety_model.pkl"
    metrics_filename: str = "safety_metrics.json"
    feature_importance_filename: str = "safety_feature_importance.json"
    target_column: str = "safety_score"


@dataclass(slots=True)
class InferenceConfig(BaseConfig):
    """Configuration for runtime inference artifacts and defaults."""

    models_dir: Path = MODELS_DIR
    config_dir: Path = INFERENCE_CONFIG_DIR
    default_output_precision: int = 4
    crowd_model_filename: str = "crowd_model.pkl"
    safety_model_filename: str = "safety_model.pkl"
    crowd_preprocessor_filename: str = "crowd_preprocessor.pkl"
    safety_preprocessor_filename: str = "safety_preprocessor.pkl"

"""Artifact IO helpers for models, preprocessors, and metrics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import json
import joblib


def save_json(data: Any, path: str | Path) -> Path:
    """Save JSON-serializable data to disk."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def load_json(path: str | Path) -> Any:
    """Load JSON data from disk."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_joblib_artifact(obj: Any, path: str | Path) -> Path:
    """Serialize a Python object to disk using joblib."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(obj, destination)
    return destination


def load_joblib_artifact(path: str | Path) -> Any:
    """Load a joblib artifact from disk."""

    return joblib.load(Path(path))

"""Generic configuration helpers."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Protocol, TypeVar

import json


class SupportsToDict(Protocol):
    """Protocol for configuration objects that can be serialized."""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""


ConfigT = TypeVar("ConfigT")


def resolve_project_path(*parts: str | Path, base_dir: Path | None = None) -> Path:
    """Resolve a path relative to the project root or a custom base directory."""

    root = base_dir or Path(__file__).resolve().parents[1]
    return root.joinpath(*map(Path, parts))


def _to_serializable_dict(config: Any) -> dict[str, Any]:
    if hasattr(config, "to_dict") and callable(config.to_dict):
        return config.to_dict()
    if is_dataclass(config):
        return asdict(config)
    if isinstance(config, dict):
        return dict(config)
    raise TypeError("Config object must be a dataclass, dict, or expose to_dict().")


def save_json_config(config: Any, path: str | Path) -> Path:
    """Save a config object to JSON with parent-directory creation."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(_to_serializable_dict(config), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination


def load_json_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON config file into a dictionary."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


class ConfigIOMixin:
    """Mixin that adds JSON persistence helpers to config dataclasses."""

    def to_dict(self) -> dict[str, Any]:
        """Convert the dataclass to a dictionary."""

        return _to_serializable_dict(self)

    def save(self, path: str | Path) -> Path:
        """Persist the config to JSON."""

        return save_json_config(self, path)

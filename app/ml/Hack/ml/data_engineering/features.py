"""Feature assembly for crowd and safety datasets."""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from .schemas import CrowdFeatureRow, SafetyFeatureRow


def _ensure_columns(df: pd.DataFrame, required_columns: Sequence[str]) -> pd.DataFrame:
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise KeyError(f"Missing required columns: {missing_columns}")
    return df.copy()


def build_crowd_features(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw crowd source inputs to the canonical crowd feature set."""

    required_columns = [
        "latitude",
        "longitude",
        "hour",
        "day_of_week",
        "restaurant_count",
        "bus_stop_count",
        "metro_count",
        "office_density",
        "commercial_density_score",
        "population_density",
    ]
    normalized = _ensure_columns(df, required_columns)
    return normalized[required_columns].copy()


def build_safety_features(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw safety source inputs to the canonical safety feature set."""

    required_columns = [
        "crime_score",
        "crowd_score",
        "weather_risk",
        "lighting_score",
        "police_distance",
        "hospital_distance",
        "community_reports",
        "hour",
        "day_of_week",
        "road_type_risk",
        "walking_distance",
        "transport_mode",
    ]
    normalized = _ensure_columns(df, required_columns)
    return normalized[required_columns].copy()

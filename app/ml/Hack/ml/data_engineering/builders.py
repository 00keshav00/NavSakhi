"""Dataset builders for crowd and safety CSV generation."""

from __future__ import annotations

import pandas as pd

from .features import build_crowd_features, build_safety_features
from .labels import generate_crowd_score, generate_safety_score


def build_crowd_dataset(source_frame: pd.DataFrame) -> pd.DataFrame:
    """Build the crowd training dataset with a generated target label."""

    features = build_crowd_features(source_frame)
    dataset = features.copy()

    dataset["crowd_score"] = dataset.apply(
        lambda row: generate_crowd_score(
            commercial_density=float(row["commercial_density_score"]),
            office_density=float(row["office_density"]),
            restaurant_density=float(row["restaurant_count"]),
            bus_stop_density=float(row["bus_stop_count"]),
            metro_density=float(row["metro_count"]),
            school_college_density=float(row.get("school_college_density", 0.0)),
            market_density=float(row.get("market_density", 0.0)),
            time_weight=float(row.get("time_weight", 0.0)),
        ),
        axis=1,
    )
    return dataset


def build_safety_dataset(source_frame: pd.DataFrame) -> pd.DataFrame:
    """Build the safety training dataset with a generated target label."""

    features = build_safety_features(source_frame)
    dataset = features.copy()

    dataset["safety_score"] = dataset.apply(
        lambda row: generate_safety_score(
            crime_score=float(row["crime_score"]),
            crowd_score=float(row["crowd_score"]),
            weather_risk=float(row["weather_risk"]),
            lighting_score=float(row["lighting_score"]),
            police_distance=float(row["police_distance"]),
            community_reports=float(row["community_reports"]),
            hospital_distance=float(row["hospital_distance"]),
            road_type_risk=float(row["road_type_risk"]),
        ),
        axis=1,
    )
    return dataset

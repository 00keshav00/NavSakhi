"""Schema validation helpers for generated datasets."""

from __future__ import annotations

import pandas as pd

from ..utils.validation import assert_columns_present, assert_dataframe_not_empty


def validate_crowd_dataset(df: pd.DataFrame) -> None:
    """Validate the crowd dataset schema before export."""

    assert_dataframe_not_empty(df, name="Crowd dataset")
    assert_columns_present(
        df,
        [
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
            "crowd_score",
        ],
        name="Crowd dataset",
    )


def validate_safety_dataset(df: pd.DataFrame) -> None:
    """Validate the safety dataset schema before export."""

    assert_dataframe_not_empty(df, name="Safety dataset")
    assert_columns_present(
        df,
        [
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
            "safety_score",
        ],
        name="Safety dataset",
    )

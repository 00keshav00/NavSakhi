"""Typed schemas for the dataset engineering layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


TransportMode = Literal["walk", "bike", "car", "transit", "ride_hail", "other"]
RoadType = Literal["residential", "primary", "secondary", "tertiary", "service", "unclassified", "other"]


@dataclass(slots=True)
class CrowdFeatureRow:
    """Canonical crowd feature record."""

    latitude: float
    longitude: float
    hour: int
    day_of_week: int
    restaurant_count: float
    bus_stop_count: float
    metro_count: float
    office_density: float
    commercial_density_score: float
    population_density: float


@dataclass(slots=True)
class SafetyFeatureRow:
    """Canonical safety feature record."""

    crime_score: float
    crowd_score: float
    weather_risk: float
    lighting_score: float
    police_distance: float
    hospital_distance: float
    community_reports: float
    hour: int
    day_of_week: int
    road_type_risk: float
    walking_distance: float
    transport_mode: TransportMode

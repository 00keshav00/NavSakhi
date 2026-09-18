"""Label generation for crowd and safety datasets."""

from __future__ import annotations

from dataclasses import dataclass


def _clamp_0_100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def generate_crowd_score(
    commercial_density: float,
    office_density: float,
    restaurant_density: float,
    bus_stop_density: float,
    metro_density: float,
    school_college_density: float,
    market_density: float,
    time_weight: float,
) -> float:
    """Compute the synthetic crowd label from the approved formula."""

    raw_score = (
        0.30 * commercial_density
        + 0.20 * office_density
        + 0.15 * restaurant_density
        + 0.10 * bus_stop_density
        + 0.10 * metro_density
        + 0.05 * school_college_density
        + 0.05 * market_density
        + 0.05 * time_weight
    )
    return _clamp_0_100(raw_score)


def generate_safety_score(
    crime_score: float,
    crowd_score: float,
    weather_risk: float,
    lighting_score: float,
    police_distance: float,
    community_reports: float,
    hospital_distance: float,
    road_type_risk: float,
) -> float:
    """Compute the synthetic safety label from the approved formula."""

    raw_score = (
        0.35 * crime_score
        + 0.20 * crowd_score
        + 0.10 * lighting_score
        + 0.10 * police_distance
        + 0.10 * community_reports
        + 0.05 * weather_risk
        + 0.05 * hospital_distance
        + 0.05 * road_type_risk
    )
    return _clamp_0_100(raw_score)


def safety_band(score: float) -> str:
    """Map a score into the approved safety band labels."""

    normalized_score = _clamp_0_100(score)
    if normalized_score < 30:
        return "unsafe"
    if normalized_score < 60:
        return "moderate"
    if normalized_score < 80:
        return "safe"
    return "very_safe"

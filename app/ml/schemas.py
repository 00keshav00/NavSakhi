from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# 41 Canonical Predictor Features frozen in schema 2.0.0
CANONICAL_PREDICTOR_FEATURES: List[str] = [
    'latitude', 'longitude', 'length_m', 'road_type', 'surface',
    'crossing', 'curvature', 'road_width', 'speed',
    'atm_count_50m', 'bank_count_100m', 'bus_stop_count_50m', 'cafe_count_100m',
    'college_count_250m', 'commercial_density', 'fuel_count_250m', 'hotel_count_250m',
    'mall_count_250m', 'metro_count_500m', 'park_count_250m', 'pharmacy_count_100m',
    'restaurant_count_100m', 'school_count_250m', 'hospital_dist_m', 'police_dist_m',
    'high_density_indicator', 'low_density_indicator', 'population_count_100m',
    'population_density', 'population_missing_coverage', 'population_percentile',
    'urban_indicator', 'accessibility_score', 'transit_density',
    'emergency_accessibility', 'walkability', 'isolation_index',
    'road_complexity', 'human_activity_score', 'desertion_score',
    'essential_services_density'
]

CATEGORICAL_FEATURES: List[str] = ['road_type', 'surface']

NUMERICAL_FEATURES: List[str] = [c for c in CANONICAL_PREDICTOR_FEATURES if c not in CATEGORICAL_FEATURES]


class SegmentSafetyPrediction(BaseModel):
    """Prediction output for a single road segment."""
    segment_id: Optional[str] = None
    safety_score: float = Field(..., ge=0.0, le=100.0, description="Safety score (0 = least safe, 100 = safest)")
    confidence: float = Field(..., ge=0.0, le=100.0, description="Model confidence score")
    risk_level: str = Field(..., description="Categorical risk: Low, Moderate, High")
    is_synthetic_proxy: bool = True

"""
Spatial Matching Service wrapper under app.services.
"""
from app.intelligence.journey.spatial_matcher import SpatialMatchingService
from app.schemas.spatial_schemas import (
    MatchStatus,
    FeatureStatus,
    MatchedSegmentResult,
    UnmatchedInterval,
    RouteCoverageMetrics,
    RouteSpatialMatchResponse,
)

__all__ = [
    "SpatialMatchingService",
    "MatchStatus",
    "FeatureStatus",
    "MatchedSegmentResult",
    "UnmatchedInterval",
    "RouteCoverageMetrics",
    "RouteSpatialMatchResponse",
]

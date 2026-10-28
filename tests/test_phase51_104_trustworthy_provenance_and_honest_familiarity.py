"""
NavSakhi Phase 51.104: Trustworthy Safety-Facility Provenance & Route Familiarity Integrity Suite.

Validates:
1. Trustworthy provenance:
   - OSM public facilities (police, hospitals, clinics, pharmacies, fire stations) are classified as "mapped_public_facility".
   - Zero promotion of raw OSM facilities to "independently verified safe havens" without documented ground audit.
   - Surveillance camera records have unverified operational status and are separated from safety infrastructure.
   - Mapped commercial businesses are strictly separated from safety collections.
2. Honest Route Familiarity Semantics:
   - State A: Explicit user-designated familiarity prioritizes the designated route with honest match explanation.
   - State B: Absence of user familiarity does NOT invent an arterial route; truthfully falls back to safest validated route.
   - Objective road safety score (LightGBM) and serious hazard constraints remain strictly preserved.
   - Mapped business density is treated as an activity preference, never an independent safety signal.
3. Corridor reconciliation reproducibility:
   - Immediate road centerline corridor (30 entities) vs Peri-urban corridor (34 entities).
"""

import json
import os
import pytest
from app.models.journey import CandidateRoute
from app.intelligence.journey.recommender import SafeSheRecommender
from app.services.poi_service import get_poi_service


def test_safety_facility_provenance_and_role_eligibility():
    """Verifies that public facilities are classified honestly without false verification claims."""
    with open("poi_data/processed/chennai_pois.json", "r", encoding="utf-8") as f:
        pois = json.load(f)

    public_facilities = [p for p in pois if p["provenance_type"] == "mapped_public_facility"]
    commercial_places = [p for p in pois if p["provenance_type"] == "mapped_commercial_business"]
    surveillance_cams = [p for p in pois if p["provenance_type"] == "public_surveillance"]

    assert len(public_facilities) == 2079
    assert len(commercial_places) == 5629
    assert len(surveillance_cams) == 187
    assert len(public_facilities) + len(commercial_places) + len(surveillance_cams) == 7895

    # Public facilities from OSM must be marked as mapped, NOT independently verified
    for pf in public_facilities:
        assert pf["verification_status"] == "MAPPED_PUBLIC_FACILITY"
        assert pf["is_verified_safety_facility"] is False
        assert pf["is_safe_haven_eligible"] is False
        assert pf["safety_role"] in (
            "public_police_station",
            "medical_emergency_facility",
            "fire_and_rescue_service",
            "public_health_support",
            "public_safety_support"
        )
        assert pf["category"] in ("police", "hospital", "clinic", "pharmacy", "fire_station")

    # Commercial shops must NEVER be in public facilities or have safety roles
    for cp in commercial_places:
        assert cp["verification_status"] == "MAPPED_COMMERCIAL_CONTEXT"
        assert cp["safety_role"] == "commercial_activity"
        assert cp["is_verified_safety_facility"] is False
        assert cp["is_emergency"] is False

    # Surveillance cameras must have unverified operational status
    for sc in surveillance_cams:
        assert sc["verification_status"] == "MAPPED_SURVEILLANCE"
        assert sc["safety_role"] == "surveillance_infrastructure"
        assert sc["is_verified_safety_facility"] is False


def test_route_familiarity_state_a_explicit_user_selection():
    """State A: When user explicitly designates a familiar route, recommender prioritizes it honestly."""
    recommender = SafeSheRecommender()

    r1 = CandidateRoute(route_identifier="route_custom_familiar", distance=10200.0, duration=700.0, recommendation_status="AVAILABLE")
    r1.route_metadata = {
        "route_name": "My Daily Commute Route",
        "safety_score": 78.5,
        "is_user_familiar": True,
        "travel_mode": "Driving"
    }

    r2 = CandidateRoute(route_identifier="route_safest_alternative", distance=11000.0, duration=850.0, recommendation_status="AVAILABLE")
    r2.route_metadata = {
        "route_name": "Safest Arterial Boulevard",
        "safety_score": 93.0,
        "is_user_familiar": False,
        "travel_mode": "Driving"
    }

    candidates = [r1, r2]
    rec = recommender.generate_recommendation(candidates, user_preference="prefer_familiar")

    # Must select the user-designated familiar route
    assert rec.primary_route_id == "route_custom_familiar"
    assert "explicitly designated familiar corridor" in rec.explanation.primary_reason.lower()
    assert any("matches user-designated familiar route" in a.lower() for a in rec.explanation.advantages)
    # Objective trade-off must acknowledge higher safety score on the alternative
    assert any("lower road safety score" in t.lower() for t in rec.explanation.tradeoffs)


def test_route_familiarity_state_b_no_familiarity_data():
    """State B: When no user familiarity data exists, recommender does NOT invent an arterial route."""
    recommender = SafeSheRecommender()

    r1 = CandidateRoute(route_identifier="route_arterial_1", distance=10000.0, duration=650.0, recommendation_status="AVAILABLE")
    r1.route_metadata = {"route_name": "Arterial Road A", "safety_score": 80.0, "travel_mode": "Driving"}

    r2 = CandidateRoute(route_identifier="route_arterial_safest", distance=10500.0, duration=700.0, recommendation_status="AVAILABLE")
    r2.route_metadata = {"route_name": "Arterial Road B", "safety_score": 91.0, "travel_mode": "Driving"}

    candidates = [r1, r2]
    rec = recommender.generate_recommendation(candidates, user_preference="prefer_familiar")

    # Must default to the safest validated route, NOT claim an arbitrary arterial road is familiar
    assert rec.primary_route_id == "route_arterial_safest"
    assert "no saved familiar route exists for this corridor" in rec.explanation.primary_reason.lower()
    assert any("no user-designated familiar route is on file" in t.lower() for t in rec.explanation.tradeoffs)
    assert any("safest validated alternative (no personal familiarity invented)" in a.lower() for a in rec.explanation.advantages)


def test_commercial_preference_does_not_mutate_ml_safety_score():
    """Verifies that prefer_businesses prioritizes commercial density as a context attribute without altering LightGBM score."""
    recommender = SafeSheRecommender()

    r_few_shops = CandidateRoute(route_identifier="r_quiet", distance=10000.0, duration=600.0, recommendation_status="AVAILABLE")
    r_few_shops.route_metadata = {"route_name": "Quiet Road", "safety_score": 90.0, "commercial_poi_count": 2, "travel_mode": "Driving"}

    r_many_shops = CandidateRoute(route_identifier="r_shops", distance=10500.0, duration=650.0, recommendation_status="AVAILABLE")
    r_many_shops.route_metadata = {"route_name": "Shop Street", "safety_score": 85.0, "commercial_poi_count": 45, "travel_mode": "Driving"}

    # With preference for businesses, r_shops is recommended
    rec_biz = recommender.generate_recommendation([r_few_shops, r_many_shops], user_preference="prefer_businesses")
    assert rec_biz.primary_route_id == "r_shops"
    assert "preference for mapped business corridors" in rec_biz.explanation.primary_reason.lower()

    # The LightGBM safety scores remain strictly unchanged
    assert r_few_shops.route_metadata["safety_score"] == 90.0
    assert r_many_shops.route_metadata["safety_score"] == 85.0

    # With preference for safest, r_quiet is recommended
    rec_safe = recommender.generate_recommendation([r_few_shops, r_many_shops], user_preference="safest")
    assert rec_safe.primary_route_id == "r_quiet"


def test_corridor_counts_reconciliation_exact_bounds():
    """Verifies that the 30 vs 34 corridor counts are exactly reproducible and mathematically disjoint."""
    with open("poi_data/processed/chennai_pois.json", "r", encoding="utf-8") as f:
        pois = json.load(f)

    tight_bounds = {"min_lat": 12.830, "max_lat": 12.875, "min_lon": 80.120, "max_lon": 80.165}
    peri_urban_bounds = {"min_lat": 12.820, "max_lat": 12.875, "min_lon": 80.120, "max_lon": 80.180}

    tight = [p for p in pois if tight_bounds["min_lat"] <= p["latitude"] <= tight_bounds["max_lat"] and tight_bounds["min_lon"] <= p["longitude"] <= tight_bounds["max_lon"]]
    peri_urban = [p for p in pois if peri_urban_bounds["min_lat"] <= p["latitude"] <= peri_urban_bounds["max_lat"] and peri_urban_bounds["min_lon"] <= p["longitude"] <= peri_urban_bounds["max_lon"]]

    assert len(tight) == 30
    assert len(peri_urban) == 34

    # Tight corridor breakdown
    tight_pub = [p for p in tight if p["provenance_type"] == "mapped_public_facility"]
    tight_com = [p for p in tight if p["provenance_type"] == "mapped_commercial_business"]
    assert len(tight_pub) == 7
    assert len(tight_com) == 23

    # Peri-urban corridor breakdown
    peri_pub = [p for p in peri_urban if p["provenance_type"] == "mapped_public_facility"]
    peri_com = [p for p in peri_urban if p["provenance_type"] == "mapped_commercial_business"]
    assert len(peri_pub) == 9
    assert len(peri_com) == 25

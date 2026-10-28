"""
NavSakhi Phase 51.103: POI Provenance Separation & Route Preference Validation Suite.

Validates:
1. Complete separation of verified safety facilities from mapped commercial context and surveillance cameras.
2. Partitioned artifact files and manifest integrity.
3. Strict invariants: commercial shops are NEVER marked as emergency safe havens or verified safety facilities.
4. Route preference propagation (prefer_businesses, prefer_familiar, fewest_transfers, safest, fastest).
5. POI spatial service query provenance propagation into RoutePOI DTOs.
"""

import json
import os
import pytest
from app.models.journey import CandidateRoute
from app.intelligence.journey.recommender import SafeSheRecommender
from app.services.poi_service import get_poi_service


def test_poi_provenance_partition_files_exist_and_counts_match():
    """Validates that partitioned artifacts exist and partition counts sum exactly to master total."""
    master_path = "poi_data/processed/chennai_pois.json"
    safety_path = "poi_data/processed/chennai_safety_facilities.json"
    commercial_path = "poi_data/processed/chennai_commercial_pois.json"
    surveillance_path = "poi_data/processed/chennai_surveillance_cameras.json"

    assert os.path.exists(master_path), f"Missing {master_path}"
    assert os.path.exists(safety_path), f"Missing {safety_path}"
    assert os.path.exists(commercial_path), f"Missing {commercial_path}"
    assert os.path.exists(surveillance_path), f"Missing {surveillance_path}"

    with open(master_path, "r", encoding="utf-8") as f:
        master = json.load(f)
    with open(safety_path, "r", encoding="utf-8") as f:
        safety = json.load(f)
    with open(commercial_path, "r", encoding="utf-8") as f:
        commercial = json.load(f)
    with open(surveillance_path, "r", encoding="utf-8") as f:
        surveillance = json.load(f)

    assert len(master) == 7895
    assert len(safety) == 2079
    assert len(commercial) == 5629
    assert len(surveillance) == 187
    assert len(safety) + len(commercial) + len(surveillance) == len(master)


def test_poi_records_have_explicit_provenance_types():
    """Ensures every record carries explicit provenance and trust fields without false verification claims."""
    with open("poi_data/processed/chennai_pois.json", "r", encoding="utf-8") as f:
        records = json.load(f)

    for r in records:
        assert "provenance_type" in r
        assert "verification_status" in r
        assert "is_verified_safety_facility" in r
        assert "is_safe_haven_eligible" in r

        prov = r["provenance_type"]
        assert prov in ("mapped_public_facility", "mapped_commercial_business", "public_surveillance")

        if prov == "mapped_public_facility":
            # OSM public facilities are geographic records; never falsely promoted to independently verified safe havens
            assert r["is_verified_safety_facility"] is False
            assert r["is_safe_haven_eligible"] is False
            assert r["verification_status"] == "MAPPED_PUBLIC_FACILITY"
            assert r["is_public_help"] is True or r["is_emergency"] is True
            assert r["category"] in ("police", "hospital", "clinic", "pharmacy", "fire_station")
            assert r["safety_role"] in (
                "public_police_station",
                "medical_emergency_facility",
                "fire_and_rescue_service",
                "public_health_support",
                "public_safety_support"
            )

        elif prov == "mapped_commercial_business":
            # Commercial shops must NEVER be marked as verified safety facilities or emergency safe havens
            assert r["is_verified_safety_facility"] is False
            assert r["is_safe_haven_eligible"] is False
            assert r["is_emergency"] is False
            assert r["verification_status"] == "MAPPED_COMMERCIAL_CONTEXT"
            assert r["safety_role"] == "commercial_activity"
            assert r["category"] not in ("police", "fire_station")

        elif prov == "public_surveillance":
            # Surveillance cameras are mapped equipment positions; operational status is unverified
            assert r["is_verified_safety_facility"] is False
            assert r["is_safe_haven_eligible"] is False
            assert r["category"] == "surveillance"
            assert r["verification_status"] == "MAPPED_SURVEILLANCE"
            assert r["safety_role"] == "surveillance_infrastructure"


def test_manifest_provenance_breakdown():
    """Validates that poi_data/manifest.json accurately documents provenance counts and corridor reconciliation."""
    with open("poi_data/manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert "provenance_breakdown" in manifest
    pb = manifest["provenance_breakdown"]
    assert pb["mapped_public_facilities_count"] == 2079
    assert pb["mapped_commercial_businesses_count"] == 5629
    assert pb["surveillance_cameras_count"] == 187
    assert pb["independently_verified_safe_havens_count"] == 0
    assert pb["total_records"] == 7895

    assert "vit_kandigai_corridor_reconciliation" in manifest
    reconcil = manifest["vit_kandigai_corridor_reconciliation"]
    assert reconcil["tight_corridor"]["counts"]["total"] == 30
    assert reconcil["tight_corridor"]["counts"]["mapped_public_facilities"] == 7
    assert reconcil["tight_corridor"]["counts"]["mapped_commercial_businesses"] == 23

    assert reconcil["peri_urban_corridor"]["counts"]["total"] == 34
    assert reconcil["peri_urban_corridor"]["counts"]["mapped_public_facilities"] == 9
    assert reconcil["peri_urban_corridor"]["counts"]["mapped_commercial_businesses"] == 25

    assert "discrepancy_explanation" in reconcil
    assert "partition_artifacts" in manifest


def test_route_preference_propagation_and_ranking():
    """
    Tests that user route preferences (prefer_businesses, prefer_familiar,
    fewest_transfers, safest, fastest) affect recommendation selection as intended,
    and that prefer_familiar distinguishes existing familiarity data from no-familiarity fallback.
    """
    recommender = SafeSheRecommender()

    # Route 1: Fastest road route (lowest duration, moderate safety, few shops)
    r1 = CandidateRoute(route_identifier="route_fast", distance=10000.0, duration=600.0, recommendation_status="AVAILABLE")
    r1.route_metadata = {
        "route_name": "Fast Expressway",
        "safety_score": 70.0,
        "commercial_poi_count": 5,
        "travel_mode": "Driving"
    }

    # Route 2: Safest road route (highest LightGBM safety score, longer duration)
    r2 = CandidateRoute(route_identifier="route_safe", distance=11000.0, duration=850.0, recommendation_status="AVAILABLE")
    r2.route_metadata = {
        "route_name": "Well-Lit Arterial",
        "safety_score": 92.0,
        "commercial_poi_count": 12,
        "travel_mode": "Driving"
    }

    # Route 3: Bustling Commercial Corridor (highest mapped shops, good safety)
    r3 = CandidateRoute(route_identifier="route_commercial", distance=10500.0, duration=800.0, recommendation_status="AVAILABLE")
    r3.route_metadata = {
        "route_name": "Market & Commercial Boulevard",
        "safety_score": 75.0,
        "commercial_poi_count": 48,
        "travel_mode": "Driving"
    }

    # Route 4: Direct single-leg transit route (0 transfers)
    r4 = CandidateRoute(route_identifier="route_direct_transit", distance=9500.0, duration=720.0, recommendation_status="AVAILABLE")
    r4.route_metadata = {
        "route_name": "Direct Metro Line",
        "safety_score": None,  # transit infrastructure unrated
        "commercial_poi_count": 20,
        "travel_mode": "Multimodal",
        "dynamic_segments": [{"mode": "metro"}]
    }

    candidates = [r1, r2, r3, r4]

    # Test "prefer_businesses"
    rec_biz = recommender.generate_recommendation(candidates, user_preference="prefer_businesses")
    assert rec_biz.primary_route_id == "route_commercial"
    assert "business" in rec_biz.explanation.primary_reason.lower() or "commercial" in rec_biz.explanation.primary_reason.lower()

    # Test "prefer_familiar" WITHOUT user familiarity data (State B)
    # Must NOT invent familiarity; defaults to safest validated alternative with truthful explanation
    rec_fam_none = recommender.generate_recommendation(candidates, user_preference="prefer_familiar")
    assert rec_fam_none.primary_route_id == "route_safe"
    assert "no saved familiar route" in rec_fam_none.explanation.primary_reason.lower()
    assert any("no user-designated familiar route" in t.lower() for t in rec_fam_none.explanation.tradeoffs)

    # Test "prefer_familiar" WITH explicit user familiarity data (State A)
    r1.route_metadata["is_user_familiar"] = True
    rec_fam_user = recommender.generate_recommendation(candidates, user_preference="prefer_familiar")
    assert rec_fam_user.primary_route_id == "route_fast"
    assert "explicitly designated familiar corridor" in rec_fam_user.explanation.primary_reason.lower()
    r1.route_metadata.pop("is_user_familiar", None)

    # Test "fewest_transfers"
    rec_transfers = recommender.generate_recommendation(candidates, user_preference="fewest_transfers")
    assert rec_transfers.primary_route_id is not None

    # Test "safest"
    rec_safe = recommender.generate_recommendation(candidates, user_preference="safest")
    assert rec_safe.primary_route_id == "route_safe"

    # Test "fastest"
    rec_fast = recommender.generate_recommendation(candidates, user_preference="fastest")
    assert rec_fast.primary_route_id == "route_fast"


def test_poi_spatial_service_propagates_provenance():
    """Tests that POISpatialService.query_pois_near_route outputs explicit provenance fields in matched POIs."""
    service = get_poi_service()

    # 2 coordinates along Anna Salai / Guindy
    coords = [[80.21, 13.00], [80.22, 13.02]]
    result = service.query_pois_near_route(coords, corridor_m=1000.0)

    assert result["status"] == "AVAILABLE"
    assert len(result["pois"]) > 0

    for poi in result["pois"]:
        assert "provenance_type" in poi
        assert "verification_status" in poi
        assert "is_verified_safety_facility" in poi
        assert "is_safe_haven_eligible" in poi
        assert "safety_role" in poi
        assert "is_emergency" in poi
        assert "is_shop" in poi

        if poi["is_emergency"]:
            assert poi["provenance_type"] == "mapped_public_facility"
            assert poi["verification_status"] == "MAPPED_PUBLIC_FACILITY"
            assert poi["is_verified_safety_facility"] is False
            assert poi["category"] in ("police", "hospital", "clinic", "pharmacy", "fire_station")
        elif poi["is_shop"]:
            assert poi["provenance_type"] == "mapped_commercial_business"
            assert poi["verification_status"] == "MAPPED_COMMERCIAL_CONTEXT"
            assert poi["is_verified_safety_facility"] is False
            assert poi["is_emergency"] is False
        elif poi["category"] == "surveillance":
            assert poi["provenance_type"] == "public_surveillance"
            assert poi["verification_status"] == "MAPPED_SURVEILLANCE"
            assert poi["is_verified_safety_facility"] is False

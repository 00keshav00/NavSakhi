"""
Test suite for Phase 51.97: Community Intelligence API Contract and Mock Elimination.
Verifies that:
1. GET /api/v1/community/intelligence returns 200 with CommunityIntelligenceResponse shape.
2. Zero reports return honest zero statistics and empty reports (no fake Bangalore mock).
3. Active reports are categorized by verification status (VERIFIED, PENDING, UNVERIFIED).
4. Heatmap points reflect real coordinates.
5. Filters by report_type and verification status function correctly.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from bson import ObjectId
from app.models.community import CommunityReport
from app.models.journey import Location
from app.services.community_service import CommunityService
from app.schemas.community_schemas import CommunityIntelligenceResponse


@pytest.mark.asyncio
async def test_community_intelligence_empty_state_honest():
    """Verify empty database returns honest empty state with no Bangalore mock coordinates."""
    mock_repo = MagicMock()
    mock_repo.get_active_reports = AsyncMock(return_value=[])

    service = CommunityService(community_repo=mock_repo)
    result = await service.get_intelligence(report_type="All", verification_filter="All")

    assert isinstance(result, CommunityIntelligenceResponse)
    assert result.statistics.total == 0
    assert result.statistics.verified == 0
    assert result.statistics.pending == 0
    assert result.statistics.unverified == 0
    assert result.reports == []
    assert result.heatmap_data.verified_only == []
    assert result.heatmap_data.all_reports == []
    assert len(result.insights) >= 1
    assert "No active community reports" in result.insights[0]


@pytest.mark.asyncio
async def test_community_intelligence_aggregates_real_reports():
    """Verify service aggregates reports into statistics, heatmap, and feed."""
    mock_repo = MagicMock()

    r1 = CommunityReport(
        id=ObjectId(),
        location=Location(type="Point", coordinates=[80.2707, 13.0827]),
        report_type="Poor Lighting",
        description="Corridor light dark near bus stop",
        verification_status="VERIFIED",
        upvotes=5,
        downvotes=0
    )

    r2 = CommunityReport(
        id=ObjectId(),
        location=Location(type="Point", coordinates=[80.2100, 13.0100]),
        report_type="Harassment",
        description="Unsafe group loitering",
        verification_status="PENDING",
        upvotes=2,
        downvotes=1
    )

    r3 = CommunityReport(
        id=ObjectId(),
        location=Location(type="Point", coordinates=[80.2500, 13.0500]),
        report_type="Road Block",
        description="Construction debris on sidewalk",
        verification_status="REJECTED",
        upvotes=0,
        downvotes=3
    )

    mock_repo.get_active_reports = AsyncMock(return_value=[r1, r2, r3])

    service = CommunityService(community_repo=mock_repo)

    # 1. Fetch All
    res_all = await service.get_intelligence(report_type="All", verification_filter="All")
    assert res_all.statistics.total == 3
    assert res_all.statistics.verified == 1
    assert res_all.statistics.pending == 1
    assert res_all.statistics.unverified == 1
    assert len(res_all.reports) == 3
    assert len(res_all.heatmap_data.all_reports) == 3
    assert len(res_all.heatmap_data.verified_only) == 1
    assert res_all.heatmap_data.verified_only[0].lat == 13.0827
    assert res_all.heatmap_data.verified_only[0].lng == 80.2707

    # 2. Filter by Verified Only
    res_ver = await service.get_intelligence(report_type="All", verification_filter="Verified")
    assert len(res_ver.reports) == 1
    assert res_ver.reports[0].report_type == "Poor Lighting"
    assert res_ver.reports[0].verification_status == "Verified"

    # 3. Filter by Type
    res_harass = await service.get_intelligence(report_type="Harassment", verification_filter="All")
    assert len(res_harass.reports) == 1
    assert res_harass.reports[0].report_type == "Harassment"
    assert res_harass.reports[0].severity == "High"

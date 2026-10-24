from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.schemas.responses import StandardResponse
from app.schemas.dashboard_schemas import DashboardOverviewResponse
from app.api.dependencies import get_optional_user_id

router = APIRouter()

@router.get("/overview", response_model=StandardResponse[DashboardOverviewResponse])
async def get_dashboard_overview(
    lat: Optional[float] = Query(None, description="Optional user latitude"),
    lon: Optional[float] = Query(None, description="Optional user longitude"),
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    effective_user_id = user_id or "guest"
    overview = await coordinator.build_dashboard_overview(user_id=effective_user_id, lat=lat, lon=lon)
    return StandardResponse(success=True, data=overview)

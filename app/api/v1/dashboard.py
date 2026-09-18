from fastapi import APIRouter, Depends
from app.schemas.responses import StandardResponse
from app.schemas.dashboard_schemas import DashboardOverviewResponse
from app.api.dependencies import get_current_user_id

router = APIRouter()

@router.get("/overview", response_model=StandardResponse[DashboardOverviewResponse])
async def get_dashboard_overview(user_id: str = Depends(get_current_user_id)):
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    overview = await coordinator.build_dashboard_overview(user_id)
    return StandardResponse(success=True, data=overview)

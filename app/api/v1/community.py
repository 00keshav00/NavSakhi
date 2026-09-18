from fastapi import APIRouter, Depends, Query
from typing import List
from app.schemas.responses import StandardResponse
from app.schemas.community_schemas import CommunityReportCreate, CommunityReportResponse
from app.services.community_service import CommunityService
from app.api.dependencies import get_community_service, get_current_user_id

router = APIRouter()

@router.post("/", response_model=StandardResponse[CommunityReportResponse], status_code=201)
async def create_report(
    data: CommunityReportCreate,
    user_id: str = Depends(get_current_user_id),
    community_service: CommunityService = Depends(get_community_service)
):
    report = await community_service.create_report(user_id, data)
    # Use model_validate so Pydantic resolves field aliases correctly
    response_item = CommunityReportResponse.model_validate(report.model_dump(by_alias=True))
    return StandardResponse(success=True, data=response_item)

@router.get("/nearby", response_model=StandardResponse[List[CommunityReportResponse]])
async def get_nearby_reports(
    lon: float = Query(...),
    lat: float = Query(...),
    radius: float = Query(5000),
    community_service: CommunityService = Depends(get_community_service)
):
    reports = await community_service.get_nearby_reports([lon, lat], radius)
    # Use model_validate so Pydantic resolves field aliases correctly
    data = [CommunityReportResponse.model_validate(report.model_dump(by_alias=True)) for report in reports]
    return StandardResponse(success=True, data=data)

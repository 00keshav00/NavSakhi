from app.repositories.community_repository import CommunityRepository
from app.models.community import CommunityReport
from app.schemas.community_schemas import CommunityReportCreate
from typing import List

class CommunityService:
    def __init__(self, community_repo: CommunityRepository):
        self.community_repo = community_repo

    async def get_nearby_reports(self, coordinates: List[float], radius_meters: float = 5000) -> List[CommunityReport]:
        return await self.community_repo.get_nearby_reports(coordinates, radius_meters)

    async def create_report(self, user_id: str, data: CommunityReportCreate) -> CommunityReport:
        report = CommunityReport(
            user_id=user_id,
            location=data.location,
            report_type=data.report_type,
            description=data.description
        )
        return await self.community_repo.create(report)

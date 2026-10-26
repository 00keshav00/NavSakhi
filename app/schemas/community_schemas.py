from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Optional, List, Any
from app.models.journey import Location


class CommunityReportCreate(BaseModel):
    location: Location
    report_type: str
    description: Optional[str] = None
    severity: Optional[str] = "Medium"
    is_anonymous: Optional[bool] = False


class CommunityReportResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default="")
    _id: Optional[str] = None
    user_id: Optional[str] = None
    location: Location
    report_type: str
    description: Optional[str] = None
    verification_status: str
    verification_timestamp: Optional[str] = None
    severity: str = "Medium"
    distance: Optional[float] = None
    time: str = "Recent"
    upvotes: int = 0
    downvotes: int = 0

    @model_validator(mode="before")
    @classmethod
    def coerce_objectids(cls, values: Any) -> Any:
        """Convert ObjectId fields to str so Pydantic doesn't choke."""
        if isinstance(values, dict):
            # Handle _id / id
            for key in ("_id", "id"):
                if key in values and values[key] is not None:
                    values[key] = str(values[key])
            if "_id" in values and "id" not in values:
                values["id"] = values["_id"]
            # Handle user_id
            if "user_id" in values and values["user_id"] is not None:
                values["user_id"] = str(values["user_id"])
        return values


class CommunityStats(BaseModel):
    total: int = 0
    verified: int = 0
    pending: int = 0
    unverified: int = 0
    high_risk_areas: int = 0
    safe_zones: int = 0


class CommunityTrending(BaseModel):
    most_reported_areas: List[str] = []
    most_common_incidents: List[str] = []
    recent_activity: List[str] = []


class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    weight: float


class CommunityHeatmapData(BaseModel):
    verified_only: List[HeatmapPoint] = []
    all_reports: List[HeatmapPoint] = []


class CommunityReportItem(CommunityReportResponse):
    pass



class CommunityIntelligenceResponse(BaseModel):
    reports: List[CommunityReportItem] = []
    statistics: CommunityStats = CommunityStats()
    trending: CommunityTrending = CommunityTrending()
    insights: List[str] = []
    heatmap_data: CommunityHeatmapData = CommunityHeatmapData()


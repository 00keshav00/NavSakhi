from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.base import MongoBaseModel, PyObjectId
from app.models.journey import Location

class CommunityReport(MongoBaseModel):
    user_id: Optional[PyObjectId] = None
    location: Location
    report_type: str # Poor Lighting, Harassment, Road Block, etc.
    description: Optional[str] = None
    verification_status: str = "PENDING" # PENDING, VERIFIED, REJECTED
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime = datetime.utcnow()
    is_active: bool = True

class ReportCollection(BaseModel):
    items: list[CommunityReport]
    metadata: dict = {}

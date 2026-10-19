from pydantic import BaseModel, Field, model_validator
from pydantic import ConfigDict
from typing import Optional, Any
from app.models.journey import Location


class CommunityReportCreate(BaseModel):
    location: Location
    report_type: str
    description: Optional[str] = None


class CommunityReportResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default="")
    user_id: Optional[str] = None
    location: Location
    report_type: str
    description: Optional[str] = None
    verification_status: str
    upvotes: int
    downvotes: int

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

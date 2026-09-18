from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.base import MongoBaseModel, PyObjectId

class ChatMessage(BaseModel):
    sender: str # "user" or "assistant"
    content: str
    timestamp: datetime = datetime.utcnow()
    metadata: dict = {}

class ChatSession(MongoBaseModel):
    user_id: PyObjectId
    journey_id: Optional[PyObjectId] = None
    title: Optional[str] = None
    messages: List[ChatMessage] = []
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    is_active: bool = True

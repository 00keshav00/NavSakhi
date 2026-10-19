from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ChatMessageCreate(BaseModel):
    content: str
    journey_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    sender: str
    content: str
    timestamp: datetime

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProviderHealth(BaseModel):
    """
    Standardized health payload representing a Provider's availability.
    """
    provider_name: str
    status: str = "UNKNOWN"
    latency_ms: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    message: str = ""
    is_healthy: bool = False

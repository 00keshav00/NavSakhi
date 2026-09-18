from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

DataT = TypeVar("DataT")

class StandardResponse(BaseModel, Generic[DataT]):
    success: bool
    message: str = ""
    data: Optional[DataT] = None
    meta: Optional[dict[str, Any]] = None

class ErrorDetails(BaseModel):
    code: Optional[str] = None
    message: str
    details: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetails

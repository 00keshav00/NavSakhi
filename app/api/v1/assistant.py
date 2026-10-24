from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.schemas.responses import StandardResponse
from app.schemas.assistant_schemas import AssistantResponse
from app.api.dependencies import get_optional_user_id, get_journey_repository
from app.repositories.journey_repository import JourneyRepository

router = APIRouter()

class ChatRequest(BaseModel):
    query: str

@router.get("/context", response_model=StandardResponse[AssistantResponse])
async def get_assistant_context(
    user_id: Optional[str] = Depends(get_optional_user_id),
    journey_repo: JourneyRepository = Depends(get_journey_repository)
):
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    effective_user_id = user_id or "guest"
    repo = journey_repo if user_id else None
    context = await coordinator.build_assistant_context(effective_user_id, journey_repo=repo)
    return StandardResponse(success=True, data=context)

@router.post("/chat", response_model=StandardResponse[AssistantResponse])
async def send_assistant_message(
    request: ChatRequest,
    user_id: Optional[str] = Depends(get_optional_user_id),
    journey_repo: JourneyRepository = Depends(get_journey_repository)
):
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    effective_user_id = user_id or "guest"
    repo = journey_repo if user_id else None
    response = await coordinator.process_assistant_chat(effective_user_id, request.query, journey_repo=repo)
    return StandardResponse(success=True, data=response)


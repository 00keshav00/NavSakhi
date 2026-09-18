from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.schemas.responses import StandardResponse
from app.schemas.assistant_schemas import AssistantResponse
from app.api.dependencies import get_current_user_id

router = APIRouter()

class ChatRequest(BaseModel):
    query: str

@router.get("/context", response_model=StandardResponse[AssistantResponse])
async def get_assistant_context(user_id: str = Depends(get_current_user_id)):
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    context = await coordinator.build_assistant_context(user_id)
    return StandardResponse(success=True, data=context)

@router.post("/chat", response_model=StandardResponse[AssistantResponse])
async def send_assistant_message(request: ChatRequest, user_id: str = Depends(get_current_user_id)):
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    response = await coordinator.process_assistant_chat(user_id, request.query)
    return StandardResponse(success=True, data=response)

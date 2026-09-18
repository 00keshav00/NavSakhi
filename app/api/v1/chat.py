from fastapi import APIRouter, Depends
from app.schemas.responses import StandardResponse
from app.schemas.chat_schemas import ChatMessageCreate, ChatMessageResponse
from app.services.chat_service import ChatService
from app.api.dependencies import get_chat_service, get_current_user_id

router = APIRouter()

@router.post("/{session_id}/messages", response_model=StandardResponse[ChatMessageResponse])
async def send_message(
    session_id: str,
    data: ChatMessageCreate,
    user_id: str = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service)
):
    msg = await chat_service.process_message(session_id, data)
    return StandardResponse(success=True, data=ChatMessageResponse(**msg.model_dump(by_alias=True)))

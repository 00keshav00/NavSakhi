from app.repositories.chat_repository import ChatRepository
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat_schemas import ChatMessageCreate
from app.api.exceptions import ResourceNotFoundException
import uuid

class ChatService:
    def __init__(self, chat_repo: ChatRepository):
        self.chat_repo = chat_repo

    async def get_session(self, session_id: str) -> ChatSession:
        session = await self.chat_repo.get_by_id(session_id)
        if not session:
            raise ResourceNotFoundException("Chat Session")
        return session

    async def process_message(self, session_id: str, data: ChatMessageCreate) -> ChatMessage:
        session = await self.get_session(session_id)
        
        user_msg = ChatMessage(sender="user", content=data.content)
        await self.chat_repo.add_message(session_id, user_msg)
        
        # Pass to Coordinator Agent
        # Pass to Coordinator Agent - temporarily mocked for Phase 1
        # context = {"session_id": session_id}
        # payload = {"message": data.content}
        response = {"data": {"reply": "This is a mocked AI response while we test backend connectivity."}}
        
        assistant_msg = ChatMessage(sender="assistant", content=response.get("data", {}).get("reply", ""))
        await self.chat_repo.add_message(session_id, assistant_msg)
        
        return assistant_msg

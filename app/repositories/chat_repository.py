from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.base import BaseRepository
from app.models.chat import ChatSession, ChatMessage
from typing import Optional, List
from bson import ObjectId

class ChatRepository(BaseRepository[ChatSession]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "chat_sessions", ChatSession)

    async def get_user_sessions(self, user_id: str, limit: int = 10) -> List[ChatSession]:
        if not ObjectId.is_valid(user_id):
            return []
        cursor = self.collection.find({
            "user_id": ObjectId(user_id),
            "is_active": True
        }).sort("updated_at", -1).limit(limit)
        
        sessions = []
        async for doc in cursor:
            sessions.append(self.model(**doc))
        return sessions

    async def add_message(self, session_id: str, message: ChatMessage) -> Optional[ChatSession]:
        if not ObjectId.is_valid(session_id):
            return None
        msg_dict = message.model_dump()
        result = await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$push": {"messages": msg_dict},
                "$set": {"updated_at": message.timestamp}
            }
        )
        if result.modified_count > 0:
            return await self.get_by_id(session_id)
        return None

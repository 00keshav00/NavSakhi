from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.base import BaseRepository
from app.models.journey import Journey, JourneyStateEnum
from typing import Optional, List, Any
from bson import ObjectId

class JourneyRepository(BaseRepository[Journey]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "journeys", Journey)

    async def get_active_journey(self, user_id: str) -> Optional[Journey]:
        for doc in self._store.values():
            uid = str(doc.get("user_id"))
            state = doc.get("state", {}).get("current_state")
            if uid == str(user_id) and state in [
                JourneyStateEnum.ACTIVE.value,
                JourneyStateEnum.MONITORING.value,
                JourneyStateEnum.PAUSED.value,
            ]:
                return self.model(**doc)
        return None

    async def get_journey_history(self, user_id: str, limit: int = 10) -> List[Journey]:
        journeys = []
        for doc in self._store.values():
            if str(doc.get("user_id")) == str(user_id):
                journeys.append(self.model(**doc))
        return journeys[:limit]

    async def add_journey_log(self, journey_id: str, log: Any) -> Optional[Journey]:
        doc = self._store.get(str(journey_id))
        if doc:
            if "logs" not in doc:
                doc["logs"] = []
            doc["logs"].append(log)
            return self.model(**doc)
        return None

    async def update_status(self, journey_id: str, status: str) -> Optional[Journey]:
        return await self.update(journey_id, {"$set": {"state.current_state": status}})

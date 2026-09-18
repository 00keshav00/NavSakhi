from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import TypeVar, Generic, Type, Optional, List
from pydantic import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseRepository(Generic[ModelType]):
    _global_store: dict[str, dict] = {} # Class-level in-memory store

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str, model: Type[ModelType]):
        self.collection = db[collection_name]
        self.model = model
        self.collection_name = collection_name
        
        if self.collection_name not in BaseRepository._global_store:
            BaseRepository._global_store[self.collection_name] = {}

    @property
    def _store(self):
        return BaseRepository._global_store[self.collection_name]

    async def get_by_id(self, id: str) -> Optional[ModelType]:
        doc = self._store.get(str(id))
        if doc:
            return self.model(**doc)
        return None

    async def create(self, obj_in: ModelType) -> ModelType:
        doc = obj_in.model_dump(by_alias=True, exclude_none=True)
        if "_id" not in doc or not doc["_id"]:
            doc["_id"] = ObjectId()
        elif isinstance(doc["_id"], str):
             doc["_id"] = ObjectId(doc["_id"])
             
        # Save to in-memory store
        self._store[str(doc["_id"])] = doc.copy()
        return self.model(**doc)

    async def update(self, id: str, update_data: dict) -> Optional[ModelType]:
        doc = self._store.get(str(id))
        if not doc:
            return None
            
        # Very simple mock $set implementation
        if "$set" in update_data:
            # Note: in a real implementation we'd do deep merge for nested fields
            # but for this mock, a simple update works enough.
            for k, v in update_data["$set"].items():
                if "." in k:
                    parts = k.split(".")
                    target = doc
                    for part in parts[:-1]:
                        if part not in target:
                            target[part] = {}
                        target = target[part]
                    target[parts[-1]] = v
                else:
                    doc[k] = v
        else:
            # Full replace
            doc.update(update_data)
            
        self._store[str(id)] = doc
        return self.model(**doc)

    async def delete(self, id: str) -> bool:
        if str(id) in self._store:
            del self._store[str(id)]
            return True
        return False

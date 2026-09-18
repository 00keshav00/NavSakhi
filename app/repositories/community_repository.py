from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.base import BaseRepository
from app.models.community import CommunityReport
from typing import List
from bson import ObjectId

class CommunityRepository(BaseRepository[CommunityReport]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "community_reports", CommunityReport)

    async def get_active_reports(self, limit: int = 50) -> List[CommunityReport]:
        cursor = self.collection.find({"is_active": True}).sort("created_at", -1).limit(limit)
        reports = []
        async for doc in cursor:
            reports.append(self.model(**doc))
        return reports

    async def get_nearby_reports(self, coordinates: List[float], max_distance: float = 5000) -> List[CommunityReport]:
        """
        Query nearby community reports using $geoNear aggregation pipeline.
        
        We use $geoNear (aggregation) instead of $near (query operator) because:
        - $geoNear works even when the collection is empty (returns [] gracefully)
        - $near can raise OperationFailure if index is not yet ready
        - $geoNear allows sorting by distance and adding distanceField
        
        Requires a 2dsphere index on the `location` field (created in init_db.py).
        """
        pipeline = [
            {
                "$geoNear": {
                    "near": {
                        "type": "Point",
                        "coordinates": coordinates
                    },
                    "distanceField": "dist_calculated",
                    "maxDistance": max_distance,
                    "query": {"is_active": True},
                    "spherical": True
                }
            },
            {"$sort": {"created_at": -1}},
            {"$limit": 100},
            # Remove the computed distance field before deserializing
            {"$project": {"dist_calculated": 0}}
        ]
        reports = []
        async for doc in self.collection.aggregate(pipeline):
            reports.append(self.model(**doc))
        return reports

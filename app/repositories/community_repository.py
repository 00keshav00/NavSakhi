from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.base import BaseRepository
from app.models.community import CommunityReport
from typing import List, Dict, Any
from bson import ObjectId

class CommunityRepository(BaseRepository[CommunityReport]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "community_reports", CommunityReport)

    async def get_user_reports(self, user_id: str) -> List[CommunityReport]:
        """Fetch all community reports submitted strictly by this user."""
        reports = []
        seen_ids = set()

        for doc in self._store.values():
            if str(doc.get("user_id")) == str(user_id):
                rid = str(doc.get("_id") or doc.get("id"))
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    reports.append(self.model(**doc))

        if self.collection is not None:
            try:
                query = {
                    "$or": [
                        {"user_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else None},
                        {"user_id": str(user_id)}
                    ]
                }
                cursor = self.collection.find(query).sort("created_at", -1)
                async for doc in cursor:
                    rid = str(doc.get("_id"))
                    if rid not in seen_ids:
                        seen_ids.add(rid)
                        reports.append(self.model(**doc))
            except Exception:
                pass
        return reports

    async def calculate_user_metrics(self, user_id: str) -> Dict[str, Any]:
        """Calculates authentic user-scoped community metrics."""
        reports = await self.get_user_reports(user_id)
        submitted = len(reports)
        verified = sum(
            1 for r in reports
            if getattr(r, "verification_status", None) == "VERIFIED" or (isinstance(r, dict) and r.get("verification_status") == "VERIFIED")
        )
        upvotes = sum(
            int(getattr(r, "upvotes", 0) or (r.get("upvotes", 0) if isinstance(r, dict) else 0))
            for r in reports
        )
        return {
            "community_reports_submitted": submitted,
            "verified_reports": verified,
            "helpful_votes": upvotes,
            "has_records": submitted > 0
        }

    async def get_active_reports(self, limit: int = 50) -> List[CommunityReport]:
        reports = []
        if self.collection is not None:
            try:
                cursor = self.collection.find({"is_active": True}).sort("created_at", -1).limit(limit)
                async for doc in cursor:
                    reports.append(self.model(**doc))
            except Exception:
                pass
        if not reports:
            for doc in self._store.values():
                if doc.get("is_active", True):
                    reports.append(self.model(**doc))
        return reports[:limit]

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

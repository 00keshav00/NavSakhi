from typing import Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.intelligence.journey.providers import ReportsProvider
from app.models.journey import Location
from app.models.community import CommunityReport, ReportCollection
from app.providers.shared.exceptions import ProviderError, ProviderResponseMappingError
from app.providers.shared.cache import ProviderCache
from app.providers.shared.retry import with_retry
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class MongoReportsProvider(ReportsProvider):
    """
    Concrete implementation of ReportsProvider using MongoDB.
    Acts purely as an ACL wrapping the DB into the domain contract.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.community_reports

    @ProviderCache.cached(ttl_seconds=settings.reports_cache_ttl)
    @with_retry(max_retries=2, base_delay_ms=100)
    async def get_nearby_reports(self, location: Location, radius_m: int = 1000) -> ReportCollection:
        try:
            # Assumes 2dsphere index on location.coordinates
            query = {
                "location.coordinates": {
                    "$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": [location.coordinates[0], location.coordinates[1]]
                        },
                        "$maxDistance": radius_m
                    }
                },
                "is_active": True
            }
            cursor = self.collection.find(query).limit(100)
            reports = []
            async for doc in cursor:
                doc["id"] = str(doc["_id"])
                reports.append(CommunityReport(**doc))
                
            return ReportCollection(
                items=reports,
                metadata={"source": "mongodb", "count": len(reports), "radius_m": radius_m}
            )
        except Exception as e:
            logger.error(f"MongoReportsProvider get_nearby Error: {str(e)}")
            raise ProviderError(f"Database error: {str(e)}")

    @ProviderCache.cached(ttl_seconds=settings.reports_cache_ttl)
    @with_retry(max_retries=2, base_delay_ms=100)
    async def get_recent_reports(self, limit: int = 50) -> ReportCollection:
        try:
            cursor = self.collection.find({"is_active": True}).sort("created_at", -1).limit(limit)
            reports = []
            async for doc in cursor:
                doc["id"] = str(doc["_id"])
                reports.append(CommunityReport(**doc))
                
            return ReportCollection(
                items=reports,
                metadata={"source": "mongodb", "count": len(reports)}
            )
        except Exception as e:
            logger.error(f"MongoReportsProvider get_recent Error: {str(e)}")
            raise ProviderError(f"Database error: {str(e)}")

    @ProviderCache.cached(ttl_seconds=settings.reports_cache_ttl)
    @with_retry(max_retries=2, base_delay_ms=100)
    async def get_report_count(self, location: Location, radius_m: int = 1000) -> int:
        try:
            query = {
                "location.coordinates": {
                    "$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": [location.coordinates[0], location.coordinates[1]]
                        },
                        "$maxDistance": radius_m
                    }
                },
                "is_active": True
            }
            return await self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"MongoReportsProvider get_count Error: {str(e)}")
            raise ProviderError(f"Database error: {str(e)}")

    @with_retry(max_retries=2, base_delay_ms=100)
    async def get_report_by_id(self, report_id: str) -> CommunityReport:
        try:
            doc = await self.collection.find_one({"_id": ObjectId(report_id)})
            if not doc:
                raise ProviderResponseMappingError(f"Report not found: {report_id}")
                
            doc["id"] = str(doc["_id"])
            return CommunityReport(**doc)
        except Exception as e:
            logger.error(f"MongoReportsProvider get_by_id Error: {str(e)}")
            raise ProviderError(f"Database error: {str(e)}")

    @with_retry(max_retries=2, base_delay_ms=100)
    async def create_report(self, report: CommunityReport) -> CommunityReport:
        try:
            doc = report.model_dump(by_alias=True, exclude_unset=True)
            if "id" in doc:
                del doc["id"]
                
            result = await self.collection.insert_one(doc)
            doc["_id"] = result.inserted_id
            doc["id"] = str(doc["_id"])
            return CommunityReport(**doc)
        except Exception as e:
            logger.error(f"MongoReportsProvider create Error: {str(e)}")
            raise ProviderError(f"Database error: {str(e)}")

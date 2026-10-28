from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.base import BaseRepository
from app.models.journey import Journey, JourneyStateEnum
from typing import Optional, List, Any, Dict
from bson import ObjectId


def parse_distance_km(val: Any) -> Optional[float]:
    """Safely parse distance value in meters or km to a float in kilometers."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        f = float(val)
        if f < 0:
            return None
        if f > 100.0:
            return round(f / 1000.0, 2)
        return round(f, 2)
    if isinstance(val, str):
        v = val.strip().lower()
        if "km" in v:
            clean = v.replace("km", "").strip()
            try:
                f = float(clean)
                return round(f, 2) if f >= 0 else None
            except ValueError:
                return None
        if "m" in v:
            clean = v.replace("m", "").strip()
            try:
                f = float(clean)
                return round(f / 1000.0, 2) if f >= 0 else None
            except ValueError:
                return None
        try:
            f = float(v)
            if f < 0:
                return None
            if f > 100.0:
                return round(f / 1000.0, 2)
            return round(f, 2)
        except ValueError:
            return None
    return None


def parse_safety_score(val: Any) -> Optional[float]:
    """Safely parse safety score into [0.0, 100.0] range."""
    if val is None:
        return None
    try:
        f = float(val)
        if 0.0 <= f <= 100.0:
            return round(f, 1)
    except (ValueError, TypeError):
        pass
    return None


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
        if self.collection is not None:
            try:
                query = {
                    "$or": [
                        {"user_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else None},
                        {"user_id": str(user_id)}
                    ],
                    "state.current_state": {
                        "$in": [
                            JourneyStateEnum.ACTIVE.value,
                            JourneyStateEnum.MONITORING.value,
                            JourneyStateEnum.PAUSED.value
                        ]
                    }
                }
                doc = await self.collection.find_one(query)
                if doc:
                    return self.model(**doc)
            except Exception:
                pass
        return None

    async def get_journey_history(self, user_id: str, limit: int = 50) -> List[Journey]:
        """Fetch journey history strictly scoped to user_id from store and database."""
        journeys = []
        seen_ids = set()

        for doc in self._store.values():
            if str(doc.get("user_id")) == str(user_id):
                jid = str(doc.get("_id") or doc.get("id"))
                if jid not in seen_ids:
                    seen_ids.add(jid)
                    journeys.append(self.model(**doc))

        if self.collection is not None:
            try:
                query = {
                    "$or": [
                        {"user_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else None},
                        {"user_id": str(user_id)}
                    ]
                }
                cursor = self.collection.find(query).sort("created_timestamp", -1).limit(limit)
                async for doc in cursor:
                    jid = str(doc.get("_id"))
                    if jid not in seen_ids:
                        seen_ids.add(jid)
                        journeys.append(self.model(**doc))
            except Exception:
                pass

        # Sort descending by created_timestamp
        journeys.sort(
            key=lambda j: getattr(j, "created_timestamp", None) or 0,
            reverse=True
        )
        return journeys[:limit]

    async def calculate_user_metrics(self, user_id: str) -> Dict[str, Any]:
        """
        Calculates truthful, owner-scoped journey metrics for completed journeys:
        - completed/safe journey count
        - total distance travelled in km
        - average safety score across completed journeys
        Excludes cancelled, incomplete, or synthetic non-completed journeys.
        """
        all_journeys = await self.get_journey_history(user_id, limit=200)
        completed_journeys = []

        for j in all_journeys:
            st = getattr(getattr(j, "state", None), "current_state", None)
            if not st and isinstance(j, dict):
                st = j.get("state", {}).get("current_state")
            st_val = getattr(st, "value", st)
            if st_val in [JourneyStateEnum.COMPLETED.value, "COMPLETED"]:
                completed_journeys.append(j)

        safe_journeys = len(completed_journeys)
        distances_km: List[float] = []
        safety_scores: List[float] = []

        for j in completed_journeys:
            # 1. Extract distance
            dist_km = None
            plan = getattr(j, "plan", None)
            sel_route_id = getattr(j, "selected_route_id", None)
            planned_routes = getattr(j, "planned_routes", None) or []

            if plan and getattr(plan, "selected_route", None):
                dist_km = parse_distance_km(getattr(plan.selected_route, "distance", None))

            if dist_km is None and planned_routes:
                target_r = None
                if sel_route_id:
                    for r in planned_routes:
                        rid = getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else None)
                        if rid == sel_route_id:
                            target_r = r
                            break
                if not target_r and planned_routes:
                    target_r = planned_routes[0]
                if target_r:
                    d_val = getattr(target_r, "distance_km", None) or (target_r.get("distance_km") if isinstance(target_r, dict) else None)
                    if d_val is None:
                        d_val = getattr(target_r, "distance", None) or (target_r.get("distance") if isinstance(target_r, dict) else None)
                    dist_km = parse_distance_km(d_val)

            if dist_km is None and getattr(j, "progress", None):
                dist_km = parse_distance_km(getattr(j.progress, "distance_covered", None))

            if dist_km is not None and dist_km >= 0:
                distances_km.append(dist_km)

            # 2. Extract safety score
            score = None
            if plan and getattr(plan, "selected_route", None):
                score = parse_safety_score(getattr(plan.selected_route, "safety_score", None))

            if score is None and planned_routes:
                target_r = None
                if sel_route_id:
                    for r in planned_routes:
                        rid = getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else None)
                        if rid == sel_route_id:
                            target_r = r
                            break
                if not target_r and planned_routes:
                    target_r = planned_routes[0]
                if target_r:
                    score = parse_safety_score(
                        getattr(target_r, "safety_score", None) or (target_r.get("safety_score") if isinstance(target_r, dict) else None)
                    )

            if score is None and plan and getattr(plan, "journey_score", None):
                score = parse_safety_score(getattr(plan.journey_score, "safety_score", None))

            if score is not None:
                safety_scores.append(score)

        total_distance = round(sum(distances_km), 2)
        avg_score = round(sum(safety_scores) / len(safety_scores), 1) if safety_scores else 0.0

        return {
            "completed_journeys": safe_journeys,
            "safe_journeys": safe_journeys,
            "total_distance_km": total_distance,
            "avg_safety_score": avg_score,
            "has_records": safe_journeys > 0,
            "completed_journey_records": completed_journeys
        }

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

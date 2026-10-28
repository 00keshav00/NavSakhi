from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata
from app.db.connection import get_database

class ProfileTool(BaseTool):
    @property
    def name(self) -> str:
        return "ProfileTool"

    @property
    def description(self) -> str:
        return "Retrieves user profile and settings from MongoDB."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="UserProfile",
            required_inputs=["user_id"],
            output_schema={"type": "dict"},
            ranking_score=10
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        user_id = params.get("user_id")
        user = params.get("user")
        
        if not user and user_id:
            db = get_database()
            if db is not None:
                try:
                    from app.repositories.user_repository import UserRepository
                    repo = UserRepository(db)
                    user = await repo.get_by_id(user_id)
                except Exception:
                    user = None

        if user:
            created_at = getattr(user, "created_at", None)
            join_date = created_at.strftime("%B %Y") if created_at else "Not available"
            ps = getattr(user, "profile_settings", {}) or {}
            
            raw_contacts = []
            for idx, c in enumerate(getattr(user, "emergency_contacts", [])):
                raw_contacts.append({
                    "id": str(getattr(c, "id", f"c_{idx}")),
                    "name": getattr(c, "name", ""),
                    "relationship": getattr(c, "relationship", "Family") or "Family",
                    "phone": getattr(c, "phone_number", "") or getattr(c, "phone", ""),
                    "is_primary": bool(getattr(c, "is_primary", False))
                })

            journey_repo = params.get("journey_repo")
            community_repo = params.get("community_repo")
            db = get_database()
            if not journey_repo:
                from app.repositories.journey_repository import JourneyRepository
                journey_repo = JourneyRepository(db)
            if not community_repo:
                from app.repositories.community_repository import CommunityRepository
                community_repo = CommunityRepository(db)

            j_metrics = {}
            c_metrics = {}
            if user_id:
                try:
                    j_metrics = await journey_repo.calculate_user_metrics(str(user_id))
                except Exception:
                    j_metrics = {}
                try:
                    c_metrics = await community_repo.calculate_user_metrics(str(user_id))
                except Exception:
                    c_metrics = {}

            return {
                "profile": {
                    "id": str(getattr(user, "id", user_id or "")),
                    "name": ps.get("full_name") or getattr(user, "username", "") or "NavSakhi User",
                    "email": getattr(user, "email", ""),
                    "phone": ps.get("phone_number") or ps.get("phone") or "Not provided",
                    "current_city": ps.get("current_city") or "Not provided",
                    "join_date": join_date,
                    "devices": [],
                    "emergency_contacts": raw_contacts
                },
                "settings": user.preferences.model_dump() if getattr(user, "preferences", None) else self._fallback_settings(),
                "journey_metrics": j_metrics,
                "community_metrics": c_metrics
            }
        else:
            return self._fallback_profile()

    def _fallback_profile(self):
        return {
            "profile": {
                "id": "",
                "name": "NavSakhi User",
                "email": "",
                "phone": "Not provided",
                "current_city": "Not provided",
                "join_date": "Not available",
                "devices": [],
                "emergency_contacts": []
            },
            "settings": self._fallback_settings()
        }

    def _fallback_settings(self):
        return {
            "notifications": {"push_enabled": True, "sms_enabled": False, "email_enabled": True, "marketing_enabled": False, "alert_types": ["sos"]},
            "privacy": {"share_location": True, "share_analytics": False, "profile_visibility": "network", "retention_period": 30},
            "journey": {"default_mode": "walking", "auto_reroute": True, "share_eta": True, "avoid_areas": [], "preferred_safe_zones": []},
            "emergency": {"auto_sos_timer": 15, "stealth_mode": True, "siren_enabled": False, "record_audio": True},
            "ai_preferences": {"voice_enabled": False, "proactive_alerts": True, "personality": "concise"}
        }


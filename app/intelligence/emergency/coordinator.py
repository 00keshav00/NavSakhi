import logging
import uuid
import asyncio
from typing import Dict, Any

from app.providers.communications.sms import SMSProvider
from app.api.websockets.emergency_ws import manager as ws_manager

logger = logging.getLogger(__name__)

class EmergencyIntelligenceCoordinator:
    """
    The Agent coordinating emergency SOS triggers.
    It manages the execution of various tools (SMS dispatch, WebSocket connection).
    """
    def __init__(self, sms_provider: SMSProvider = None):
        self.sms_provider = sms_provider or SMSProvider()
        self.ws_manager = ws_manager

    async def handle_sos_trigger(self, user_id: str, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Orchestrates the emergency response sequence.
        """
        logger.info(f"[Emergency Agent] Handling SOS trigger for user {user_id}")
        
        # 1. Generate a unique emergency session ID
        session_id = str(uuid.uuid4())
        
        # 2. Extract context
        location = context.get("current_location", "Unknown Location")
        
        # 3. Formulate the emergency message
        # In a real agent, an LLM might craft this message dynamically based on user profile/context.
        message = f"URGENT: User {user_id} has triggered an SOS at {location}. Live tracking link: https://safeshe.app/track/{session_id}"
        
        # 4. Dispatch SMS asynchronously only if user has real configured contacts
        user_repo = context.get("user_repo")
        real_contacts = []
        user = None
        if user_repo:
            try:
                user = await user_repo.get_by_id(user_id)
            except Exception:
                user = None
        if not user:
            try:
                from app.db.connection import get_database
                db = get_database()
            except Exception:
                db = None
            if db is not None:
                try:
                    from app.repositories.user_repository import UserRepository
                    repo = UserRepository(db)
                    user = await repo.get_by_id(user_id)
                except Exception:
                    pass
            if not user:
                from app.repositories.base import BaseRepository
                user_dict = BaseRepository._global_store.get("users", {}).get(str(user_id))
                if user_dict:
                    from app.models.user import User
                    user = User(**user_dict)

        if user and getattr(user, "emergency_contacts", None):
            for c in user.emergency_contacts:
                phone = getattr(c, "phone_number", None) or getattr(c, "phone", None)
                if phone:
                    real_contacts.append(str(phone))

        if real_contacts:
            asyncio.create_task(self.sms_provider.send_emergency_sms(real_contacts, message))
        else:
            logger.info(f"[Emergency Agent] No emergency contacts configured with phone numbers for user {user_id}. No automated SMS dispatched.")

        # 5. The WebSocket session is already available for connection at ws://.../emergency/{session_id}
        # The agent returns the session_id so the frontend can connect to it.
        logger.info(f"[Emergency Agent] Escalation complete. WebSocket channel ready: {session_id}")
        
        return {
            "session_id": session_id,
            "status": "escalated",
            "message": "Emergency dispatch sequence initiated."
        }

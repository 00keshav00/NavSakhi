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
        
        # 4. Dispatch SMS asynchronously using the tool
        # In reality, the contacts list would be fetched from the User Profile.
        contacts = ["+1234567890", "+0987654321"]
        asyncio.create_task(self.sms_provider.send_emergency_sms(contacts, message))
        
        # 5. The WebSocket session is already available for connection at ws://.../emergency/{session_id}
        # The agent returns the session_id so the frontend can connect to it.
        logger.info(f"[Emergency Agent] Escalation complete. WebSocket channel ready: {session_id}")
        
        return {
            "session_id": session_id,
            "status": "escalated",
            "message": "Emergency dispatch sequence initiated."
        }

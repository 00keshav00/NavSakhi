import logging
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class EmergencySession:
    session_id: str
    user_id: str
    journey_id: Optional[str]
    created_at: datetime
    is_active: bool = True
    authorized_users: Set[str] = field(default_factory=set)

class EmergencySessionRegistry:
    """
    In-memory registry for tracking emergency SOS sessions, their creators,
    and authorized recipients / responders for secure real-time WebSocket broadcasting.
    """
    def __init__(self):
        self._sessions: Dict[str, EmergencySession] = {}

    def register_session(
        self,
        session_id: str,
        user_id: str,
        journey_id: Optional[str] = None,
        authorized_recipients: Optional[Set[str]] = None
    ) -> EmergencySession:
        """Register a new emergency session with owner and optional authorized recipients."""
        authorized = {str(user_id)}
        if authorized_recipients:
            authorized.update(str(u) for u in authorized_recipients)

        session = EmergencySession(
            session_id=session_id,
            user_id=str(user_id),
            journey_id=journey_id,
            created_at=datetime.utcnow(),
            is_active=True,
            authorized_users=authorized
        )
        self._sessions[session_id] = session
        logger.info(f"Registered emergency session {session_id} for user {user_id}")
        return session

    def get_session(self, session_id: str) -> Optional[EmergencySession]:
        return self._sessions.get(session_id)

    def is_authorized(self, session_id: str, user_id: str) -> bool:
        """Verify whether user_id is authorized to view or listen to the emergency session."""
        session = self.get_session(session_id)
        if not session or not session.is_active:
            return False
        return str(user_id) in session.authorized_users

    def add_authorized_user(self, session_id: str, user_id: str) -> bool:
        session = self.get_session(session_id)
        if session and session.is_active:
            session.authorized_users.add(str(user_id))
            return True
        return False

    def close_session(self, session_id: str) -> None:
        session = self.get_session(session_id)
        if session:
            session.is_active = False
            logger.info(f"Closed emergency session {session_id}")

    def clear(self) -> None:
        """Clear all sessions (for unit test isolation)."""
        self._sessions.clear()

emergency_session_registry = EmergencySessionRegistry()

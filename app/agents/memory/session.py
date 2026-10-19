from typing import Any, Dict
from app.agents.memory.models import Memory

class SessionMemory(Memory):
    """
    Shared state for active user sessions.
    In production, this would be backed by Redis.
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def store(self, key: str, value: Any, session_id: str = None, **kwargs) -> None:
        if not session_id:
            raise ValueError("session_id is required for SessionMemory")
        if session_id not in self._cache:
            self._cache[session_id] = {}
        self._cache[session_id][key] = value

    def retrieve(self, key: str, session_id: str = None, **kwargs) -> Any:
        if not session_id:
            raise ValueError("session_id is required for SessionMemory")
        return self._cache.get(session_id, {}).get(key)
        
    def retrieve_all(self, session_id: str = None, **kwargs) -> Dict[str, Any]:
        if not session_id:
            raise ValueError("session_id is required for SessionMemory")
        return dict(self._cache.get(session_id, {}))

    def clear(self, session_id: str = None, **kwargs) -> None:
        if session_id and session_id in self._cache:
            del self._cache[session_id]

from typing import Any, Dict
from app.agents.memory.models import Memory

class PreferenceMemory(Memory):
    """
    Stores long-term user preferences that influence planning.
    Persistent memory.
    """
    def __init__(self):
        # In a real implementation, this would connect to the UserPreferences model in MongoDB.
        self._preferences: Dict[str, Dict[str, Any]] = {}

    def store(self, key: str, value: Any, user_id: str = None, **kwargs) -> None:
        if not user_id:
            raise ValueError("user_id is required for PreferenceMemory")
        if user_id not in self._preferences:
            self._preferences[user_id] = {}
        self._preferences[user_id][key] = value

    def retrieve(self, key: str, user_id: str = None, **kwargs) -> Any:
        if not user_id:
            raise ValueError("user_id is required for PreferenceMemory")
        return self._preferences.get(user_id, {}).get(key)
        
    def retrieve_all(self, user_id: str = None, **kwargs) -> Dict[str, Any]:
        if not user_id:
            raise ValueError("user_id is required for PreferenceMemory")
        return dict(self._preferences.get(user_id, {}))

    def clear(self, user_id: str = None, **kwargs) -> None:
        # User preferences shouldn't generally be fully cleared unless the user deletes their account.
        if user_id and user_id in self._preferences:
            del self._preferences[user_id]

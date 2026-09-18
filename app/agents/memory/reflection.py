from typing import Any, Dict
from app.agents.memory.models import Memory

class ReflectionMemory(Memory):
    """
    Stores knowledge generated during previous executions (e.g., tool failures).
    Persistent memory for adaptive runtime learning.
    """
    def __init__(self):
        # In a real implementation, this would persist to the DB.
        self._reflections: Dict[str, Dict[str, Any]] = {}

    def store(self, key: str, value: Any, agent_identity: str = None, **kwargs) -> None:
        if not agent_identity:
            raise ValueError("agent_identity is required for ReflectionMemory")
        if agent_identity not in self._reflections:
            self._reflections[agent_identity] = {}
        self._reflections[agent_identity][key] = value

    def retrieve(self, key: str, agent_identity: str = None, **kwargs) -> Any:
        if not agent_identity:
            raise ValueError("agent_identity is required for ReflectionMemory")
        return self._reflections.get(agent_identity, {}).get(key)
        
    def retrieve_all(self, agent_identity: str = None, **kwargs) -> Dict[str, Any]:
        if not agent_identity:
            raise ValueError("agent_identity is required for ReflectionMemory")
        return dict(self._reflections.get(agent_identity, {}))

    def clear(self, agent_identity: str = None, **kwargs) -> None:
        if agent_identity and agent_identity in self._reflections:
            del self._reflections[agent_identity]

from typing import Any, Dict
from app.agents.memory.models import Memory

class WorkingMemory(Memory):
    """
    Temporary execution data used only during a single agent invocation.
    Destroyed after execution.
    """
    def __init__(self):
        self._data: Dict[str, Any] = {}

    def store(self, key: str, value: Any, **kwargs) -> None:
        self._data[key] = value

    def retrieve(self, key: str, **kwargs) -> Any:
        return self._data.get(key)
        
    def retrieve_all(self, **kwargs) -> Dict[str, Any]:
        return dict(self._data)

    def clear(self, **kwargs) -> None:
        self._data.clear()

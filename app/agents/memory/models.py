from abc import ABC, abstractmethod
from typing import Any, Dict

class Memory(ABC):
    """
    Abstract interface for all Agent Runtime memory systems.
    """
    @abstractmethod
    def store(self, key: str, value: Any, **kwargs) -> None:
        """Stores a key-value pair in memory."""
        pass

    @abstractmethod
    def retrieve(self, key: str, **kwargs) -> Any:
        """Retrieves a value from memory."""
        pass
        
    @abstractmethod
    def retrieve_all(self, **kwargs) -> Dict[str, Any]:
        """Retrieves all context from this memory layer."""
        pass

    @abstractmethod
    def clear(self, **kwargs) -> None:
        """Clears the memory layer, according to its lifespan policy."""
        pass

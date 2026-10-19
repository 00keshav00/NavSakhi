from typing import Any, Dict

class BaseSpecializedAgent:
    """
    Base class for all Specialized Agents.
    Each specialized agent has a single responsibility and uses Tools to communicate with Providers.
    """
    def __init__(self):
        self.name = self.__class__.__name__

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        raise NotImplementedError("Each specialized agent must implement execute()")

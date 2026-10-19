from typing import Any, Dict
from app.agents.memory.retrieval import MemoryRetrievalEngine
from app.agents.context import ExecutionContext

class MemoryPrioritization:
    """
    Resolves conflicts when multiple memories contain related information.
    Hierarchy: Working > Journey > Session > Conversation > Preference > Reflection
    """
    def __init__(self, retrieval_engine: MemoryRetrievalEngine):
        self.retrieval = retrieval_engine
        
        # Priority order (highest to lowest)
        self.hierarchy = [
            "working",
            "journey",
            "session",
            "conversation",
            "preference",
            "reflection"
        ]

    def prioritize_key(self, key: str, context: ExecutionContext) -> Any:
        """
        Searches memory layers in priority order and returns the first found value.
        """
        for layer in self.hierarchy:
            layer_data = self.retrieval.retrieve_context_layer(layer, context)
            if key in layer_data:
                return layer_data[key]
        return None

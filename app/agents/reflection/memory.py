from typing import Dict, Any
from app.agents.reflection.models import ReflectionInsight
from app.agents.memory.manager import MemoryManager

class ReflectionMemoryGenerator:
    """
    Transforms insights into memories compatible with ReflectionMemory.
    """
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        
    def store_insight(self, agent_identity: str, insight: ReflectionInsight) -> None:
        """
        Stores the insight in the memory layer.
        """
        key = f"insight_{insight.insight_type}"
        self.memory_manager.reflection.store(
            key, 
            insight.model_dump(), 
            agent_identity=agent_identity
        )

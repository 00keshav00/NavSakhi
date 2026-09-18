from typing import Any, Dict
from app.agents.memory.manager import MemoryManager
from app.agents.memory.retrieval import MemoryRetrievalEngine
from app.agents.context import ExecutionContext

class ContextAssembly:
    """
    Assembles reasoning-ready context from all memory layers before execution.
    """
    def __init__(self, manager: MemoryManager):
        self.retrieval_engine = MemoryRetrievalEngine(manager)

    def assemble(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Combines current execution context with retrieved memory layers.
        """
        assembled_context = {
            "execution": {
                "goal": context.goal,
                "agent_identity": context.agent_identity,
                "current_task": context.current_task,
                "constraints": context.constraints,
            },
            "working_memory": self.retrieval_engine.retrieve_context_layer("working", context),
            "session_memory": self.retrieval_engine.retrieve_context_layer("session", context),
            "conversation_memory": self.retrieval_engine.retrieve_context_layer("conversation", context),
            "journey_memory": self.retrieval_engine.retrieve_context_layer("journey", context),
            "preference_memory": self.retrieval_engine.retrieve_context_layer("preference", context),
            "reflection_memory": self.retrieval_engine.retrieve_context_layer("reflection", context),
        }
        return assembled_context

from typing import Any, Dict
from app.agents.memory.manager import MemoryManager
from app.agents.context import ExecutionContext

class MemoryRetrievalEngine:
    """
    Enforces deterministic retrieval of context based on the current execution.
    """
    def __init__(self, manager: MemoryManager):
        self.manager = manager

    def retrieve_context_layer(self, layer_name: str, context: ExecutionContext) -> Dict[str, Any]:
        """
        Retrieves all active memory from a specific layer using the execution context.
        """
        if layer_name == "working":
            return self.manager.working.retrieve_all()
        elif layer_name == "session":
            return self.manager.session.retrieve_all(session_id=context.session_id)
        elif layer_name == "conversation":
            return self.manager.conversation.retrieve_all(conversation_id=context.session_id)
        elif layer_name == "journey":
            # Assuming execution context might hold journey ID in constraints or we use session_id
            journey_id = context.constraints.get("journey_id")
            if journey_id:
                return self.manager.journey.retrieve_all(journey_id=journey_id)
            return {}
        elif layer_name == "preference":
            user_id = context.constraints.get("user_id")
            if user_id:
                return self.manager.preference.retrieve_all(user_id=user_id)
            return {}
        elif layer_name == "reflection":
            return self.manager.reflection.retrieve_all(agent_identity=context.agent_identity)
        else:
            raise ValueError(f"Unknown memory layer: {layer_name}")

from typing import Any, Dict, List
from app.agents.memory.models import Memory

class ConversationMemory(Memory):
    """
    Maintains dialogue continuity for the conversational assistant.
    Stores previous messages and dialog context.
    """
    def __init__(self):
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}

    def store(self, key: str, value: Any, conversation_id: str = None, **kwargs) -> None:
        if not conversation_id:
            raise ValueError("conversation_id is required for ConversationMemory")
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
            
        # key is unused for simple list-append pattern, or used for specific context dict mapping
        self._conversations[conversation_id].append({"role": key, "content": value})

    def retrieve(self, key: str = None, conversation_id: str = None, **kwargs) -> Any:
        if not conversation_id:
            raise ValueError("conversation_id is required for ConversationMemory")
        return self._conversations.get(conversation_id, [])
        
    def retrieve_all(self, conversation_id: str = None, **kwargs) -> Dict[str, Any]:
        if not conversation_id:
            raise ValueError("conversation_id is required for ConversationMemory")
        return {"history": self._conversations.get(conversation_id, [])}

    def clear(self, conversation_id: str = None, **kwargs) -> None:
        if conversation_id and conversation_id in self._conversations:
            del self._conversations[conversation_id]

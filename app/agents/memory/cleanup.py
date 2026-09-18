from app.agents.memory.manager import MemoryManager
from app.agents.context import ExecutionContext

class MemoryCleanup:
    """
    Handles expiration policies across different memory lifespans.
    """
    def __init__(self, manager: MemoryManager):
        self.manager = manager

    def cleanup_after_execution(self):
        """Called when an agent completes its execution."""
        self.manager.working.clear()

    def cleanup_session(self, session_id: str):
        """Called when a user session ends."""
        self.manager.session.clear(session_id=session_id)
        
    def cleanup_conversation(self, conversation_id: str):
        """Called after conversation timeout."""
        self.manager.conversation.clear(conversation_id=conversation_id)

    def cleanup_journey(self, journey_id: str):
        """Called when a journey completes."""
        self.manager.journey.clear(journey_id=journey_id)

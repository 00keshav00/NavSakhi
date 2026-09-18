from app.agents.memory.working import WorkingMemory
from app.agents.memory.session import SessionMemory
from app.agents.memory.conversation import ConversationMemory
from app.agents.memory.journey import JourneyMemory
from app.agents.memory.preference import PreferenceMemory
from app.agents.memory.reflection import ReflectionMemory

class MemoryManager:
    """
    Orchestrates interactions across all six memory systems.
    Agents never directly manipulate another memory's internal state.
    """
    def __init__(self):
        # Instantiate memory layers
        self.working = WorkingMemory()
        
        # Shared components (in a real system these would be Singletons or connected to remote stores)
        self.session = SessionMemory()
        self.conversation = ConversationMemory()
        self.journey = JourneyMemory()
        self.preference = PreferenceMemory()
        self.reflection = ReflectionMemory()

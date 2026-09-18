from enum import Enum, auto

class AgentState(Enum):
    """
    Defines the exact runtime states of an agent during execution.
    An agent exists in exactly one state at any given moment.
    """
    CREATED = auto()
    INITIALIZING = auto()
    READY = auto()
    UNDERSTANDING_GOAL = auto()
    PLANNING = auto()
    WAITING_FOR_TOOL_EXECUTION = auto()
    PROCESSING_RESULTS = auto()
    REASONING = auto()
    DECISION_READY = auto()
    RESPONDING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

    def __str__(self):
        return self.name

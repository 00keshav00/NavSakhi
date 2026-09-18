from app.api.exceptions import SafeSheException

class AgentRuntimeError(SafeSheException):
    """Base class for all Agent Runtime exceptions."""
    def __init__(self, message: str, status_code: int = 500, error_code: str = "AGENT_RUNTIME_ERROR"):
        super().__init__(message=message, status_code=status_code, error_code=error_code)

class InvalidStateTransitionError(AgentRuntimeError):
    """Raised when an agent attempts an illegal state transition."""
    def __init__(self, current_state: str, attempted_state: str):
        super().__init__(
            message=f"Invalid transition from {current_state} to {attempted_state}.",
            error_code="INVALID_STATE_TRANSITION"
        )

class ContextValidationError(AgentRuntimeError):
    """Raised when the execution context is invalid or missing required fields."""
    def __init__(self, message: str):
        super().__init__(message=message, error_code="CONTEXT_VALIDATION_ERROR")
        
class AgentNotFoundError(AgentRuntimeError):
    """Raised when an agent cannot be found in the registry."""
    def __init__(self, agent_name: str):
        super().__init__(
            message=f"Agent '{agent_name}' is not registered.",
            status_code=404,
            error_code="AGENT_NOT_FOUND"
        )

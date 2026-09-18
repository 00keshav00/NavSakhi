from typing import Dict, Any, Optional

class ExecutionContext:
    """
    Immutable execution context passed through the execution pipeline.
    Serves as the single source of truth for the agent during its lifecycle.
    """
    def __init__(
        self,
        goal: str,
        agent_identity: str,
        session_id: str,
        execution_id: str,
        working_memory_ref: Any = None,
        available_tools: list = None,
        constraints: Dict[str, Any] = None,
        collected_evidence: Dict[str, Any] = None,
        execution_history: list = None,
        current_task: str = None
    ):
        self._goal = goal
        self._agent_identity = agent_identity
        self._session_id = session_id
        self._execution_id = execution_id
        self._working_memory_ref = working_memory_ref
        self._available_tools = available_tools or []
        self._constraints = constraints or {}
        self._collected_evidence = collected_evidence or {}
        self._execution_history = execution_history or []
        self._current_task = current_task
        self._assembled_context: Dict[str, Any] = {}

    def assemble(self, manager: Any) -> None:
        """
        Uses ContextAssembly to build the reasoning-ready context.
        manager must be an instance of MemoryManager.
        """
        from app.agents.memory.assembly import ContextAssembly
        assembly = ContextAssembly(manager)
        self._assembled_context = assembly.assemble(self)
        
    @property
    def assembled_context(self) -> Dict[str, Any]:
        return self._assembled_context

    @property
    def goal(self) -> str:
        return self._goal

    @property
    def agent_identity(self) -> str:
        return self._agent_identity

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def working_memory_ref(self) -> Any:
        return self._working_memory_ref

    @property
    def available_tools(self) -> list:
        return list(self._available_tools)

    @property
    def constraints(self) -> Dict[str, Any]:
        return dict(self._constraints)

    @property
    def collected_evidence(self) -> Dict[str, Any]:
        return dict(self._collected_evidence)

    @property
    def execution_history(self) -> list:
        return list(self._execution_history)
        
    @property
    def current_task(self) -> Optional[str]:
        return self._current_task

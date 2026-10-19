from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.agents.state import AgentState
from app.agents.context import ExecutionContext
from app.agents.events import RuntimeEvent
from app.agents.exceptions import InvalidStateTransitionError
from app.agents.planning.engine import PlanningEngine
from app.agents.planning.models import ExecutionPlan
from app.agents.intelligence.strategy import StrategyGenerator
from app.tools.registry import registry as global_tool_registry
from typing import List, Dict, Any
from app.agents.intelligence.models import ExecutionStrategy
from app.agents.reasoning.engine import ReasoningEngine
from app.agents.reasoning.models import ReasoningState
from app.agents.reflection.engine import ReflectionEngine
from app.agents.reflection.models import ExecutionOutcome
from app.agents.memory.manager import MemoryManager

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the runtime.
    """
    def __init__(self):
        self._state = AgentState.CREATED
        self._context: Optional[ExecutionContext] = None
        self._planning_engine = PlanningEngine()
        self._strategy_generator = StrategyGenerator(global_tool_registry)
        self._reasoning_engine = ReasoningEngine()
        self._memory_manager = MemoryManager() # A shared manager would usually be injected
        self._reflection_engine = ReflectionEngine(self._memory_manager)
        
        from app.agents.collaboration.coordinator import CollaborationCoordinator
        self._collaboration_coordinator = CollaborationCoordinator() # Shared instance
        self._active_session_id: Optional[str] = None
        
        self._execution_plan: Optional[ExecutionPlan] = None
        self._execution_strategies: List[ExecutionStrategy] = []
        self._execution_results: List[Dict[str, Any]] = []
        self._reasoning_state: Optional[ReasoningState] = None
        self._execution_outcome: Optional[ExecutionOutcome] = None

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def state(self) -> AgentState:
        return self._state

    def set_state(self, new_state: AgentState):
        """State transitions will be strictly managed by AgentLifecycle."""
        self._state = new_state
        
    def initialize(self, context: ExecutionContext):
        if self._state != AgentState.CREATED:
            raise InvalidStateTransitionError(self._state.name, AgentState.INITIALIZING.name)
        self._context = context
        self.set_state(AgentState.INITIALIZING)
        
    # The following lifecycle methods must be implemented by subclasses,
    # but actual logic will be added in subsequent milestones (Planning Engine, etc.).
    # For now, they act as the execution interface.
    
    @abstractmethod
    async def receive_goal(self) -> None:
        pass
        
    @abstractmethod
    async def understand_goal(self) -> None:
        pass
        
    async def plan(self) -> None:
        """
        Executes the cognitive planning step.
        """
        if not self._context:
            raise InvalidStateTransitionError("No context provided", "PLANNING")
        
        # Use the Planning Engine to construct the execution plan
        self._execution_plan = self._planning_engine.create_plan(self._context)
        
        # In a real environment, this plan would be stored in Working Memory.
        # For this milestone, we store it on the agent itself.
        
    async def select_tools(self) -> None:
        """
        Translates the ExecutionPlan's capability requirements into concrete tool execution strategies.
        """
        if not self._context:
            raise InvalidStateTransitionError("No context provided", "SELECTING_TOOLS")
            
        if not self._execution_plan:
            raise InvalidStateTransitionError("No execution plan found. Cannot select tools.", "SELECTING_TOOLS")
            
        self._execution_strategies = self._strategy_generator.generate_strategies(self._context, self._execution_plan)
        
    async def execute_tools(self) -> None:
        """
        Executes the strategies. In a real environment, this invokes ToolManager.
        For this deterministic milestone, we mock the results.
        """
        self._execution_results = []
        for strategy in self._execution_strategies:
            self._execution_results.append({
                "tool_name": strategy.selected_tool_name or strategy.capability,
                "status": "success",
                "data": {"mock_result": True},
                "timestamp": "now"
            })
        
    async def process_results(self) -> None:
        """
        Passes results into the ReasoningEngine.
        """
        if not self._context:
            raise InvalidStateTransitionError("No context provided", "PROCESSING_RESULTS")
        self._reasoning_state = self._reasoning_engine.process(self._context, self._execution_results)
        
    async def reason(self) -> None:
        """
        The reasoning steps are already handled in process() by the ReasoningEngine.
        """
        pass
        
    async def make_decision(self) -> None:
        """
        Validates the generated decision.
        """
        if not self._reasoning_state or not self._reasoning_state.is_validated:
            # We don't raise here immediately; we let reflection handle it.
            pass
            
    async def reflect(self) -> None:
        """
        Evaluates the outcome and generates recovery strategies or insights.
        """
        if not self._reasoning_state:
            raise InvalidStateTransitionError("No reasoning state available to reflect upon.", "REFLECTING")
            
        self._execution_outcome = self._reflection_engine.reflect(self._reasoning_state)
        
    async def delegate_task(self, required_capability: str, payload: Dict[str, Any]) -> None:
        """
        Delegates a task to another agent without calling it directly.
        """
        if not self._active_session_id:
            session = self._collaboration_coordinator.initialize_session(self.name)
            self._active_session_id = session.session_id
            
        self._collaboration_coordinator.delegate_and_send(self._active_session_id, self.name, required_capability, payload)
        
    async def receive_messages(self) -> None:
        """
        Pulls pending messages from the inter-agent message bus.
        """
        if self._active_session_id:
            message = self._collaboration_coordinator.receive_messages(self._active_session_id, self.name)
            if message:
                # In a real environment, the agent would process the message payload.
                pass
        
    async def format_output(self) -> None:
        """
        Formats final output using ReasoningEngine.
        """
        if self._reasoning_state:
            formatted = self._reasoning_engine.format_output(self._reasoning_state)
            # Would normally return this to the user/coordinator
        
    @abstractmethod
    async def respond(self) -> Dict[str, Any]:
        pass

class SpecialistAgent(BaseAgent):
    """
    Abstract base class for all specialized domain agents.
    """
    pass

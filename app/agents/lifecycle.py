from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.agents.exceptions import InvalidStateTransitionError
from app.config.logging_config import logger
from typing import Dict, Any

class AgentLifecycle:
    """
    Ensures that an agent progresses through its lifecycle states deterministically.
    No agent may skip mandatory lifecycle stages.
    """
    def __init__(self, agent: BaseAgent):
        self.agent = agent

    async def execute(self) -> Dict[str, Any]:
        """
        Executes the strictly defined Agent Lifecycle.
        """
        try:
            logger.info(f"[{self.agent.name}] Starting lifecycle execution.")
            
            # Initialized state should have been set by factory/manager prior to execute
            if self.agent.state != AgentState.INITIALIZING:
                raise InvalidStateTransitionError(self.agent.state.name, AgentState.INITIALIZING.name)
                
            self.agent.set_state(AgentState.READY)
            
            # 1. Receive Goal
            await self.agent.receive_goal()
            
            # 2. Understand Goal
            self.agent.set_state(AgentState.UNDERSTANDING_GOAL)
            await self.agent.understand_goal()
            
            # 3. Planning
            self.agent.set_state(AgentState.PLANNING)
            await self.agent.plan()
            
            # 4. Select Tools
            await self.agent.select_tools()
            
            # 5. Execute Tools
            self.agent.set_state(AgentState.WAITING_FOR_TOOL_EXECUTION)
            await self.agent.execute_tools()
            
            # 6. Process Results
            self.agent.set_state(AgentState.PROCESSING_RESULTS)
            await self.agent.process_results()
            
            # 7. Reason
            self.agent.set_state(AgentState.REASONING)
            await self.agent.reason()
            
            # 8. Decision Ready
            self.agent.set_state(AgentState.DECISION_READY)
            await self.agent.make_decision()
            
            # 9. Respond
            self.agent.set_state(AgentState.RESPONDING)
            response = await self.agent.respond()
            
            # 10. Complete
            self.agent.set_state(AgentState.COMPLETED)
            logger.info(f"[{self.agent.name}] Execution completed successfully.")
            return response
            
        except Exception as e:
            self.agent.set_state(AgentState.FAILED)
            logger.error(f"[{self.agent.name}] Execution failed: {str(e)}")
            raise e

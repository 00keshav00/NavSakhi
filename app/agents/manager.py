from typing import Dict, Any
from app.agents.factory import AgentFactory
from app.agents.lifecycle import AgentLifecycle
from app.agents.context import ExecutionContext

class AgentManager:
    """
    Manages the execution environment and orchestrates the agent lifecycle.
    """
    @staticmethod
    async def execute_agent(agent_name: str, context: ExecutionContext) -> Dict[str, Any]:
        """
        Creates an agent, initializes its lifecycle, and executes it to completion.
        """
        agent = AgentFactory.create_agent(agent_name, context)
        lifecycle = AgentLifecycle(agent)
        return await lifecycle.execute()

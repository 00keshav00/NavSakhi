from typing import Dict, Any
from app.agents.registry import AgentRegistry
from app.agents.base import BaseAgent
from app.agents.context import ExecutionContext
from app.agents.exceptions import AgentRuntimeError

class AgentFactory:
    """
    Instantiates agents with the correct dependencies and initial context.
    """
    @classmethod
    def create_agent(cls, name: str, context: ExecutionContext) -> BaseAgent:
        agent_class = AgentRegistry.get_agent_class(name)
        try:
            agent = agent_class()
            agent.initialize(context)
            return agent
        except Exception as e:
            raise AgentRuntimeError(f"Failed to instantiate agent '{name}': {str(e)}")

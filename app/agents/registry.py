from typing import Dict, Type
from app.agents.base import BaseAgent
from app.agents.exceptions import AgentNotFoundError

class AgentRegistry:
    """
    Registry for discovering available agents dynamically.
    """
    _agents: Dict[str, Type[BaseAgent]] = {}

    @classmethod
    def register(cls, agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
        # Temporarily instantiate to get the name, a better design in production might use class attributes
        temp_instance = agent_class()
        cls._agents[temp_instance.name] = agent_class
        return agent_class

    @classmethod
    def get_agent_class(cls, name: str) -> Type[BaseAgent]:
        if name not in cls._agents:
            raise AgentNotFoundError(name)
        return cls._agents[name]
        
    @classmethod
    def list_agents(cls) -> list:
        return list(cls._agents.keys())

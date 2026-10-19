from typing import Dict, Type
from app.agents.specialized.base import BaseSpecializedAgent

class SpecializedAgentRegistry:
    """
    Centralized AgentRegistry for all specialized agents.
    """
    _agents: Dict[str, Type[BaseSpecializedAgent]] = {}

    @classmethod
    def register(cls, name: str, agent_class: Type[BaseSpecializedAgent]):
        cls._agents[name] = agent_class

    @classmethod
    def get_agent(cls, name: str) -> BaseSpecializedAgent:
        if name not in cls._agents:
            raise ValueError(f"Agent {name} not found in SpecializedAgentRegistry")
        return cls._agents[name]()

def setup_registry():
    from app.agents.specialized.routing import RoutingAgent
    from app.agents.specialized.weather import WeatherAgent
    from app.agents.specialized.community import CommunityAgent
    from app.agents.specialized.emergency import EmergencyAgent
    from app.agents.specialized.assistant import AssistantAgent
    from app.agents.specialized.transit import TransitAgent
    from app.agents.specialized.dashboard import DashboardAgent
    from app.agents.specialized.profile import ProfileAgent
    
    SpecializedAgentRegistry.register("RoutingAgent", RoutingAgent)
    SpecializedAgentRegistry.register("WeatherAgent", WeatherAgent)
    SpecializedAgentRegistry.register("CommunityAgent", CommunityAgent)
    SpecializedAgentRegistry.register("EmergencyAgent", EmergencyAgent)
    SpecializedAgentRegistry.register("AssistantAgent", AssistantAgent)
    SpecializedAgentRegistry.register("TransitAgent", TransitAgent)
    SpecializedAgentRegistry.register("DashboardAgent", DashboardAgent)
    SpecializedAgentRegistry.register("ProfileAgent", ProfileAgent)

setup_registry()

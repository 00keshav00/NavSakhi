from typing import Optional, List
from app.agents.registry import AgentRegistry
from app.agents.base import BaseAgent

class CapabilityMatching:
    """
    Evaluates agent contracts against a required task.
    """
    def match(self, required_capability: str, agents: List[BaseAgent]) -> Optional[BaseAgent]:
        """
        Determines the best agent for a specific capability.
        (Mock logic for deterministic milestone execution)
        """
        # In a real environment, we'd inspect agent capability metadata.
        # Here we just mock based on agent name conventions.
        for agent in agents:
            if required_capability.lower() in agent.name.lower():
                return agent
        
        # Fallback to coordinator or first available
        return agents[0] if agents else None

class AgentDiscovery:
    """
    Finds agents available for collaboration.
    """
    def __init__(self):
        self.matcher = CapabilityMatching()
        
    def discover(self, required_capability: str) -> Optional[str]:
        """
        Returns the agent ID (name) capable of handling the request.
        """
        # Since AgentRegistry stores classes, we would normally instantiate or query metadata.
        # For this deterministic milestone, we return a mocked agent name string.
        known_agents = list(AgentRegistry._registry.keys())
        for name in known_agents:
            if required_capability.lower() in name.lower():
                return name
                
        return known_agents[0] if known_agents else None

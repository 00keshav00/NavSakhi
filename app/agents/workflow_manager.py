from typing import Dict, Any
from app.agents.specialized.registry import SpecializedAgentRegistry

class WorkflowManager:
    """
    Orchestrates the agents based on the required workflow.
    """
    async def run_workflow(self, workflow_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        results = {}
        agents_to_run = []
        
        if workflow_type == "journey_plan":
            agents_to_run = ["RoutingAgent", "WeatherAgent", "CommunityAgent", "TransitAgent"]
        elif workflow_type == "emergency":
            agents_to_run = ["EmergencyAgent", "WeatherAgent", "CommunityAgent"]
        elif workflow_type == "dashboard":
            agents_to_run = ["DashboardAgent"]
        elif workflow_type == "assistant":
            agents_to_run = ["AssistantAgent", "WeatherAgent", "CommunityAgent"]
        elif workflow_type == "profile":
            agents_to_run = ["ProfileAgent"]
            
        for agent_name in agents_to_run:
            agent = SpecializedAgentRegistry.get_agent(agent_name)
            results[agent_name] = await agent.execute(context)
            
        return results

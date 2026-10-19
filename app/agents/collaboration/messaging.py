from typing import Dict, List, Optional
from app.agents.collaboration.models import AgentMessage

class InterAgentMessaging:
    """
    Secure message bus that routes AgentMessages between agents asynchronously.
    """
    def __init__(self):
        self._inboxes: Dict[str, List[AgentMessage]] = {}
        
    def register(self, agent_id: str) -> None:
        """
        Registers an agent on the message bus.
        """
        if agent_id not in self._inboxes:
            self._inboxes[agent_id] = []
            
    def send(self, message: AgentMessage) -> None:
        """
        Routes the message to the receiver's inbox.
        """
        if message.receiver_id in self._inboxes:
            self._inboxes[message.receiver_id].append(message)
        else:
            # Drop or handle unroutable messages
            pass
            
    def receive(self, agent_id: str) -> Optional[AgentMessage]:
        """
        Pulls the next message for the agent.
        """
        inbox = self._inboxes.get(agent_id, [])
        if inbox:
            return inbox.pop(0)
        return None

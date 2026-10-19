import uuid
from datetime import datetime
from typing import Dict, Any
from app.agents.collaboration.models import AgentMessage
from app.agents.collaboration.discovery import AgentDiscovery

class TaskDelegation:
    """
    Structures a goal/task into an AgentMessage directed to the discovered specialist agent.
    """
    def __init__(self):
        self.discovery = AgentDiscovery()
        
    def delegate(self, sender_id: str, required_capability: str, payload: Dict[str, Any]) -> AgentMessage:
        """
        Creates a formal message for delegation.
        """
        receiver_id = self.discovery.discover(required_capability)
        
        if not receiver_id:
            raise Exception(f"No agent discovered for capability: {required_capability}")
            
        return AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            intent="DELEGATE_TASK",
            payload=payload,
            timestamp=datetime.utcnow().isoformat()
        )

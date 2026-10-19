import uuid
from typing import Dict, Any, Optional
from app.agents.collaboration.models import CollaborationSession, AgentMessage
from app.agents.collaboration.discovery import AgentDiscovery
from app.agents.collaboration.delegation import TaskDelegation
from app.agents.collaboration.messaging import InterAgentMessaging
from app.agents.collaboration.conflict import ConflictResolution

class CollaborationCoordinator:
    """
    The central hub orchestrating discovery, messaging, session lifecycle, and completion.
    """
    def __init__(self):
        self.discovery = AgentDiscovery()
        self.delegation = TaskDelegation()
        self.messaging = InterAgentMessaging()
        self.conflict = ConflictResolution()
        self.active_sessions: Dict[str, CollaborationSession] = {}
        
    def initialize_session(self, initiator_id: str) -> CollaborationSession:
        """
        Starts a new collaboration session.
        """
        session = CollaborationSession(
            session_id=str(uuid.uuid4()),
            initiator_id=initiator_id,
            participants=[initiator_id]
        )
        self.active_sessions[session.session_id] = session
        self.messaging.register(initiator_id)
        return session
        
    def delegate_and_send(self, session_id: str, sender_id: str, required_capability: str, payload: Dict[str, Any]) -> None:
        """
        Discovers the right agent and delegates the task.
        """
        if session_id not in self.active_sessions:
            raise Exception("Invalid session ID")
            
        session = self.active_sessions[session_id]
        
        message = self.delegation.delegate(sender_id, required_capability, payload)
        
        if message.receiver_id not in session.participants:
            session.participants.append(message.receiver_id)
            self.messaging.register(message.receiver_id)
            
        self.messaging.send(message)
        session.history.append(message)
        
    def receive_messages(self, session_id: str, agent_id: str) -> Optional[AgentMessage]:
        """
        Pulls messages for the agent within the session.
        """
        return self.messaging.receive(agent_id)
        
    def terminate_session(self, session_id: str) -> None:
        """
        Marks a collaboration session as completed.
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id].status = "completed"

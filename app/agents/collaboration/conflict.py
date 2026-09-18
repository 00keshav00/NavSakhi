from typing import Dict, Any
from app.agents.collaboration.models import AgentMessage, CollaborationSession

class ConflictResolution:
    """
    Determines how to resolve deadlocks or contradictory outputs between collaborating agents.
    """
    def resolve(self, session: CollaborationSession, message_a: AgentMessage, message_b: AgentMessage) -> Dict[str, Any]:
        """
        Provides a deterministic resolution for conflicting agent outputs.
        """
        # In this milestone, we resolve conflict by favoring the primary/initiator, 
        # or logging the conflict for human review.
        resolution = {
            "resolved_state": message_a.payload, # Naive resolution
            "discarded_state": message_b.payload,
            "reason": "Favoring primary agent."
        }
        
        session.context.resolved_conflicts.append(resolution)
        return resolution

from datetime import datetime
from typing import Dict, Any, Optional

class RuntimeEvent:
    """
    Represents an observable state transition or communication
    within the Agent Runtime.
    """
    def __init__(self, event_type: str, source: str, payload: Dict[str, Any] = None):
        self.event_type = event_type
        self.source = source
        self.payload = payload or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "source": self.source,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat()
        }

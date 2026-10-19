from typing import Any, Dict
from app.agents.memory.models import Memory

class JourneyMemory(Memory):
    """
    Stores information specific to an active journey.
    Cleared when the journey completes.
    """
    def __init__(self):
        self._journeys: Dict[str, Dict[str, Any]] = {}

    def store(self, key: str, value: Any, journey_id: str = None, **kwargs) -> None:
        if not journey_id:
            raise ValueError("journey_id is required for JourneyMemory")
        if journey_id not in self._journeys:
            self._journeys[journey_id] = {}
        self._journeys[journey_id][key] = value

    def retrieve(self, key: str, journey_id: str = None, **kwargs) -> Any:
        if not journey_id:
            raise ValueError("journey_id is required for JourneyMemory")
        return self._journeys.get(journey_id, {}).get(key)
        
    def retrieve_all(self, journey_id: str = None, **kwargs) -> Dict[str, Any]:
        if not journey_id:
            raise ValueError("journey_id is required for JourneyMemory")
        return dict(self._journeys.get(journey_id, {}))

    def clear(self, journey_id: str = None, **kwargs) -> None:
        if journey_id and journey_id in self._journeys:
            del self._journeys[journey_id]

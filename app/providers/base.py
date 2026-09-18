from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseMapsProvider(ABC):
    @abstractmethod
    async def get_routes(self, source: Dict[str, float], destination: Dict[str, float], mode: str) -> List[Dict[str, Any]]:
        pass

class BaseWeatherProvider(ABC):
    @abstractmethod
    async def get_weather(self, location: Dict[str, float]) -> Dict[str, Any]:
        pass

class BaseNotificationProvider(ABC):
    @abstractmethod
    async def send_notification(self, contacts: List[str], message: str, notification_type: str) -> Dict[str, Any]:
        pass

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, context: Dict[str, Any]) -> str:
        pass

class BasePredictionProvider(ABC):
    @abstractmethod
    async def get_crowd_prediction(self, location: Dict[str, float], time: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_safety_score(self, route_features: Dict[str, Any]) -> Dict[str, Any]:
        pass

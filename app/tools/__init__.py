from app.tools.registry import registry
from app.tools.manager import ToolManager

from app.tools.routing import RoutingTool
from app.tools.location import LocationTool
from app.tools.weather import WeatherTool
from app.tools.community import CommunityTool
from app.tools.notification import NotificationTool

# Register all tools automatically upon import
registry.register(RoutingTool())
registry.register(LocationTool())
registry.register(WeatherTool())
registry.register(CommunityTool())
registry.register(NotificationTool())

__all__ = ["registry", "ToolManager"]

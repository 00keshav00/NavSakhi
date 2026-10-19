from typing import Dict, List, Optional
from app.tools.base import BaseTool

class ToolRegistry:
    """
    Central registry for all available tools in the system.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Registers an instantiated tool."""
        self._tools[tool.name] = tool

    def get_tool(self, tool_name: str) -> BaseTool:
        """Retrieves a tool by name."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found in registry.")
        return self._tools[tool_name]

    def list_tools(self) -> Dict[str, str]:
        """Returns a map of tool names to their descriptions."""
        return {name: tool.description for name, tool in self._tools.items()}

    def discover_tools_by_capability(self, capability: str) -> List[BaseTool]:
        """Finds all tools providing the specified capability, ordered by ranking score (descending)."""
        matching_tools = [tool for tool in self._tools.values() if tool.metadata.capability == capability]
        matching_tools.sort(key=lambda t: t.metadata.ranking_score, reverse=True)
        return matching_tools

    def get_best_tool_for_capability(self, capability: str) -> Optional[BaseTool]:
        """Returns the highest ranked tool for a capability, or None if no tools exist."""
        tools = self.discover_tools_by_capability(capability)
        return tools[0] if tools else None

# Global registry instance
registry = ToolRegistry()

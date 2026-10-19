from typing import Dict, Any
from app.tools.registry import registry
from app.config.logging_config import logger

class ToolManager:
    """
    Executes tools and handles failures based on the graceful degradation policy.
    """
    
    @staticmethod
    async def execute_tool(tool_name: str, params: Dict[str, Any], fail_gracefully: bool = True) -> Dict[str, Any]:
        """
        Executes a specific tool by name with the given parameters.
        """
        try:
            tool = registry.get_tool(tool_name)
            logger.info(f"Executing tool: {tool_name}")
            return await tool.execute(params)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            if fail_gracefully:
                return {"status": "error", "error": str(e), "data": None}
            raise e

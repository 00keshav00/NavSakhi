from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.tools.base import ExecutionPolicy, ToolContract

class ExecutionStrategy(BaseModel):
    """
    Represents how a specific capability will be executed.
    Bridges the Planning Engine's ExecutionTask with the Tool Layer's BaseTool.
    """
    task_id: str
    capability: str
    selected_tool_name: Optional[str] = None
    parameters: Dict[str, Any] = {}
    policy: ExecutionPolicy
    contract: ToolContract
    is_resolved: bool = False

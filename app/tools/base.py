from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel, Field

class ToolMetadata(BaseModel):
    capability: str
    required_inputs: List[str]
    output_schema: Dict[str, Any]
    ranking_score: int = 1  # Higher is better for capability resolution

class ToolContract(BaseModel):
    preconditions: List[str] = Field(default_factory=list)
    postconditions: List[str] = Field(default_factory=list)

class ExecutionPolicy(BaseModel):
    retry_count: int = 3
    timeout_ms: int = 5000
    fallback_capability: str = None
    graceful_degradation: bool = True

class BaseTool(ABC):
    """
    Abstract base class for all SafeShe tools.
    Every tool must implement an execute method that takes a context dictionary
    and returns a result dictionary.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        pass
        
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Capabilities and ranking data."""
        pass
        
    @property
    def contract(self) -> ToolContract:
        """Execution preconditions and postconditions."""
        return ToolContract()
        
    @property
    def policy(self) -> ExecutionPolicy:
        """Execution constraints and resilience strategies."""
        return ExecutionPolicy()

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the tool's core logic.
        """
        pass

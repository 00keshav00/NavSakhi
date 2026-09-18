from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ExecutionTask(BaseModel):
    """
    Represents a single logical objective within a plan.
    Does NOT contain tool execution logic; only describes what is needed.
    """
    task_id: str
    description: str
    required_capabilities: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    is_completed: bool = False
    result: Optional[Any] = None

class ExecutionGraph(BaseModel):
    """
    Explicitly models tasks, dependencies, and parallel branches.
    """
    tasks: Dict[str, ExecutionTask] = Field(default_factory=dict)
    
    def add_task(self, task: ExecutionTask):
        self.tasks[task.task_id] = task

    def get_executable_tasks(self) -> List[ExecutionTask]:
        """Returns tasks whose dependencies are fully met and are not completed."""
        executable = []
        for task in self.tasks.values():
            if not task.is_completed:
                can_run = all(self.tasks[dep].is_completed for dep in task.dependencies)
                if can_run:
                    executable.append(task)
        return executable

class ExecutionPlan(BaseModel):
    """
    The structured planning result serving as the contract between Planning and Runtime.
    """
    intent: str
    goals: List[str]
    constraints: Dict[str, Any]
    required_information: List[str]
    graph: ExecutionGraph
    is_valid: bool = False

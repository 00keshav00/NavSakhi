import uuid
from typing import List
from app.agents.planning.models import ExecutionTask
from app.agents.context import ExecutionContext

class TaskDecomposer:
    """
    Breaks required capabilities into concrete ExecutionTask instances.
    """
    def decompose(self, context: ExecutionContext, requirements: List[str]) -> List[ExecutionTask]:
        tasks = []
        for req in requirements:
            # Create a logical task for each required capability
            task = ExecutionTask(
                task_id=str(uuid.uuid4()),
                description=f"Execute {req} capability",
                required_capabilities=[req]
            )
            tasks.append(task)
            
        # In a real LLM implementation, the decomposer would break down larger objectives 
        # (e.g. "Compare Alternatives", "Produce Recommendation") which don't map directly to tools.
        # For this milestone, we add a mock reasoning/decision task.
        decision_task = ExecutionTask(
            task_id=str(uuid.uuid4()),
            description="Produce final decision based on evidence",
            required_capabilities=[] # Requires reasoning, not an external tool capability
        )
        tasks.append(decision_task)
        
        return tasks

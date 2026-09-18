from typing import List
from app.agents.planning.models import ExecutionTask

class DependencyAnalyzer:
    """
    Determines task dependencies before execution to construct the dependency graph.
    """
    def analyze(self, tasks: List[ExecutionTask]) -> List[ExecutionTask]:
        # Identify the decision task
        decision_task = next((t for t in tasks if "decision" in t.description.lower()), None)
        
        if decision_task:
            # The decision task depends on all capability execution tasks
            for task in tasks:
                if task.task_id != decision_task.task_id:
                    decision_task.dependencies.append(task.task_id)
                    
        # In a real LLM implementation, complex dependencies (e.g., Prediction depends on Routing)
        # would be established here by analyzing the tasks.
        return tasks

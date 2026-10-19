from app.agents.planning.models import ExecutionPlan
from app.agents.context import ExecutionContext

class ReplanningEngine:
    """
    Supports updating an execution plan mid-execution based on tool failures or new constraints.
    """
    def replan(self, context: ExecutionContext, current_plan: ExecutionPlan) -> ExecutionPlan:
        """
        Updates the remaining execution graph. Completed tasks are never repeated.
        """
        # In this milestone, we define the structure for replanning.
        # It takes the current plan, evaluates failures from the context, 
        # and would re-invoke the planning pipeline for uncompleted tasks.
        return current_plan

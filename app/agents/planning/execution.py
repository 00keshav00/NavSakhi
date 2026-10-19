from typing import List
from app.agents.planning.models import ExecutionTask, ExecutionGraph

class ExecutionPlanner:
    """
    Combines tasks into a finalized ExecutionGraph, aiming to maximize parallelism.
    """
    def generate_graph(self, tasks: List[ExecutionTask]) -> ExecutionGraph:
        graph = ExecutionGraph()
        for task in tasks:
            graph.add_task(task)
        return graph

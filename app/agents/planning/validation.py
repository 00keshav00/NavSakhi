from app.agents.planning.models import ExecutionGraph, ExecutionPlan

class PlanValidator:
    """
    Validates the execution graph ensuring dependencies are satisfiable and no cycles exist.
    """
    def validate(self, plan: ExecutionPlan) -> bool:
        graph = plan.graph
        
        # 1. Check if all required tasks exist
        if not graph.tasks:
            return False
            
        # 2. Check for circular dependencies
        visited = set()
        path = set()
        
        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            path.add(task_id)
            
            for dep_id in graph.tasks[task_id].dependencies:
                if dep_id not in graph.tasks:
                    return True # Dependency is missing entirely
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in path:
                    return True
                    
            path.remove(task_id)
            return False

        for task_id in graph.tasks:
            if task_id not in visited:
                if has_cycle(task_id):
                    return False
                    
        # 3. Check for termination condition
        # An execution graph must have at least one task with no outgoing dependencies
        # that acts as the final resolution task (e.g., producing the decision).
        # We can check if there's any task that no other task depends on.
        all_deps = set()
        for task in graph.tasks.values():
            all_deps.update(task.dependencies)
            
        leaf_nodes = [t_id for t_id in graph.tasks if t_id not in all_deps]
        if not leaf_nodes:
            return False
            
        plan.is_valid = True
        return True

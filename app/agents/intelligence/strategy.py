from typing import List
from app.agents.planning.models import ExecutionTask, ExecutionPlan
from app.agents.intelligence.models import ExecutionStrategy
from app.tools.registry import ToolRegistry
from app.agents.context import ExecutionContext

class StrategyGenerator:
    """
    Transforms ExecutionTasks into concrete ExecutionStrategies without executing them.
    Discovers tools dynamically from the ToolRegistry.
    """
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def generate_strategies(self, context: ExecutionContext, plan: ExecutionPlan) -> List[ExecutionStrategy]:
        strategies = []
        for task in plan.graph.tasks.values():
            # In this milestone, we map the primary capability required by the task.
            # Real LLM implementation might resolve multiple capabilities per task.
            if not task.required_capabilities:
                continue
                
            capability = task.required_capabilities[0]
            best_tool = self.registry.get_best_tool_for_capability(capability)
            
            if best_tool:
                # Tool Intelligence found a tool for this capability
                strategy = ExecutionStrategy(
                    task_id=task.task_id,
                    capability=capability,
                    selected_tool_name=best_tool.name,
                    policy=best_tool.policy,
                    contract=best_tool.contract,
                    is_resolved=True
                )
            else:
                # No tool exists for this capability - fallback or graceful degradation required
                from app.tools.base import ExecutionPolicy, ToolContract
                strategy = ExecutionStrategy(
                    task_id=task.task_id,
                    capability=capability,
                    policy=ExecutionPolicy(graceful_degradation=True),
                    contract=ToolContract(),
                    is_resolved=False
                )
                
            strategies.append(strategy)
            
        return strategies

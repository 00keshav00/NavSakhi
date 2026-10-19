from typing import Dict, Any, Tuple
from app.agents.reasoning.models import ReasoningState
from app.agents.reflection.models import ExecutionOutcome
from app.agents.reflection.analysis import OutcomeAnalyzer, SuccessEvaluator
from app.agents.reflection.failure import FailureClassifier
from app.agents.reflection.recovery import RecoveryPlanner
from app.agents.reflection.improvement import SelfImprovementGenerator
from app.agents.reflection.audit import ExecutionAuditLogger
from app.agents.reflection.memory import ReflectionMemoryGenerator
from app.agents.memory.manager import MemoryManager

class ReflectionEngine:
    """
    Orchestrates the evaluation, failure mapping, recovery planning, and insight generation.
    """
    def __init__(self, memory_manager: MemoryManager):
        self.analyzer = OutcomeAnalyzer()
        self.success_evaluator = SuccessEvaluator()
        self.classifier = FailureClassifier()
        self.recovery_planner = RecoveryPlanner()
        self.improvement_generator = SelfImprovementGenerator()
        self.audit_logger = ExecutionAuditLogger()
        self.memory_generator = ReflectionMemoryGenerator(memory_manager)

    def reflect(self, state: ReasoningState) -> ExecutionOutcome:
        """
        Executes the reflection lifecycle based on the reasoning state.
        """
        is_success, reason = self.analyzer.analyze(state)
        
        outcome = ExecutionOutcome(
            execution_id=state.execution_id,
            is_success=is_success
        )
        
        if is_success:
            evaluation = self.success_evaluator.evaluate(state)
            outcome.audit_trail.append(evaluation)
        else:
            # 1. Classify the failure
            classification = self.classifier.classify(state, reason)
            outcome.failure_classification = classification
            
            # 2. Plan recovery
            recovery = self.recovery_planner.plan_recovery(classification)
            outcome.recovery_plan = recovery
            
        # 3. Generate self-improvement insights
        insight = self.improvement_generator.generate(outcome)
        outcome.insights.append(insight)
        
        # 4. Store insight in Reflection Memory
        agent_identity = state.context.get("agent_identity", "unknown_agent")
        self.memory_generator.store_insight(agent_identity, insight)
        
        # 5. Log audit trail
        self.audit_logger.log_outcome(outcome)
        
        return outcome

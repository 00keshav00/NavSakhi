from app.agents.reflection.models import FailureClassification, RecoveryPlan

class RetryStrategyGenerator:
    """
    Calculates backoff and retry parameters based on failure type.
    """
    def generate(self, classification: FailureClassification) -> RecoveryPlan:
        if classification.is_recoverable:
            return RecoveryPlan(
                strategy_name="exponential_backoff",
                parameters={"max_retries": 3, "initial_delay_ms": 1000}
            )
        return RecoveryPlan(
            strategy_name="abort",
            parameters={"reason": "Unrecoverable error"}
        )

class RecoveryPlanner:
    """
    Builds a full recovery plan to salvage the execution.
    """
    def __init__(self):
        self.retry_generator = RetryStrategyGenerator()
        
    def plan_recovery(self, classification: FailureClassification) -> RecoveryPlan:
        """
        Constructs the recovery strategy.
        """
        return self.retry_generator.generate(classification)

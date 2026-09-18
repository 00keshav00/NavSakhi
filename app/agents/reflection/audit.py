import logging
from app.agents.reflection.models import ExecutionOutcome

logger = logging.getLogger(__name__)

class ExecutionAuditLogger:
    """
    Persists the complete execution trail for transparency.
    """
    def log_outcome(self, outcome: ExecutionOutcome) -> None:
        """
        Logs the outcome to standard logging (or an audit DB in the future).
        """
        status = "SUCCESS" if outcome.is_success else "FAILURE"
        logger.info(f"[AUDIT] Execution {outcome.execution_id} completed with status: {status}")
        
        if outcome.failure_classification:
            logger.info(f"[AUDIT] Failure Category: {outcome.failure_classification.category}")
            logger.info(f"[AUDIT] Failure Reason: {outcome.failure_classification.description}")
            
        if outcome.recovery_plan:
            logger.info(f"[AUDIT] Recovery Strategy: {outcome.recovery_plan.strategy_name}")
            
        for insight in outcome.insights:
            logger.info(f"[AUDIT] Insight generated: {insight.recommendation}")

"""Escalation handler for failed tasks."""

from typing import Dict, Any

from src.config import get_logger


logger = get_logger(__name__)


class Escalator:
    """Handle task escalation when local implementation fails."""
    
    @staticmethod
    def escalate(
        task: Dict[str, Any],
        iteration: int,
        error_message: str,
        previous_code: str = "",
        test_output: str = "",
    ) -> Dict[str, Any]:
        """
        Escalate task to cloud with full context.
        
        Returns:
            escalated_task dict with preserved context
        """
        
        escalated = {
            **task,
            "model_tier": "cloud",
            "escalation_iteration": iteration,
            "escalation_reason": error_message,
            "context": {
                "previous_code": previous_code,
                "test_output": test_output,
                "iteration_count": iteration,
            },
        }
        
        logger.info(
            f"Task {task['id']} escalated to cloud at iteration {iteration}: {error_message}"
        )
        
        return escalated
    
    @staticmethod
    def log_escalation(task_id: str, reason: str, additional_context: str = ""):
        """Log escalation event for observability."""
        logger.warning(f"ESCALATION: Task {task_id} - {reason}\n{additional_context}")

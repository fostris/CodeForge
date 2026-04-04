"""Router for directing tasks to appropriate model tier."""

from typing import Literal, Dict, Any

from src.config import get_logger


logger = get_logger(__name__)


class Router:
    """Route tasks to model tiers based on decision tree."""
    
    @staticmethod
    def route_task(task: Dict[str, Any]) -> Literal["local_cheap", "local_strong", "cloud"]:
        """
        Route a task to appropriate model tier.
        
        Decision tree:
        1. Check risk_level → high → CLOUD
        2. Check file count → >3 → REJECT
        3. Check size + domain → route accordingly
        """
        
        # High-risk tasks always go to cloud
        risk_level = task.get("risk_level", "low")
        if risk_level == "high":
            logger.info(f"Task {task['id']} routed to CLOUD (high risk)")
            return "cloud"
        
        # Check file count
        file_count = len(task.get("files", []))
        if file_count > 3:
            logger.warning(f"Task {task['id']} has {file_count} files (>3), should re-decompose")
            return "cloud"  # Escalate to review
        
        # Route by size and domain
        size = task.get("size", "M")
        module = task.get("module", "")
        
        # Security/auth/payment-related → cloud
        security_modules = {"auth", "security", "payment", "billing"}
        if module.lower() in security_modules:
            logger.info(f"Task {task['id']} routed to CLOUD (security domain)")
            return "cloud"
        
        # Small tasks → cheap local
        if size == "S":
            logger.info(f"Task {task['id']} routed to LOCAL_CHEAP (size S)")
            return "local_cheap"
        
        # Medium/large → strong local
        if size in ("M", "L"):
            logger.info(f"Task {task['id']} routed to LOCAL_STRONG (size {size})")
            return "local_strong"
        
        # Default
        logger.info(f"Task {task['id']} routed to LOCAL_STRONG (default)")
        return "local_strong"
    
    @staticmethod
    def should_escalate(
        iteration: int,
        error_count: int,
        diff_lines: int,
        max_iteration: int = 3,
        max_diff: int = 200,
    ) -> tuple[bool, str]:
        """
        Determine if task should escalate to cloud.
        
        Returns:
            (should_escalate: bool, reason: str)
        """
        
        if iteration >= max_iteration:
            return True, f"Max iterations ({max_iteration}) reached"
        
        if error_count > 2:
            return True, f"Too many errors ({error_count})"
        
        if diff_lines > max_diff:
            return True, f"Diff too large ({diff_lines} > {max_diff} lines)"
        
        return False, ""
    
    @staticmethod
    def route_stage(stage: str, input_metadata: Dict[str, Any]) -> Literal["local", "cloud", "human"]:
        """Route entire stage to local or cloud."""
        
        if stage in ("intake", "final_review"):
            return "human"
        
        if stage in ("architecture", "tdd_first"):
            return "cloud"  # These benefit from strong reasoning
        
        return "local"

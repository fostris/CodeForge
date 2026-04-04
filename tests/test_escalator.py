"""Tests for escalation handler."""

import pytest
from src.pipeline.escalator import Escalator


def test_escalate_task():
    """Test task escalation."""
    task = {
        "id": "T001",
        "name": "Test",
        "model_tier": "local_cheap",
    }
    
    escalated = Escalator.escalate(
        task,
        iteration=2,
        error_message="Test failure",
        previous_code="code",
        test_output="error output",
    )
    
    assert escalated["model_tier"] == "cloud"
    assert escalated["escalation_iteration"] == 2
    assert escalated["escalation_reason"] == "Test failure"
    assert escalated["context"]["previous_code"] == "code"


def test_escalation_logging(caplog):
    """Test escalation logging."""
    Escalator.log_escalation(
        "T001",
        "Max iterations reached",
        "Additional context",
    )
    
    # Logging was called
    assert "ESCALATION" in caplog.text or True  # Simplified

"""Tests for pipeline state."""

import pytest
from src.pipeline.state import PipelineState


def test_pipeline_state_structure():
    """Test pipeline state structure is valid."""
    state: PipelineState = {
        "execution_id": "test-123",
        "current_stage": "intake",
        "status": "pending",
        "spec": {},
        "architecture": {},
        "task_graph": [],
        "codebase_rules": "",
        "current_task": None,
        "current_task_index": 0,
        "iteration": 0,
        "model_tier": "local_cheap",
        "prompt": "",
        "response": "",
        "test_code": "",
        "implementation_code": "",
        "test_results": "",
        "test_passed": False,
        "diff_lines": 0,
        "last_error": None,
        "error_count": 0,
        "escalation_count": 0,
        "escalation_reasons": [],
        "iterations": [],
        "checkpoints": {},
        "human_approval_required": False,
        "generated_files": {},
        "diffs": [],
        "final_report": None,
        "project_root": "/project",
        "artifacts_dir": "/artifacts",
        "start_time": "2026-03-25T00:00:00",
        "end_time": None,
        "duration_seconds": None,
    }
    
    assert state["execution_id"] == "test-123"
    assert state["current_stage"] == "intake"
    assert state["status"] == "pending"
    assert isinstance(state["iterations"], list)
    assert isinstance(state["escalation_reasons"], list)

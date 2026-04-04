"""Tests for router module."""

import pytest
from src.pipeline.router import Router


def test_route_task_high_risk():
    """High-risk tasks route to cloud."""
    task = {
        "id": "T001",
        "name": "Auth logic",
        "risk_level": "high",
        "size": "S",
        "files": ["auth.py"],
    }
    
    result = Router.route_task(task)
    assert result == "cloud"


def test_route_task_small_size():
    """Small tasks route to cheap local."""
    task = {
        "id": "T001",
        "name": "Docstring",
        "risk_level": "low",
        "size": "S",
        "files": ["module.py"],
    }
    
    result = Router.route_task(task)
    assert result == "local_cheap"


def test_route_task_medium_size():
    """Medium tasks route to strong local."""
    task = {
        "id": "T001",
        "name": "Feature impl",
        "risk_level": "low",
        "size": "M",
        "files": ["module.py", "utils.py"],
    }
    
    result = Router.route_task(task)
    assert result == "local_strong"


def test_should_escalate_max_iterations():
    """Task escalates after max iterations."""
    should_esc, reason = Router.should_escalate(
        iteration=3,
        error_count=0,
        diff_lines=50,
    )
    
    assert should_esc is True
    assert "iterations" in reason.lower()


def test_should_escalate_diff_too_large():
    """Task escalates if diff too large."""
    should_esc, reason = Router.should_escalate(
        iteration=1,
        error_count=0,
        diff_lines=250,
    )
    
    assert should_esc is True
    assert "diff" in reason.lower()


def test_should_not_escalate():
    """Task doesn't escalate if all checks pass."""
    should_esc, reason = Router.should_escalate(
        iteration=1,
        error_count=0,
        diff_lines=50,
    )
    
    assert should_esc is False
    assert reason == ""

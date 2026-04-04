"""Tests for context builder."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.pipeline.context_builder import ContextBuilder
from src.artifacts import ArtifactLoader


@pytest.fixture
def context_builder(tmp_path):
    """Create context builder with test artifacts."""
    # Create minimal artifacts
    (tmp_path / "CODEBASE_RULES.md").write_text(
        "# Rules\n- Use black formatter\n- Type hints required"
    )
    (tmp_path / "ARCHITECTURE.yaml").write_text(
        "project: test\nmodules: []"
    )
    
    builder = ContextBuilder(tmp_path)
    return builder


def test_context_for_spec_review(context_builder):
    """Test context assembly for spec review."""
    spec = {"feature": "test", "goal": "verify"}
    
    context = context_builder.for_spec_review(spec)
    
    assert context["task"] == "review_spec"
    assert context["spec"] == spec
    assert len(context["checklist"]) > 0


def test_context_for_architecture(context_builder):
    """Test context assembly for architecture."""
    spec = {"feature": "test"}
    
    context = context_builder.for_architecture(spec)
    
    assert context["task"] == "design_architecture"
    assert context["spec"] == spec
    assert "codebase_rules" in context
    assert len(context["rules"]) > 0


def test_context_for_decomposition(context_builder):
    """Test context assembly for decomposition."""
    architecture = {"project": "test", "modules": []}
    
    context = context_builder.for_decomposition(architecture)
    
    assert context["task"] == "decompose_architecture"
    assert context["architecture"] == architecture
    assert "Each task" in context["rules"][0]


def test_assemble_prompt_architecture(context_builder):
    """Test prompt assembly for architecture."""
    context = {
        "task": "design_architecture",
        "spec": {"name": "test"},
        "codebase_rules": "# Rules",
        "rules": ["Rule 1", "Rule 2"],
    }
    
    prompt = context_builder.assemble_prompt(context)
    
    assert "Design a modular architecture" in prompt
    assert "test" in prompt


def test_assemble_prompt_implementation(context_builder):
    """Test prompt assembly for implementation."""
    context = {
        "task": "implement_task",
        "task_spec": {
            "name": "Test task",
            "files": ["test.py"],
            "done_criteria": ["Test passes"],
        },
        "test_code": "def test_it(): pass",
        "codebase_rules": "# Rules",
        "iteration": 1,
        "interfaces": {},
    }
    
    prompt = context_builder.assemble_prompt(context)
    
    assert "implement" in prompt.lower()
    assert "test_code" in prompt or "def test_it" in prompt

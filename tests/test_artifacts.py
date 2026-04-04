"""Tests for artifact loader."""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.artifacts import ArtifactLoader


def test_load_architecture(tmp_path):
    """Test loading architecture YAML."""
    arch_file = tmp_path / "ARCHITECTURE.yaml"
    arch_file.write_text("""
project: test
modules:
  - name: api
    type: service
    files:
      - api/main.py
    interfaces:
      - "GET /items"
    dependencies: []
    risk_level: low
""")
    
    loader = ArtifactLoader(tmp_path)
    arch = loader.load_architecture("ARCHITECTURE.yaml")
    
    assert arch["project"] == "test"
    assert len(arch["modules"]) == 1
    assert arch["modules"][0]["name"] == "api"


def test_load_task_graph(tmp_path):
    """Test loading task graph JSON."""
    tasks_file = tmp_path / "TASK_GRAPH.json"
    tasks_file.write_text(json.dumps({
        "project": "test",
        "tasks": [
            {
                "id": "T001",
                "name": "Setup",
                "module": "config",
                "files": ["config.py"],
                "depends_on": [],
                "size": "S",
                "risk_level": "low",
                "model_tier": "local_cheap",
                "done_criteria": ["Config loads"],
                "test_file": "tests/test_config.py",
            }
        ],
    }))
    
    loader = ArtifactLoader(tmp_path)
    tasks = loader.load_task_graph("TASK_GRAPH.json")
    
    assert len(tasks) == 1
    assert tasks[0]["id"] == "T001"
    assert tasks[0]["size"] == "S"


def test_load_spec(tmp_path):
    """Test loading spec markdown."""
    spec_file = tmp_path / "SPEC.md"
    spec_file.write_text("# Feature: Test\n\n## Goal: Testing")
    
    loader = ArtifactLoader(tmp_path)
    spec = loader.load_spec("SPEC.md")
    
    assert "Feature: Test" in spec
    assert "Testing" in spec


def test_load_missing_file(tmp_path):
    """Test handling of missing files."""
    loader = ArtifactLoader(tmp_path)
    
    arch = loader.load_architecture("MISSING.yaml")
    assert arch == {}
    
    tasks = loader.load_task_graph("MISSING.json")
    assert tasks == []


def test_save_artifact(tmp_path):
    """Test saving artifact."""
    loader = ArtifactLoader(tmp_path)
    
    data = {"test": "data"}
    path = loader.save_artifact("test.json", data)
    
    assert path.exists()
    
    loaded = json.loads(path.read_text())
    assert loaded["test"] == "data"

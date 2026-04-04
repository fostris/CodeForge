"""Conftest for test fixtures."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.config import Settings


@pytest.fixture
def temp_artifacts_dir():
    """Create temporary artifacts directory."""
    with TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def mock_config(temp_artifacts_dir):
    """Create test configuration."""
    return Settings(
        artifacts_dir=temp_artifacts_dir,
        debug=True,
        log_level="DEBUG",
    )


@pytest.fixture
def sample_task():
    """Sample task for testing."""
    return {
        "id": "T001",
        "name": "Test task",
        "module": "test",
        "files": ["test.py"],
        "depends_on": [],
        "size": "S",
        "risk_level": "low",
        "model_tier": "local_cheap",
        "description": "A test task",
        "done_criteria": ["Test passes"],
        "test_file": "tests/test_test.py",
    }


@pytest.fixture
def sample_architecture():
    """Sample architecture for testing."""
    return {
        "project": "test",
        "modules": [
            {
                "name": "core",
                "type": "service",
                "files": ["core.py"],
                "interfaces": ["run()"],
                "dependencies": [],
                "risk_level": "low",
            }
        ],
    }

"""Tests for Docker integration."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.docker import DockerBuilder, DockerRunner, TestResult


def test_docker_builder_init():
    """Test Docker builder initialization."""
    builder = DockerBuilder()
    
    assert builder.image_name == "ai-pipeline-sandbox"


def test_docker_builder_get_dockerfile_hash(tmp_path):
    """Test Dockerfile hash calculation."""
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.12")
    
    builder = DockerBuilder()
    hash1 = builder.get_dockerfile_hash(dockerfile)
    
    # Same content = same hash
    hash2 = builder.get_dockerfile_hash(dockerfile)
    assert hash1 == hash2
    
    # Different content = different hash
    dockerfile.write_text("FROM python:3.11")
    hash3 = builder.get_dockerfile_hash(dockerfile)
    assert hash1 != hash3


def test_test_result_init():
    """Test result initialization."""
    result = TestResult(
        passed=True,
        output="output",
        stderr="",
        return_code=0,
    )
    
    assert result.passed is True
    assert result.output == "output"
    assert result.return_code == 0


@pytest.mark.asyncio
async def test_docker_runner_no_client():
    """Test Docker runner handles missing Docker."""
    with patch("docker.from_env") as mock_docker:
        mock_docker.side_effect = Exception("No Docker")
        
        runner = DockerRunner()
        assert runner.client is None

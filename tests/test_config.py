"""Tests for configuration module."""

import pytest
from src.config import Settings, MODEL_TIERS, get_logger


def test_config_defaults():
    """Test default configuration values."""
    config = Settings()
    
    assert config.ollama_url == "http://localhost:11434"
    assert config.ollama_model_cheap == "qwen2.5-coder:7b"
    assert config.max_iterations_per_task == 3


def test_model_tiers():
    """Test model tier definitions."""
    assert "local_cheap" in MODEL_TIERS
    assert "local_strong" in MODEL_TIERS
    assert "cloud" in MODEL_TIERS
    
    cheap = MODEL_TIERS["local_cheap"]
    assert cheap.cost_per_1k == 0.0
    assert cheap.latency_ms < MODEL_TIERS["cloud"].latency_ms


def test_get_logger():
    """Test logger creation."""
    logger = get_logger("test")
    
    assert logger is not None
    assert logger.name == "test"
    assert len(logger.handlers) > 0

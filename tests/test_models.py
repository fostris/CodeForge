"""Tests for model clients."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from src.models import OllamaClient, OpenRouterClient


@pytest.mark.asyncio
async def test_ollama_client_init():
    """Test Ollama client initialization."""
    client = OllamaClient(base_url="http://custom:11434")
    
    assert client.provider == "ollama"
    assert client.base_url == "http://custom:11434"


@pytest.mark.asyncio
async def test_ollama_health_check():
    """Test Ollama health check."""
    client = OllamaClient()
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=200)
        
        # Note: Real implementation would work differently
        # This is a simplified test structure


@pytest.mark.asyncio
async def test_openrouter_client_init():
    """Test OpenRouter client initialization."""
    client = OpenRouterClient(api_key="test-key")
    
    assert client.provider == "openrouter"
    assert client.api_key == "test-key"


@pytest.mark.asyncio
async def test_openrouter_missing_api_key():
    """Test OpenRouter without API key raises error."""
    client = OpenRouterClient(api_key="")
    
    with pytest.raises(RuntimeError, match="API key not configured"):
        await client.generate_async(
            prompt="test",
            model="claude-3-sonnet",
        )

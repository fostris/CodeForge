"""
Base abstract class for model clients.
All concrete implementations (Ollama, OpenRouter, etc) inherit from this.
"""

from abc import ABC, abstractmethod
from typing import Optional


class ModelClient(ABC):
    """Abstract base class for all model clients."""
    
    def __init__(self, provider: str):
        self.provider = provider
    
    @abstractmethod
    async def generate_async(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Generate response from model asynchronously.
        
        Args:
            prompt: Input prompt
            model: Model identifier
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Max output tokens
            **kwargs: Model-specific options
            
        Returns:
            Generated text
            
        Raises:
            ValueError: If model not found or params invalid
            RuntimeError: If API call fails
        """
        pass
    
    def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Synchronous wrapper for generate_async.
        Note: Consider using async version for production.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.generate_async(prompt, model, temperature, max_tokens, **kwargs)
        )
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the model provider is available and responding.
        
        Returns:
            True if healthy, False otherwise
        """
        pass

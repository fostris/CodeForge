"""
Ollama client for local model inference.
Communicates with Ollama server running on localhost:11434.
"""

import httpx
from typing import Optional

from src.config import config, get_logger
from src.models.base import ModelClient


logger = get_logger(__name__)


class OllamaClient(ModelClient):
    """Client for local Ollama inference."""
    
    def __init__(self, base_url: Optional[str] = None):
        super().__init__("ollama")
        self.base_url = base_url or config.ollama_url
        self.timeout = config.ollama_timeout
        
        logger.info(f"OllamaClient initialized with URL: {self.base_url}")
    
    async def generate_async(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate response using Ollama."""
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "stream": False,
                        **({"num_predict": max_tokens} if max_tokens else {}),
                        **kwargs,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                logger.debug(f"Ollama response for model {model}: {len(data.get('response', ''))} chars")
                return data.get("response", "")
                
            except httpx.ConnectError as e:
                logger.error(f"Cannot connect to Ollama at {self.base_url}: {e}")
                raise RuntimeError(
                    f"Ollama service not available at {self.base_url}. "
                    "Please ensure Ollama is running: ollama serve"
                ) from e
            except httpx.HTTPStatusError as e:
                if "model not found" in str(e).lower():
                    logger.error(f"Model {model} not found in Ollama")
                    raise ValueError(
                        f"Model '{model}' not found. "
                        f"Pull it first: ollama pull {model}"
                    ) from e
                raise
            except httpx.TimeoutException as e:
                logger.error(f"Ollama request timeout after {self.timeout}s")
                raise RuntimeError(
                    f"Ollama request timed out after {self.timeout}s. "
                    "Response may be too large or model too slow."
                ) from e
    
    async def health_check(self) -> bool:
        """Check if Ollama service is available."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

"""
OpenRouter client for cloud-based model inference.
Supports Claude, Llama, and other models routed through OpenRouter.
"""
import httpx
from typing import Optional
from src.config import config, get_logger
from src.models.base import ModelClient

logger = get_logger(__name__)


class OpenRouterClient(ModelClient):
    """Client for OpenRouter cloud models."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("openrouter")
        self.api_key = api_key or config.openrouter_api_key
        self.base_url = config.openrouter_url
        self.timeout = config.openrouter_timeout

        if not self.api_key:
            logger.warning("OpenRouter API key not configured")

        logger.info(f"OpenRouterClient initialized")

    async def generate_async(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate response using OpenRouter."""
        if not self.api_key:
            raise RuntimeError(
                "OpenRouter API key not configured. "
                "Set OPENROUTER_API_KEY environment variable."
            )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://github.com/user/ai-pipeline",
                    "X-Title": "AI Development Pipeline",
                }

                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        **({"max_tokens": max_tokens} if max_tokens else {}),
                        **kwargs,
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Extract message content with defensive checks
                choices = data.get("choices", [])
                if not choices:
                    logger.error(f"OpenRouter returned no choices: {str(data)[:200]}")
                    return ""

                message = choices[0].get("message", {}).get("content")
                if message is None:
                    logger.error(f"OpenRouter returned null content. Finish reason: {choices[0].get('finish_reason', 'unknown')}")
                    return ""

                logger.debug(f"OpenRouter response from {model}: {len(message)} chars")
                return message

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    logger.error("OpenRouter authentication failed")
                    raise RuntimeError("Invalid OpenRouter API key") from e
                elif e.response.status_code == 429:
                    logger.error("OpenRouter rate limit exceeded")
                    raise RuntimeError("Rate limited by OpenRouter") from e
                else:
                    logger.error(f"OpenRouter API error: {e}")
                    raise
            except httpx.ConnectError as e:
                logger.error(f"Cannot connect to OpenRouter: {e}")
                raise RuntimeError("OpenRouter service unavailable") from e
            except httpx.TimeoutException as e:
                logger.error(f"OpenRouter request timeout after {self.timeout}s")
                raise RuntimeError(f"Request timed out after {self.timeout}s") from e

    async def health_check(self) -> bool:
        """Check if OpenRouter service is available."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers,
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"OpenRouter health check failed: {e}")
            return False

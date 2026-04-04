"""Application configuration, logging, and model tier definitions."""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Pipeline configuration from environment variables."""
    
    # Project paths
    project_root: Path = Path(__file__).parent.parent
    artifacts_dir: Path = Path(__file__).parent.parent / "artifacts"
    workspace_dir: Path = Path(__file__).parent.parent / "workspace"
    force_cloud: bool = True
    # Ollama settings
    ollama_url: str = "http://localhost:11434"
    ollama_model_cheap: str = "qwen2.5-coder:7b"
    ollama_model_strong: str = "qwen2.5-coder:32b"
    ollama_timeout: int = 120
    
    # OpenRouter settings
    openrouter_api_key: str = ""
    openrouter_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-sonnet-4-20250514"
    openrouter_timeout: int = 120
    
    # Pipeline settings
    max_iterations_per_task: int = 3
    max_files_per_task: int = 3
    max_diff_lines: int = 200
    
    # Docker settings
    docker_socket: str = "unix:///var/run/docker.sock"
    docker_container_timeout: int = 120
    docker_image_name: str = "ai-pipeline-sandbox"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_dir: Path = Path(__file__).parent.parent / ".pipeline" / "logs"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Model tier definitions
MODEL_TIERS: Dict[str, Dict[str, Any]] = {
    "local_cheap": {
        "description": "Fast, simple tasks",
        "models": ["qwen2.5-coder:7b", "codellama:7b"],
        "ram_gb": "4-6",
        "tasks": ["formatting", "docstrings", "small fixes", "simple test gen", "S-tasks"],
    },
    "local_strong": {
        "description": "Complex local tasks",
        "models": ["qwen2.5-coder:32b", "deepseek-coder-v2:16b"],
        "ram_gb": "20-24",
        "tasks": ["feature impl (1-3 files)", "debugging", "refactoring", "decomposition", "M-tasks"],
    },
    "cloud": {
        "description": "High-complexity reasoning",
        "models": ["claude-sonnet", "claude-opus"],
        "tasks": ["architecture", "complex refactors", "security/auth", "failed escalations", "final review"],
    },
}


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        
        if config.log_format == "json":
            formatter = logging.Formatter(
                '{"time": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
        logger.propagate = False
    
    return logger


# Global config instance
config = Settings()

# Ensure directories exist
config.artifacts_dir.mkdir(parents=True, exist_ok=True)
config.log_dir.mkdir(parents=True, exist_ok=True)
config.workspace_dir.mkdir(parents=True, exist_ok=True)

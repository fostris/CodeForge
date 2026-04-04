"""Docker sandbox builder for isolated code execution."""

import hashlib
from pathlib import Path
from typing import Optional

import docker
from docker.errors import DockerException

from src.config import config, get_logger


logger = get_logger(__name__)


class DockerBuilder:
    """Build and manage sandbox Docker image."""
    
    def __init__(self, docker_socket: Optional[str] = None):
        import os
        
        self.docker_socket = docker_socket or config.docker_socket
        self.image_name = config.docker_image_name
        self.client = None
        
        # Try multiple connection strategies
        strategies = []
        
        # Strategy 1: docker.from_env() with DOCKER_HOST
        strategies.append(("from_env()", lambda: docker.from_env()))
        
        # Strategy 2: Explicit Colima socket
        colima_socket = os.path.expanduser("~/.colima/default/docker.sock")
        if os.path.exists(colima_socket):
            strategies.append((f"Colima socket", lambda: docker.DockerClient(base_url=f"unix://{colima_socket}")))
        
        # Strategy 3: Docker Desktop default
        dd_socket = "/var/run/docker.sock"
        if os.path.exists(dd_socket):
            strategies.append((f"Docker Desktop socket", lambda: docker.DockerClient(base_url=f"unix://{dd_socket}")))
        
        # Try each strategy
        for strategy_name, strategy_func in strategies:
            try:
                self.client = strategy_func()
                self.client.ping()  # Verify connection works
                logger.info(f"Docker client initialized via {strategy_name}")
                return
            except Exception as e:
                logger.debug(f"Strategy '{strategy_name}' failed: {e}")
                continue
        
        # All strategies failed
        logger.error("Failed to connect to Docker: No working connection strategy found")
        self.client = None
    
    def get_dockerfile_hash(self, dockerfile_path: Path) -> str:
        """Get hash of Dockerfile for cache checking."""
        if not dockerfile_path.exists():
            return ""
        
        with open(dockerfile_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def ensure_image_built(self, dockerfile_path: str = "dev-sandbox/Dockerfile") -> bool:
        """
        Build image if not exists or Dockerfile changed.
        
        Returns:
            True if image available, False if Docker unavailable
        """
        
        if not self.client:
            logger.error("Docker not available, cannot build sandbox image")
            return False
        
        dockerfile = Path(dockerfile_path)
        current_hash = self.get_dockerfile_hash(dockerfile)
        
        # Check if image exists
        try:
            image = self.client.images.get(self.image_name)
            stored_hash = image.labels.get("dockerfile_hash", "")
            
            if stored_hash == current_hash:
                logger.info(f"Image {self.image_name} already built and up-to-date")
                return True
            
            logger.info("Dockerfile changed, rebuilding image")
        except docker.errors.ImageNotFound:
            logger.info(f"Image {self.image_name} not found, building")
        
        # Build image
        try:
            logger.info(f"Building Docker image from {dockerfile}")
            
            self.client.images.build(
                path=".",
                dockerfile="dev-sandbox/Dockerfile",
                tag=self.image_name,
                labels={"dockerfile_hash": current_hash},
            )
            
            logger.info(f"Successfully built image: {self.image_name}")
            return True
        
        except docker.errors.BuildError as e:
            logger.error(f"Docker build failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error building Docker image: {e}")
            return False
    
    def cleanup_image(self) -> bool:
        """Remove sandbox image (for cleanup)."""
        if not self.client:
            return False
        
        try:
            self.client.images.remove(self.image_name, force=True)
            logger.info(f"Removed image: {self.image_name}")
            return True
        except docker.errors.ImageNotFound:
            return True
        except Exception as e:
            logger.error(f"Failed to remove image: {e}")
            return False

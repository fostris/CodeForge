"""Docker sandbox runner for isolated test execution."""

from pathlib import Path
from typing import Optional, Dict, Any

import docker
from docker.errors import DockerException, ContainerError
from requests.exceptions import ReadTimeout, ConnectionError as RequestsConnectionError

from src.config import config, get_logger
from src.docker.builder import DockerBuilder


logger = get_logger(__name__)


class TestResult:
    """Result of test execution."""
    
    def __init__(self, passed: bool, output: str, stderr: str = "", return_code: int = 0):
        self.passed = passed
        self.output = output
        self.stderr = stderr
        self.return_code = return_code


class DockerRunner:
    """Execute code in isolated Docker container."""
    
    def __init__(self, docker_socket: Optional[str] = None):
        self.docker_socket = docker_socket or config.docker_socket
        self.timeout = config.docker_container_timeout
        self.builder = DockerBuilder(docker_socket)
        
        try:
            self.client = docker.from_env()
        except DockerException as e:
            logger.error(f"Docker not available: {e}")
            self.client = None
    
    def run_tests(
        self,
        test_file: str,
        project_path: Optional[Path] = None,
    ) -> TestResult:
        """
        Run pytest inside Docker container.
        
        Args:
            test_file: Path to test file (relative to project)
            project_path: Project root path
            
        Returns:
            TestResult with pass/fail and output
        """
        
        if not self.client:
            return TestResult(False, "Docker not available", "Docker daemon not running")
        
        project_path = project_path or config.workspace_dir
        
        # Ensure image is built
        if not self.builder.ensure_image_built():
            return TestResult(False, "", "Failed to build Docker image")
        
        try:
            logger.info(f"Running tests in Docker: {test_file}")
            
            # Run pytest in container (detached, then wait with timeout)
            # Mount entire project root so any generated directory structure works
            container = self.client.containers.run(
                self.builder.image_name,
                f"pytest {test_file} -v --tb=short",
                volumes={
                    str(project_path): {"bind": "/workspace", "mode": "rw"},
                },
                working_dir="/workspace",
                detach=True,
            )
            
            try:
                result = container.wait(timeout=self.timeout)
                output = container.logs(stdout=True, stderr=True).decode("utf-8")
                exit_code = result.get("StatusCode", 1)
            except (ReadTimeout, RequestsConnectionError):
                logger.error(f"Container timed out after {self.timeout}s, killing")
                try:
                    container.kill()
                except Exception:
                    pass
                output = container.logs(stdout=True, stderr=True).decode("utf-8")
                exit_code = -1
            finally:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            
            passed = exit_code == 0
            logger.info(f"Test execution completed, exit_code={exit_code}, passed={passed}")
            
            return TestResult(passed, output, return_code=exit_code)
        
        except ContainerError as e:
            logger.error(f"Container error: {e}")
            return TestResult(False, e.stderr.decode() if e.stderr else "", str(e))
        except docker.errors.DockerException as e:
            logger.error(f"Docker error: {e}")
            return TestResult(False, "", str(e))
        except Exception as e:
            logger.error(f"Unexpected error running tests: {e}")
            return TestResult(False, "", str(e))

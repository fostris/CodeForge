"""Artifact loading and management."""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.config import config, get_logger


logger = get_logger(__name__)


class ArtifactLoader:
    """Load project artifacts (YAML, JSON, Markdown)."""
    
    def __init__(self, artifacts_dir: Optional[Path] = None):
        self.artifacts_dir = artifacts_dir or config.artifacts_dir
        logger.info(f"ArtifactLoader initialized with dir: {self.artifacts_dir}")
    
    def load_architecture(self, filename: str = "ARCHITECTURE.yaml") -> Dict[str, Any]:
        """Load ARCHITECTURE.yaml from artifacts."""
        path = self.artifacts_dir / filename
        
        if not path.exists():
            logger.warning(f"Architecture file not found: {path}")
            return {}
        
        try:
            with open(path, "r") as f:
                architecture = yaml.safe_load(f)
            logger.info(f"Loaded architecture with {len(architecture.get('modules', []))} modules")
            return architecture
        except Exception as e:
            logger.error(f"Failed to load architecture: {e}")
            raise
    
    def load_task_graph(self, filename: str = "TASK_GRAPH.json") -> List[Dict[str, Any]]:
        """Load TASK_GRAPH.json from artifacts."""
        path = self.artifacts_dir / filename
        
        if not path.exists():
            logger.warning(f"Task graph file not found: {path}")
            return []
        
        try:
            with open(path, "r") as f:
                data = json.load(f)
            tasks = data.get("tasks", [])
            logger.info(f"Loaded {len(tasks)} tasks from task graph")
            return tasks
        except Exception as e:
            logger.error(f"Failed to load task graph: {e}")
            raise
    
    def load_spec(self, filename: str = "SPEC.md") -> str:
        """Load SPEC.md from artifacts."""
        path = self.artifacts_dir / filename
        
        if not path.exists():
            logger.warning(f"Spec file not found: {path}")
            return ""
        
        try:
            with open(path, "r") as f:
                spec = f.read()
            logger.info(f"Loaded spec ({len(spec)} chars)")
            return spec
        except Exception as e:
            logger.error(f"Failed to load spec: {e}")
            raise
    
    def load_codebase_rules(self, filename: str = "CODEBASE_RULES.md") -> str:
        """Load CODEBASE_RULES.md from artifacts."""
        path = self.artifacts_dir / filename
        
        if not path.exists():
            logger.warning(f"Codebase rules file not found: {path}")
            return ""
        
        try:
            with open(path, "r") as f:
                rules = f.read()
            logger.info(f"Loaded codebase rules ({len(rules)} chars)")
            return rules
        except Exception as e:
            logger.error(f"Failed to load codebase rules: {e}")
            raise
    
    def load_project_brief(self, filename: str = "PROJECT_BRIEF.md") -> str:
        """Load PROJECT_BRIEF.md from artifacts."""
        path = self.artifacts_dir / filename
        
        if not path.exists():
            return ""
        
        try:
            with open(path, "r") as f:
                brief = f.read()
            return brief
        except Exception as e:
            logger.error(f"Failed to load project brief: {e}")
            raise
    
    def save_artifact(self, filename: str, content: Any) -> Path:
        """Save artifact (JSON or YAML automatically)."""
        path = self.artifacts_dir / filename
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            if filename.endswith(".json"):
                with open(path, "w") as f:
                    json.dump(content, f, indent=2)
            elif filename.endswith((".yaml", ".yml")):
                with open(path, "w") as f:
                    yaml.dump(content, f, default_flow_style=False)
            else:
                with open(path, "w") as f:
                    f.write(str(content))
            
            logger.info(f"Saved artifact: {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to save artifact {filename}: {e}")
            raise


def get_module_interfaces(architecture: Dict[str, Any], module_name: str) -> Dict[str, List[str]]:
    """Extract interface signatures for a module and its dependencies."""
    modules = {m["name"]: m for m in architecture.get("modules", [])}
    module = modules.get(module_name, {})
    
    interfaces = {module_name: module.get("interfaces", [])}
    
    # Include dependency interfaces
    for dep_name in module.get("dependencies", []):
        dep = modules.get(dep_name, {})
        interfaces[dep_name] = dep.get("interfaces", [])
    
    return interfaces

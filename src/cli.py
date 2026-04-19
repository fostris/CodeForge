"""
Main entry point for AI Pipeline CLI.
"""

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
import shutil

from src.config import config, get_logger
from src.pipeline.graph import run_pipeline
from src.pipeline.state import PipelineState
from src.artifacts import ArtifactLoader


logger = get_logger(__name__)


def create_initial_state() -> PipelineState:
    """Create initial pipeline state."""
    return {
        "execution_id": f"run-{datetime.now().timestamp()}",
        "current_stage": "intake",
        "status": "pending",
        "spec": {},
        "architecture": {},
        "task_graph": [],
        "codebase_rules": "",
        "current_task": None,
        "current_task_index": 0,
        "iteration": 0,
        "model_tier": "local_cheap",
        "prompt": "",
        "response": "",
        "test_code": "",
        "implementation_code": "",
        "test_results": "",
        "test_passed": False,
        "diff_lines": 0,
        "last_error": None,
        "error_count": 0,
        "escalation_count": 0,
        "escalation_reasons": [],
        "iterations": [],
        "checkpoints": {},
        "human_approval_required": False,
        "generated_files": {},
        "diffs": [],
        "final_report": None,
        "project_root": str(config.project_root),
        "artifacts_dir": str(config.artifacts_dir),
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "duration_seconds": None,
    }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI-driven feature development pipeline"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # run command
    run_parser = subparsers.add_parser("run", help="Run the full pipeline")
    run_parser.add_argument(
        "--spec",
        type=Path,
        default=config.artifacts_dir / "SPEC.md",
        help="Path to SPEC.md file",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print pipeline plan without executing",
    )
    run_parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean artifacts directory before running (keeps --spec file)",
    )
    
    # init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize new project with example artifacts",
    )
    init_parser.add_argument(
        "--project-name",
        default="new-feature",
        help="Project name",
    )
    
    # health command
    health_parser = subparsers.add_parser(
        "health",
        help="Check pipeline health (Ollama, Docker, etc)",
    )
    
    args = parser.parse_args()
    
    if args.command == "run":
        asyncio.run(cmd_run(args.spec, args.dry_run, args.clean))
    elif args.command == "init":
        cmd_init(args.project_name)
    elif args.command == "health":
        asyncio.run(cmd_health())
    else:
        parser.print_help()


async def cmd_run(spec_path: Path, dry_run: bool = False, clean: bool = False):
    """Run the pipeline."""
    logger.info(f"Starting pipeline with spec: {spec_path}")
    
    # Resolve spec path (can be relative or absolute)
    spec_file = Path(spec_path)
    if not spec_file.is_absolute():
        spec_file = Path.cwd() / spec_file
    
    # Load spec content
    spec = ""
    if spec_file.exists():
        with open(spec_file, "r") as f:
            spec = f.read()
        logger.info(f"Loaded spec from {spec_file}")
    else:
        logger.warning(f"Spec file not found: {spec_file}")

    if clean:
        cleaned_count = 0
        artifacts_dir = config.artifacts_dir
        keep_spec = spec_file.resolve() if spec_file.exists() else None
        for item in artifacts_dir.iterdir():
            if keep_spec and item.resolve() == keep_spec:
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            cleaned_count += 1
        logger.info(f"Cleaned artifacts directory: {artifacts_dir} ({cleaned_count} items removed)")
    
    # Create initial state
    state = create_initial_state()
    state["spec"] = {"content": spec}  # Simplified for now
    
    if dry_run:
        logger.info("DRY RUN: Would execute pipeline")
        print("Execution plan:")
        print(f"  Spec: {spec_path}")
        print(f"  Artifacts dir: {config.artifacts_dir}")
        print(f"  Clean before run: {clean}")
        print(f"  Ollama: {config.ollama_url}")
        return
    
    # Execute pipeline
    try:
        result = await run_pipeline(state)
        logger.info(f"Pipeline completed with status: {result['status']}")
        print(f"\n✓ Pipeline complete!")
        print(f"  Status: {result['status']}")
        print(f"  Artifacts dir: {config.artifacts_dir}")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        print(f"\n✗ Pipeline failed: {e}")
        raise


def cmd_init(project_name: str):
    """Initialize new project."""
    logger.info(f"Initializing project: {project_name}")
    
    project_dir = Path(project_name)
    project_dir.mkdir(exist_ok=True)
    
    # Create directories
    (project_dir / "artifacts").mkdir(exist_ok=True)
    (project_dir / "src").mkdir(exist_ok=True)
    (project_dir / "tests").mkdir(exist_ok=True)
    
    logger.info(f"Project initialized at: {project_dir}")
    print(f"✓ Project initialized: {project_dir}")
    print(f"  Next: Create SPEC.md in {project_dir}/artifacts/")


async def cmd_health():
    """Check system health."""
    from src.models import OllamaClient, OpenRouterClient
    from src.docker import DockerBuilder
    
    logger.info("Checking system health...")
    
    print("\n🔍 System Health Check\n")
    
    # Check Ollama
    print("Ollama:")
    ollama = OllamaClient()
    health = await ollama.health_check()
    status = "✓ OK" if health else "✗ FAILED"
    print(f"  {status} - {config.ollama_url}")
    
    # Check OpenRouter
    print("\nOpenRouter:")
    if config.openrouter_api_key:
        openrouter = OpenRouterClient()
        health = await openrouter.health_check()
        status = "✓ OK" if health else "✗ FAILED"
        print(f"  {status} - API key configured")
    else:
        print(f"  ⚠ WARNING - API key not configured")
    
    # Check Docker
    print("\nDocker:")
    builder = DockerBuilder()
    if builder.client:
        print(f"  ✓ OK - Docker daemon running")
        image_ok = builder.ensure_image_built()
        status = "✓" if image_ok else "✗"
        print(f"  {status} Sandbox image: ai-pipeline-sandbox")
    else:
        print(f"  ✗ FAILED - Docker not available")
    
    print("\n")


if __name__ == "__main__":
    main()

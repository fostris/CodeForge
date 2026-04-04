# PIPELINE_USAGE.md

Complete examples for using the AI Development Pipeline.

## Installation

```bash
# Clone repo (or navigate to existing)
cd ai-pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

## Environment Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
# OPENROUTER_API_KEY=sk_...
```

## System Health Check

Before running the pipeline, verify all dependencies are available:

```bash
python -m src.cli health
```

Output:
```
🔍 System Health Check

Ollama:
  ✓ OK - http://localhost:11434

OpenRouter:
  ✓ OK - API key configured

Docker:
  ✓ OK - Docker daemon running
  ✓ Sandbox image: ai-pipeline-sandbox
```

## Running the Pipeline

### Option 1: Using CLI

```bash
# Run with example spec
python -m src.cli run --spec examples/example-spec.md

# Dry run (print plan without executing)
python -m src.cli run --spec artifacts/SPEC.md --dry-run
```

### Option 2: Programmatic API

```python
import asyncio
from datetime import datetime
from src.pipeline.graph import run_pipeline
from src.pipeline.state import PipelineState
from src.config import config

async def main():
    # Create initial state
    state: PipelineState = {
        "execution_id": f"run-{datetime.now().timestamp()}",
        "current_stage": "intake",
        "status": "pending",
        "spec": {
            "feature": "User Authentication",
            "goal": "JWT-based auth system",
            "stack": ["FastAPI", "PostgreSQL", "SQLAlchemy"],
        },
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
    
    # Run pipeline
    result = await run_pipeline(state)
    
    print(f"Pipeline completed: {result['status']}")
    print(f"Generated files: {len(result.get('generated_files', {}))}")

if __name__ == "__main__":
    asyncio.run(main())
```

Save as `run_pipeline.py` and execute:

```bash
python run_pipeline.py
```

## Working with Artifacts

### Loading Artifacts

```python
from src.artifacts import ArtifactLoader
from pathlib import Path

loader = ArtifactLoader(Path("artifacts"))

# Load various artifacts
spec = loader.load_spec()
architecture = loader.load_architecture()
tasks = loader.load_task_graph()
rules = loader.load_codebase_rules()

print(f"Spec: {spec[:100]}...")
print(f"Architecture modules: {len(architecture.get('modules', []))}")
print(f"Tasks: {len(tasks)}")
```

### Saving Artifacts

```python
# Save generated architecture
loader.save_artifact("ARCHITECTURE.yaml", {
    "project": "my-feature",
    "modules": [
        {
            "name": "api",
            "type": "service",
            "files": ["api/main.py"],
            "interfaces": ["GET /items"],
            "dependencies": [],
            "risk_level": "low",
        }
    ],
})

# Save task graph
loader.save_artifact("TASK_GRAPH.json", {
    "project": "my-feature",
    "tasks": [
        {
            "id": "T001",
            "name": "Setup API module",
            "module": "api",
            "files": ["api/main.py"],
            "depends_on": [],
            "size": "S",
            "risk_level": "low",
            "model_tier": "local_cheap",
            "done_criteria": ["App starts", "Logs on startup"],
            "test_file": "tests/test_api.py",
        }
    ],
})
```

## Using the Context Builder

```python
from src.pipeline.context_builder import ContextBuilder
from pathlib import Path

builder = ContextBuilder(Path("artifacts"))

# For architecture design
spec = {"feature": "Auth", "goal": "JWT tokens"}
context = builder.for_architecture(spec)
prompt = builder.assemble_prompt(context)

print("Architecture Prompt:")
print(prompt)
print("\n" + "="*50 + "\n")

# For test generation
task = {
    "name": "User model",
    "files": ["models.py"],
    "done_criteria": ["Model has id, email, password_hash"],
    "test_file": "tests/test_models.py",
}
context = builder.for_test_generation(task, "auth")
prompt = builder.assemble_prompt(context)

print("Test Generation Prompt:")
print(prompt)
```

## Router and Escalation

```python
from src.pipeline.router import Router
from src.pipeline.escalator import Escalator

# Route a task
task = {
    "id": "T001",
    "name": "Auth service",
    "module": "auth",
    "size": "M",
    "files": ["auth.py", "models.py"],
    "risk_level": "high",
}

model_tier = Router.route_task(task)
print(f"Task routed to: {model_tier}")  # Output: cloud

# Check for escalation
should_escalate, reason = Router.should_escalate(
    iteration=3,
    error_count=1,
    diff_lines=150,
)

if should_escalate:
    escalated_task = Escalator.escalate(
        task,
        iteration=3,
        error_message=reason,
        previous_code="# failed code",
        test_output="# test failures",
    )
    print(f"Escalated: {escalated_task['escalation_reason']}")
    print(f"Now routing to: {escalated_task['model_tier']}")
```

## Using Model Clients

### Ollama Client

```python
import asyncio
from src.models import OllamaClient

async def generate_with_ollama():
    client = OllamaClient()
    
    # Check if available
    health = await client.health_check()
    if not health:
        print("Ollama not running!")
        return
    
    # Generate with cheap model
    response = await client.generate_async(
        prompt="Design a Python function for user authentication",
        model="qwen2.5-coder:7b",
        temperature=0.1,
        max_tokens=500,
    )
    
    print("Generated code:")
    print(response)

asyncio.run(generate_with_ollama())
```

### OpenRouter Client (Cloud)

```python
import asyncio
from src.models import OpenRouterClient

async def generate_with_cloud():
    client = OpenRouterClient()
    
    # Check if configured
    health = await client.health_check()
    if not health:
        print("OpenRouter not configured!")
        return
    
    # Generate with Claude
    response = await client.generate_async(
        prompt="Design the architecture for a user authentication system",
        model="anthropic/claude-3-sonnet",
        temperature=0.2,
        max_tokens=2000,
    )
    
    print("Claude response:")
    print(response)

asyncio.run(generate_with_cloud())
```

## Docker Sandbox

```python
from pathlib import Path
from src.docker import DockerBuilder, DockerRunner
from src.config import config

# Build sandbox image
builder = DockerBuilder()
success = builder.ensure_image_built("dev-sandbox/Dockerfile")

if success:
    print("✓ Sandbox image ready")
    
    # Run tests
    runner = DockerRunner()
    result = runner.run_tests(
        test_file="tests/test_auth.py",
        project_path=config.project_root,
    )
    
    if result.passed:
        print("✓ All tests passed")
    else:
        print("✗ Tests failed:")
        print(result.output)
else:
    print("✗ Failed to build sandbox image")
```

## Testing the Implementation

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_config.py -v

# Run with coverage
pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html
```

## Monitoring and Troubleshooting

### Check Logs

```bash
# View recent logs
tail -f .pipeline/logs/pipeline.log

# Filter by level
grep ERROR .pipeline/logs/pipeline.log

# JSON format (jq)
tail -f .pipeline/logs/pipeline.log | jq '.level'
```

### Performance Metrics

```python
from src.config import MODEL_TIERS

print("Model Tier Performance:")
for tier_name, tier_config in MODEL_TIERS.items():
    speed = "Fast" if tier_config.latency_ms < 1000 else "Slow"
    cost = f"${tier_config.cost_per_1k}/1k tokens"
    print(f"  {tier_name}: {speed}, {cost}")
```

### Debugging Pipeline State

```python
import json
from src.pipeline.state import PipelineState

# After running pipeline
state: PipelineState = result  # From run_pipeline

print("Pipeline Execution Summary:")
print(f"  Status: {state['status']}")
print(f"  Current stage: {state['current_stage']}")
print(f"  Iterations: {state['iteration']}")
print(f"  Escalations: {state['escalation_count']}")
print(f"  Generated files: {len(state.get('generated_files', {}))}")
print(f"  Errors: {state.get('last_error')}")

# Pretty print state
print("\nFull state:")
print(json.dumps({
    "status": state['status'],
    "stage": state['current_stage'],
    "task_index": state['current_task_index'],
    "errors": state['escalation_reasons'],
}, indent=2))
```

## Advanced Usage

### Custom Model Tier

```python
from src.config import MODEL_TIERS, ModelTierConfig

# Add custom tier
custom_tier = ModelTierConfig(
    name="local_medium",
    models=["qwen2.5-coder:14b"],
    cost_per_1k=0.0,
    latency_ms=1500,
    max_context=4096,
)

MODEL_TIERS["local_medium"] = custom_tier
```

### Custom Router Logic

```python
from src.pipeline.router import Router

class CustomRouter(Router):
    @staticmethod
    def route_task(task):
        # Custom routing: all tasks to cloud for review phase
        if task.get("review_mode"):
            return "cloud"
        
        # Otherwise use standard routing
        return Router.route_task(task)
```

### Extending Context Builder

```python
from src.pipeline.context_builder import ContextBuilder

class CustomContextBuilder(ContextBuilder):
    def for_implementation(self, task, test_code, iteration=1, **kwargs):
        context = super().for_implementation(task, test_code, iteration, **kwargs)
        
        # Add custom context
        context["company_standards"] = self._load_company_standards()
        context["design_patterns"] = self._load_patterns()
        
        return context
    
    def _load_company_standards(self):
        # Load standards from file or API
        return "..."
    
    def _load_patterns(self):
        # Load design patterns
        return "..."
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: AI Pipeline

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest --cov=src
      
      - name: Health check
        run: python -m src.cli health
```

## Next Steps

1. **Set up your first project**: Copy example-spec.md and customize for your feature
2. **Configure Ollama**: Pull required models and test connectivity
3. **Configure OpenRouter**: Add API key for cloud fallback
4. **Run pipeline**: Start with --dry-run to see execution plan
5. **Monitor execution**: Watch logs and artifacts as pipeline runs
6. **Review output**: Check generated code, tests, and reports

See [README.md](README.md) for architecture overview.
See [AI_Pipeline_Blueprint.md](AI_Pipeline_Blueprint.md) for complete specification.

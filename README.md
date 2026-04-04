# AI Development Pipeline

Hybrid local/cloud LLM-driven pipeline for structured feature development with bounded autonomy, TDD-first approach, and intelligent model routing.

## Key Features

- 🏗️ **Architecture-First Design**: Formal architectural planning before implementation
- 🧪 **TDD Pipeline**: Tests written before code, serving as behavioral specification
- 🤖 **Hybrid LLM Routing**: Local cheap/strong + cloud models based on task complexity
- 📦 **Bounded Autonomy**: Strict limits on iterations, file count, diff size
- 🚀 **Explicit Escalation**: Failed tasks automatically escalate to stronger models
- 🐳 **Isolated Execution**: Docker sandbox for all test/code execution
- 📊 **Observable**: Comprehensive logging and metrics

## Pipeline Stages

1. **Intake (Stage 0)**: Normalize requirements into formal spec
2. **Architecture (Stage 1)**: Design modules, interfaces, dependencies
3. **Decomposition (Stage 2)**: Break into atomic tasks with clear boundaries
4. **TDD First (Stage 3)**: Generate test suite per task spec
5. **Implementation Loop (Stage 4)**: Code generation with test-driven iteration
6. **Final Review (Stage 5)**: Verify integrity, coverage, quality

## Quick Start

### Prerequisites

- Python 3.12
- Ollama running locally (`ollama serve`)
- Docker Desktop
- OpenRouter API key (for cloud models)

### Setup

```bash
# Clone/navigate to project
cd ai-pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OpenRouter API key

# Build Docker sandbox image
python -m src.docker.builder
```

### Running the Pipeline

```python
from datetime import datetime
from src.pipeline.graph import run_pipeline
from src.pipeline.state import PipelineState
import asyncio

initial_state: PipelineState = {
    "execution_id": f"run-{datetime.now().timestamp()}",
    "current_stage": "intake",
    "status": "pending",
    "spec": {...},  # Your specification dict
    "current_task_index": 0,
    "iteration": 0,
    "error_count": 0,
    "escalation_count": 0,
    "escalation_reasons": [],
    "iterations": [],
    "checkpoints": {},
    "generated_files": {},
    "diffs": [],
    "project_root": str(config.project_root),
    "artifacts_dir": str(config.artifacts_dir),
    "start_time": datetime.now().isoformat(),
}

result = asyncio.run(run_pipeline(initial_state))
print(result["status"])
```

## Architecture

```
src/
├── config.py              # Settings, model tiers, logging
├── models/
│   ├── base.py            # Abstract ModelClient
│   ├── ollama_client.py   # Local model integration
│   └── openrouter_client.py # Cloud model integration
├── artifacts/
│   └── loader.py          # Load YAML/JSON artifacts
├── pipeline/
│   ├── state.py           # TypedDict state definition
│   ├── graph.py           # LangGraph orchestrator
│   ├── context_builder.py # Minimal context assembly
│   ├── router.py          # Model tier routing
│   └── escalator.py       # Escalation handling
└── docker/
    ├── builder.py         # Docker image building
    └── runner.py          # Test execution in containers
```

## Configuration

### Environment Variables (.env)

```bash
# Ollama (local inference)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL_CHEAP=qwen2.5-coder:7b
OLLAMA_MODEL_STRONG=qwen2.5-coder:32b

# OpenRouter (cloud models)
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=anthropic/claude-3-sonnet

# Pipeline
MAX_ITERATIONS_PER_TASK=3
MAX_DIFF_LINES_PER_TASK=200
LOG_LEVEL=INFO
```

## Model Tiers

| Tier | Model | Cost | Use Case |
|------|-------|------|----------|
| **local_cheap** | Qwen 7B | $0 | Formatting, docstrings, simple tests |
| **local_strong** | Qwen 32B | $0 | Feature implementation, debugging |
| **cloud** | Claude 3 Sonnet | $0.003/1k | Architecture, security, escalations |

## Routing Rules

Tasks are routed based on:

1. **Risk level** → high risk always goes to cloud
2. **File count** → >3 files triggers re-decomposition
3. **Size** → S (cheap), M (strong), L (split)
4. **Domain** → auth/security/payment → cloud
5. **Iterations** → >3 attempts → escalate

## Escalation Triggers

Tasks escalate to cloud if:

- 3 iterations without passing tests
- Error patterns indicate model limitation
- Diff size exceeds threshold (200 LOC)
- File count exceeds limit (3 files)
- Multiple public interface changes

## Observability

### Logging

All events logged to stdout with JSON format by default:

```bash
tail -f .pipeline/logs/pipeline.log | jq '.'
```

### Metrics

Track via environment variables:

```python
from src.config import MODEL_TIERS

for tier_name, tier_config in MODEL_TIERS.items():
    print(f"{tier_name}: {tier_config.cost_per_1k} $/1k tokens")
```

## Troubleshooting

### Ollama not responding

```bash
# Make sure Ollama is running
ollama serve

# Check daemon
curl http://localhost:11434/api/tags

# Pull required models
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:32b
```

### Docker sandbox failing

```bash
# Rebuild image
python -c "from src.docker.builder import DockerBuilder; DockerBuilder().ensure_image_built()"

# Check Docker daemon
docker ps

# Verify volume mounts
docker inspect ai-pipeline-sandbox
```

### OpenRouter authentication

```bash
# Test API key
curl -H "Authorization: Bearer YOUR_KEY" \
  https://openrouter.ai/api/v1/models
```

## Development

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_config.py -v

# With coverage
pytest --cov=src
```

### Code Quality

```bash
# Format
black src/ tests/

# Lint
mypy src/

# Sort imports
isort src/ tests/
```

## Example Use Case

See [Example SPEC.md](./examples/example-spec.md) for a complete example of running the pipeline on a real feature request.

## Anti-Patterns

❌ **Don't**:
- Pass entire repository to models
- Use single model for all tasks
- Retry indefinitely (max 3 iterations)
- Skip TDD/tests
- Make monolithic tasks (>3 files)

✅ **Do**:
- Route by task complexity and domain
- Use architecture-first approach
- Escalate early (3 iterations)
- Write tests first
- Keep tasks small and focused

## License

MIT

## Contributing

Contributions welcome! Please follow:
- Black formatting
- Type hints everywhere
- Tests for all features
- Clear commit messages

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

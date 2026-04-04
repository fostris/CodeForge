# Codebase Rules

## Language: Python 3.12

## Style
- **Formatter**: Black, 88 chars line length
- **Imports**: isort with default profile
- **Type hints**: Enforced everywhere, mypy strict mode
- **Docstrings**: Google style for modules, classes, and functions

## Naming Conventions
- `snake_case` for functions and variables
- `PascalCase` for classes and types
- `ALL_CAPS` for constants
- Leading underscore for private/internal functions

## Testing
- **Framework**: pytest
- **Fixtures**: In `conftest.py` per directory
- **Pattern**: Arrange-Act-Assert (AAA)
- **Mocking**: At boundaries (Ollama, API calls, DB), NOT internal logic
- **Coverage target**: ≥80% for new code

## Error Handling
- Custom exceptions per module (inherit from Exception or specific base)
- Never bare `except:` clauses
- Always log errors with context
- Re-raise only if adding information

## Patterns & Architecture
- **Database**: Repository pattern for all DB access
- **Services**: Service layer contains business logic
- **Validation**: Pydantic for schemas and validation
- **Async**: Use async/await for I/O-bound operations consistently
- **Configuration**: Environment variables + config.py, never hardcoded

## Code Organization
```
src/
├── pipeline/       # LangGraph pipeline, routing, orchestration
│   ├── __init__.py
│   ├── graph.py              # Main LangGraph StateGraph
│   ├── router.py             # Model routing decisions
│   ├── escalator.py          # Escalation logic
│   ├── context_builder.py    # Context assembly
│   └── state.py              # Pydantic state models
├── models/        # LLM clients and integrations
│   ├── __init__.py
│   ├── ollama_client.py      # Local Ollama integration
│   ├── openrouter_client.py  # Cloud model integration
│   └── base.py               # Abstract model client
├── docker/        # Docker sandbox runner
│   ├── __init__.py
│   ├── runner.py             # Docker container execution
│   └── builder.py            # Image building utilities
├── artifacts/     # Project artifact management
│   ├── __init__.py
│   ├── loader.py             # Load YAML/JSON/MD artifacts
│   └── validator.py          # Validate artifact schemas
└── config.py      # Configuration and constants
```

## Imports Order
```python
# 1. Standard library
import json
import os
from pathlib import Path
from typing import TypedDict, Literal

# 2. Third-party
import httpx
import yaml
from pydantic import BaseModel

# 3. Local
from src.models.ollama_client import OllamaClient
```

## Async/Await Rules
- Async functions end with `_async` (e.g., `generate_response_async`)
- Use `httpx.AsyncClient` for HTTP
- Don't block event loop with sync I/O
- Gather parallel tasks with `asyncio.gather`

## Configuration
All external dependencies are configured via:
- Environment variables for secrets (API keys, URLs)
- `src/config.py` for application constants
- `.env.example` documents all required variables

## Dependencies
All Python packages listed in `requirements.txt`:
```
langgraph>=0.0.6
pydantic>=2.0
httpx>=0.24
pyyaml>=6.0
docker>=6.0
pytest>=7.4
pytest-asyncio>=0.21
black>=23.0
isort>=5.12
mypy>=1.4
```

## Git & Commits
- Commits are atomic (one concern per commit)
- Messages: `type(scope): description` (e.g., `feat(ollama): add streaming support`)
- Types: feat, fix, refactor, test, docs, chore

## Logging
- Use `logging` module, configured in `config.py`
- Levels: DEBUG (execution flow), INFO (important events), WARNING (recoverable issues), ERROR (failures)
- Always include context: `logger.error(f"Task {task_id} failed: {error}")`

## Documentation
- README.md for project overview and setup
- Docstrings in code for complex logic
- Type hints serve as interface documentation
- No TODOs without ticket reference

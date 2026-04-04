# AI Development Pipeline Blueprint

## Project: AI-Driven Feature Development Pipeline

### One-liner
Hybrid local/cloud LLM-driven pipeline for structured feature development with bounded autonomy, TDD-first approach, and intelligent model routing.

### Stack
- **Runtime**: Python 3.12, LangGraph, Pydantic
- **Local Models**: Ollama (Qwen 2.5 Coder 7B/32B, DeepSeek Coder)
- **Cloud Models**: OpenRouter (Claude, via LiteLLM proxy)
- **Container**: Docker (Ubuntu 22.04 base)
- **Testing**: pytest, pytest-asyncio
- **Development**: Black, isort, mypy

### Status
**Phase**: Stage 0-1 (Design, Architecture Blueprint)
**Target**: Full working pipeline with example project by end of implementation

### Key Decisions
- ✅ Architecture-first approach separates design from implementation
- ✅ TDD as specification (tests before code)
- ✅ Context minimization (no full repo to models)
- ✅ Explicit escalation (3 iterations max, then cloud)
- ✅ Routing by task tier: local-cheap, local-strong, cloud
- ✅ YAML/JSON artifacts for machine-readable configuration

### Components Being Built
1. **LangGraph Pipeline** (`pipeline/graph.py`)
   - State management via TypedDict
   - Routing engine by model tier and risk level
   - Escalation handler

2. **Model Clients** (`models/`)
   - OllamaClient for local inference
   - OpenRouterClient for cloud models
   - Unified interface via BaseModelClient

3. **Context Builder** (`pipeline/context_builder.py`)
   - Minimal context assembly
   - Artifact loading and filtering
   - Interface extraction from dependencies

4. **Docker Sandbox** (`dev-sandbox/Dockerfile`)
   - Isolated execution environment
   - pytest runner integration
   - Volume mount support for code sync

5. **Artifact System** (`artifacts/`, `pipeline/artifacts/`)
   - SPEC.md (normalized specifications)
   - ARCHITECTURE.yaml (module design)
   - TASK_GRAPH.json (decomposed tasks)
   - CODEBASE_RULES.md (standards, this file next)

### Open Issues / TBD
- Model tier thresholds (file count, complexity metrics)
- Error recovery strategy (retry vs escalate)
- Logging and observability setup
- Integration tests with real Ollama

### Infrastructure Requirements
- **Local**: Ollama running on localhost:11434
- **Cloud**: OpenRouter API key in environment
- **Docker**: Docker Desktop available
- **RAM**: 16+ GB (for Qwen 32B quantization)

### Success Criteria
- [x] Project structure created
- [ ] All artifact types defined and validated
- [ ] LangGraph pipeline runs end-to-end
- [ ] Router correctly assigns model tiers
- [ ] Context builder produces minimal, valid context
- [ ] Docker sandbox integrates with test runner
- [ ] Example feature project completes all stages
- [ ] Observability dashboard functional (metrics, logging)

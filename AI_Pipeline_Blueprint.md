# AI Development Pipeline Blueprint
## Hybrid Local/Cloud Architecture for Mac (Apple Silicon)

---

## 1. Pipeline Architecture

### 1.1 Design Principles

Pipeline строится на пяти инженерных принципах:

- **Architecture-first**: никакая реализация не начинается без согласованной архитектуры.
- **Bounded autonomy**: каждый агент работает в рамках жёстких ограничений — по числу файлов, итераций и scope.
- **TDD as specification**: тесты пишутся ДО реализации и служат поведенческой спецификацией для LLM.
- **Context minimization**: модели никогда не получают весь проект — только релевантный срез.
- **Explicit escalation**: эскалация — часть архитектуры, а не аварийный выход.

### 1.2 Stages Overview

| Stage | Название | Модель | Вход | Выход | Критерий успеха |
|-------|----------|--------|------|-------|-----------------|
| 0 | Intake | — (human) | PRD, constraints, stack | Normalized spec | Spec reviewable, no ambiguity |
| 1 | Architecture | Cloud / strong local | Normalized spec | Module tree, interfaces, data flow | Passes human review |
| 2 | Decomposition | Local strong | Architecture artifacts | Task DAG + sizing | Each task ≤3 files, testable |
| 3 | TDD First | Local cheap/strong | Task spec + interfaces | Test suite per task | Tests run, fail meaningfully |
| 4 | Impl Loop | Local cheap/strong | Tests + task spec + context | Passing code | All tests green, ≤3 iterations |
| 5 | Final Review | Cloud | Codebase + diffs + spec | Approved / rejection list | Architecture intact, coverage ok |

### 1.3 Human Checkpoints

Три обязательных точки, где pipeline останавливается и ждёт человека:

**Checkpoint A — после Stage 0 (Intake → Architecture)**
- Человек подтверждает, что spec корректно отражает требования.
- Блокирует начало архитектурного проектирования.

**Checkpoint B — после Stage 1 (Architecture → Decomposition)**
- Человек подтверждает архитектурные решения: выбор модулей, интерфейсы, библиотеки.
- Самый критичный checkpoint — ошибка здесь каскадирует на весь проект.

**Checkpoint C — после Stage 5 (Final Review → Done)**
- Человек подтверждает итоговое качество, coverage, security basics.
- Последний gate перед merge/deploy.

---

## 2. Stage Details

### Stage 0: Intake

**Цель**: превратить сырой запрос в структурированную, однозначную спецификацию.

**Вход**:
- PRD или текстовое описание задачи
- Технические ограничения (stack, infra, performance)
- Контекст проекта (если есть)

**Выход**: `SPEC.md` — нормализованная спецификация:
```
## Feature: <название>
## Goal: <одно предложение>
## Scope:
  - IN: <что входит>
  - OUT: <что явно исключено>
## Constraints:
  - Stack: ...
  - Performance: ...
  - Security: ...
## Acceptance Criteria:
  - [ ] ...
  - [ ] ...
## Open Questions:
  - ...
```

**Агент**: не требуется (human-driven), но можно использовать local LLM для помощи в нормализации.

**Критерий успеха**: spec не содержит двусмысленностей, scope ограничен, acceptance criteria формализованы.

---

### Stage 1: Architecture

**Цель**: спроектировать модульную архитектуру с чёткими границами.

**Модель**: Cloud (предпочтительно) или strong local + fallback.

**Вход**:
- `SPEC.md`
- `CODEBASE_RULES.md` (если проект существующий)
- Текущая структура проекта (только module tree, не код)

**Выход**: `ARCHITECTURE.yaml`
```yaml
project: <name>
modules:
  - name: auth
    type: service
    files:
      - auth/service.py
      - auth/models.py
      - auth/routes.py
    interfaces:
      - authenticate(token: str) -> User
      - create_session(user: User) -> Session
    dependencies: [db, config]
    risk_level: high  # triggers cloud routing

  - name: api
    type: controller
    files:
      - api/routes.py
      - api/schemas.py
    interfaces:
      - GET /items -> List[Item]
      - POST /items -> Item
    dependencies: [auth, db]
    risk_level: low

data_flow:
  - Request → API → Auth → DB → Response

libraries:
  - fastapi: "0.104+"
  - sqlalchemy: "2.0+"

constraints:
  - async everywhere
  - no ORM lazy loading
```

**Ограничения для модели**:
- Контекст: ТОЛЬКО spec + существующий module tree + codebase rules
- НЕ передавать код реализации
- Результат должен быть parseable YAML

**Критерий успеха**: каждый модуль имеет чёткие interfaces, dependencies явные, risk_level проставлен.

---

### Stage 2: Decomposition

**Цель**: разбить архитектуру на атомарные задачи с зависимостями.

**Модель**: Local strong (Qwen 2.5 Coder 32B, DeepSeek Coder V2 Lite, или аналог).

**Вход**:
- `ARCHITECTURE.yaml`
- `CODEBASE_RULES.md`

**Выход**: `TASK_GRAPH.json`
```json
{
  "tasks": [
    {
      "id": "T001",
      "name": "Create User model and migration",
      "module": "auth",
      "files": ["auth/models.py", "alembic/versions/001_users.py"],
      "depends_on": [],
      "size": "S",
      "risk_level": "low",
      "model_tier": "local_cheap",
      "done_criteria": [
        "User model has id, email, hashed_password, created_at",
        "Migration runs forward and backward",
        "Model passes unit tests"
      ],
      "test_file": "tests/test_auth_models.py"
    },
    {
      "id": "T002",
      "name": "Implement authenticate() service",
      "module": "auth",
      "files": ["auth/service.py"],
      "depends_on": ["T001"],
      "size": "M",
      "risk_level": "high",
      "model_tier": "cloud",
      "done_criteria": [
        "Validates JWT tokens",
        "Returns User or raises AuthError",
        "Handles expired tokens"
      ],
      "test_file": "tests/test_auth_service.py"
    }
  ],
  "execution_order": [
    ["T001"],
    ["T002", "T003"],
    ["T004"]
  ]
}
```

**Жёсткие ограничения на задачу**:
- ≤ 3 файлов на задачу
- ≤ 1 изменение публичного интерфейса
- Каждая задача должна быть тестируемой
- Размеры: S (1 файл, <50 строк), M (2-3 файла, <150 строк), L (→ разбить дальше)

**Критерий успеха**: DAG не имеет циклов, каждая задача проходит size check, risk_level назначен.

---

### Stage 3: TDD First

**Цель**: сгенерировать тесты ДО реализации. Тесты — поведенческая спецификация для LLM.

**Модель**: Local cheap (для простых) / Local strong (для сложных тестов).

**Вход на каждую задачу**:
- Task spec из `TASK_GRAPH.json`
- Интерфейсы из `ARCHITECTURE.yaml`
- Связанные интерфейсы зависимостей (если есть)

**Выход**: test file per task.

```python
# tests/test_auth_service.py
import pytest
from auth.service import authenticate
from auth.exceptions import AuthError

class TestAuthenticate:
    def test_valid_token_returns_user(self, valid_jwt, db_user):
        user = authenticate(valid_jwt)
        assert user.id == db_user.id
        assert user.email == db_user.email

    def test_expired_token_raises(self, expired_jwt):
        with pytest.raises(AuthError, match="expired"):
            authenticate(expired_jwt)

    def test_malformed_token_raises(self):
        with pytest.raises(AuthError, match="invalid"):
            authenticate("not-a-jwt")

    def test_unknown_user_raises(self, jwt_for_deleted_user):
        with pytest.raises(AuthError, match="not found"):
            authenticate(jwt_for_deleted_user)
```

**Контекст для модели**:
- Task spec (done_criteria)
- Interface signature (из ARCHITECTURE.yaml)
- Интерфейсы зависимостей (mock targets)
- CODEBASE_RULES.md (стиль тестов, naming conventions)

**Критерий успеха**: тесты запускаются (с expected failures), покрывают все done_criteria, используют правильные mock boundaries.

---

### Stage 4: Implementation Loop

**Цель**: реализовать код, чтобы тесты прошли. Bounded loop с жёстким лимитом итераций.

**Модель**: Local cheap (для S-задач) / Local strong (для M-задач).

**Цикл**:
```
Iteration 1:
  Input: task spec + tests + interfaces
  Action: generate implementation
  Run: pytest test_file.py
  If PASS → done
  If FAIL → collect errors

Iteration 2:
  Input: previous code + diff + error output + failing tests
  Action: fix implementation
  Run: pytest test_file.py
  If PASS → done
  If FAIL → collect errors

Iteration 3:
  Input: previous code + diff + error output + failing tests
  Action: final fix attempt
  Run: pytest test_file.py
  If PASS → done
  If FAIL → ESCALATE
```

**Контекст для каждой итерации** (context minimization):
- Task spec (done_criteria)
- Test file (full)
- Current implementation file(s) (full)
- Error output (stderr + test failures)
- Interface definitions зависимостей (signatures only, не код)
- `CODEBASE_RULES.md`

**НЕ передавать**:
- Весь проект
- Файлы других модулей (кроме interface signatures)
- Историю предыдущих задач
- README, docs, конфиги не относящиеся к задаче

**Жёсткие правила**:
- Max 3 итерации — затем эскалация
- Если diff > 200 строк — задача слишком большая, вернуть в Stage 2
- Если задача требует изменения >1 публичного интерфейса — вернуть в Stage 2
- Sandbox: код запускается в Docker контейнере

**Критерий успеха**: все тесты green, код соответствует CODEBASE_RULES, diff в пределах нормы.

---

### Stage 5: Final Review

**Цель**: верификация целостности проекта после всех реализованных задач.

**Модель**: Cloud (обязательно).

**Вход**:
- `ARCHITECTURE.yaml`
- Все diffs за текущий цикл
- Test coverage report
- Список выполненных задач с результатами

**Checklist**:
- [ ] Architecture integrity: интерфейсы соответствуют `ARCHITECTURE.yaml`
- [ ] Contract compliance: публичные контракты не нарушены
- [ ] Test coverage: ≥80% на новый код
- [ ] Security basics: нет hardcoded secrets, SQL injection, XSS (для web)
- [ ] No TODO/FIXME без ticket reference
- [ ] Dependencies: нет unused imports, нет circular deps

**Выход**: `REVIEW_REPORT.md` со статусом APPROVED / NEEDS_WORK + список issues.

**Критерий успеха**: отчёт не содержит blocking issues, coverage в норме, архитектура не "поплыла".

---

## 3. Routing & Escalation Engine

### 3.1 Model Tiers

| Tier | Модель (Ollama) | RAM | Задачи |
|------|-----------------|-----|--------|
| Local cheap | Qwen 2.5 Coder 7B, CodeLlama 7B | 4-6 GB | Formatting, docstrings, small fixes, simple test gen, S-tasks |
| Local strong | Qwen 2.5 Coder 32B, DeepSeek Coder V2 | 20-24 GB | Feature impl (1-3 files), debugging, refactoring, decomposition, M-tasks |
| Cloud | Claude Sonnet / Opus (API) | — | Architecture, complex refactors, security/auth, failed escalations, final review |

### 3.2 Routing Decision Tree

```
INPUT: task from TASK_GRAPH.json

1. Check risk_level:
   - "high" (auth, security, payments, migrations) → CLOUD
   
2. Check file count:
   - > 3 files → REJECT (return to decomposition)
   - > 5 files → REJECT + flag architecture issue

3. Check task size:
   - S (1 file, <50 LOC) → LOCAL_CHEAP
   - M (2-3 files, <150 LOC) → LOCAL_STRONG
   - L → REJECT (split further)

4. Check domain:
   - formatting, docstrings, linting → LOCAL_CHEAP
   - test generation (simple) → LOCAL_CHEAP
   - test generation (complex mocks) → LOCAL_STRONG
   - feature implementation → LOCAL_STRONG
   - debugging with traceback → LOCAL_STRONG
   - architecture decisions → CLOUD
   - cross-module refactoring → CLOUD

5. Fallback:
   - If unsure → LOCAL_STRONG
   - If LOCAL_STRONG fails 3x → CLOUD
```

### 3.3 Escalation Triggers

Эскалация — это не ошибка. Это штатная часть pipeline.

| Триггер | Действие |
|---------|----------|
| Task touches >3 files | Return to Stage 2 (re-decompose) |
| Task touches >5 files | Return to Stage 1 (architecture issue) |
| Affects core architecture | Route to cloud immediately |
| Auth / security / payments domain | Route to cloud immediately |
| Implementation loop fails after 3 iterations | Escalate to cloud model |
| Diff > 200 LOC | Return to Stage 2 (task too large) |
| Model confidence low (repeated hedging, contradictions) | Escalate to cloud |
| Public interface change >1 per task | Return to Stage 2 |
| Test coverage drops below threshold | Block merge, investigate |

### 3.4 Cost Model

При типичном проекте (50 задач):

```
40 задач (80%) → local cheap    → $0
 7 задач (14%) → local strong   → $0
 3 задачи (6%) → cloud          → ~$0.50-2.00 per task

Architecture (1x)                → ~$1-3
Final Review (1x)                → ~$1-3

Total per feature cycle: $5-15
vs. All-cloud: $50-150+
```

---

## 4. Artifact Memory System

### 4.1 Project Artifacts

Каждый проект содержит 4 обязательных артефакта. Они хранятся в корне проекта и обновляются по ходу pipeline.

#### PROJECT_BRIEF.md
```markdown
# Project: <name>
## One-liner: <что это>
## Stack: Python 3.12, FastAPI, PostgreSQL, Redis
## Status: active | paused | done
## Current Phase: Stage 2 (decomposition)
## Key Decisions:
  - 2024-01-15: Chose async SQLAlchemy over sync
  - 2024-01-16: JWT auth, not session-based
## Open Issues:
  - Rate limiting strategy TBD
```
**Обновляется**: после каждого checkpoint.
**Подаётся в контекст**: Stage 1, Stage 5.

#### ARCHITECTURE.yaml
Формат описан в Stage 1 выше.
**Обновляется**: Stage 1, после архитектурных escalations.
**Подаётся в контекст**: Stage 2, Stage 4 (только interfaces), Stage 5.

#### TASK_GRAPH.json
Формат описан в Stage 2 выше.
**Обновляется**: Stage 2, при re-decomposition из эскалации.
**Подаётся в контекст**: Stage 3, Stage 4 (только текущая задача).

#### CODEBASE_RULES.md
```markdown
# Codebase Rules
## Language: Python 3.12
## Style:
  - Black formatter, 88 chars
  - isort for imports
  - Type hints everywhere (strict mypy)
## Naming:
  - snake_case for functions/variables
  - PascalCase for classes
  - ALL_CAPS for constants
## Testing:
  - pytest, fixtures in conftest.py
  - Arrange-Act-Assert pattern
  - Mock at boundaries, not internals
## Error Handling:
  - Custom exceptions per module
  - Never bare except
  - Log errors with context
## Patterns:
  - Repository pattern for DB access
  - Service layer for business logic
  - Pydantic for validation / serialization
```
**Обновляется**: редко (при изменении стандартов).
**Подаётся в контекст**: Stage 3, Stage 4 (каждая итерация).

### 4.2 Context Assembly Rules

Для каждого вызова LLM собирается минимальный контекст:

```
Context = {
  task_spec:        TASK_GRAPH.json[current_task],      # always
  codebase_rules:   CODEBASE_RULES.md,                  # always
  interfaces:       ARCHITECTURE.yaml[relevant_modules], # interfaces only
  test_file:        tests/test_<module>.py,              # Stage 4
  impl_files:       [current files being modified],      # Stage 4
  error_output:     stderr + pytest output,              # Stage 4, iter 2-3
  diff:             git diff of current changes,         # Stage 4, iter 2-3
}
```

**Никогда не включать**:
- Весь проект / репозиторий
- Файлы других модулей (кроме interface signatures)
- Историю чата / предыдущих задач
- README, CI configs, deployment files
- Node_modules, venv, build artifacts

### 4.3 Artifact Lifecycle

```
Intake → creates PROJECT_BRIEF.md
       ↓
Architecture → creates ARCHITECTURE.yaml
             → updates PROJECT_BRIEF.md (key decisions)
             ↓
Decomposition → creates TASK_GRAPH.json
              ↓
TDD/Impl → reads TASK_GRAPH.json, CODEBASE_RULES.md
         → reads ARCHITECTURE.yaml (interfaces only)
         → updates TASK_GRAPH.json (task status)
         ↓
Final Review → reads all artifacts
            → updates PROJECT_BRIEF.md (status, issues)
            → produces REVIEW_REPORT.md
```

---

## 5. Agent Roles

### 5.1 Agent Registry

| Agent | Роль | Model Tier | Input | Output |
|-------|------|------------|-------|--------|
| Spec Normalizer | Структурирует PRD в SPEC.md | Local cheap | Raw PRD | SPEC.md |
| Architect | Проектирует модульную архитектуру | Cloud | SPEC.md, rules | ARCHITECTURE.yaml |
| Decomposer | Разбивает архитектуру на задачи | Local strong | ARCHITECTURE.yaml | TASK_GRAPH.json |
| Test Writer | Генерирует тесты по spec | Local cheap/strong | Task spec, interfaces | Test files |
| Implementer | Реализует код по тестам | Local cheap/strong | Tests, spec, context | Implementation |
| Debugger | Фиксит по error output | Local strong | Code, errors, diff | Fixed code |
| Reviewer | Финальная проверка качества | Cloud | All artifacts, diffs | REVIEW_REPORT.md |
| Router | Направляет задачи на нужный tier | Rule-based (no LLM) | Task metadata | Model selection |
| Escalator | Обрабатывает failures | Rule-based → Cloud | Failed task context | Re-routed task |

### 5.2 Agent Constraints

Каждый агент работает под жёсткими ограничениями:

```yaml
implementer:
  max_files_per_task: 3
  max_iterations: 3
  max_diff_lines: 200
  max_public_interface_changes: 1
  must_receive: [task_spec, test_file, codebase_rules]
  must_not_receive: [full_repo, other_module_code, chat_history]
  on_failure: escalate_to_cloud

decomposer:
  max_task_size: M (2-3 files, <150 LOC)
  must_produce: [task_id, files, depends_on, done_criteria, test_file]
  must_verify: [no_cycles_in_dag, all_tasks_testable, risk_level_assigned]

test_writer:
  must_cover: all done_criteria from task spec
  must_use: mock boundaries from ARCHITECTURE.yaml
  must_follow: patterns from CODEBASE_RULES.md
```

---

## 6. Implementation Playbook

### 6.1 Recommended Ollama Models (Apple Silicon)

**Для Mac с 32 GB RAM**:
- **Cheap tier**: `qwen2.5-coder:7b` — быстрый, хорош для formatting, docstrings, simple tests
- **Strong tier**: `qwen2.5-coder:32b` (Q4_K_M quantization) — основная рабочая лошадь
- **Alternative strong**: `deepseek-coder-v2:16b` — хорош для debugging

**Для Mac с 16 GB RAM**:
- **Cheap tier**: `qwen2.5-coder:7b`
- **Strong tier**: `qwen2.5-coder:14b` — компромисс между качеством и RAM
- **Fallback**: более агрессивная эскалация в cloud

**Установка**:
```bash
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:32b
```

### 6.2 Docker Sandbox

Каждая задача выполняется в изолированном контейнере:

```dockerfile
# dev-sandbox/Dockerfile
FROM python:3.12-slim

WORKDIR /workspace
COPY requirements.txt .
RUN pip install -r requirements.txt

# Project code mounted as volume
# Tests run inside container
# No network access (except for pip install)
```

```bash
# Run task in sandbox
docker run --rm \
  -v $(pwd)/src:/workspace/src \
  -v $(pwd)/tests:/workspace/tests \
  -v $(pwd)/artifacts:/workspace/artifacts \
  dev-sandbox \
  pytest tests/test_auth_service.py -v
```

### 6.3 LangGraph Pipeline Structure

Минимальная структура графа:

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

class PipelineState(TypedDict):
    spec: str
    architecture: dict
    task_graph: dict
    current_task: dict
    iteration: int
    test_results: str
    implementation: str
    status: Literal["pending", "pass", "fail", "escalated"]

def route_task(state: PipelineState) -> str:
    task = state["current_task"]
    if task["risk_level"] == "high":
        return "cloud_implement"
    if task["size"] == "S":
        return "local_cheap_implement"
    return "local_strong_implement"

def check_iteration(state: PipelineState) -> str:
    if state["status"] == "pass":
        return "next_task"
    if state["iteration"] >= 3:
        return "escalate"
    return "retry"

# Graph construction
graph = StateGraph(PipelineState)

graph.add_node("decompose", decompose_task)
graph.add_node("write_tests", generate_tests)
graph.add_node("local_cheap_implement", implement_cheap)
graph.add_node("local_strong_implement", implement_strong)
graph.add_node("cloud_implement", implement_cloud)
graph.add_node("run_tests", run_tests_in_docker)
graph.add_node("escalate", escalate_to_cloud)
graph.add_node("next_task", advance_to_next)

graph.add_conditional_edges("decompose", route_task, {
    "local_cheap_implement": "local_cheap_implement",
    "local_strong_implement": "local_strong_implement",
    "cloud_implement": "cloud_implement",
})

# All implement nodes lead to test runner
for node in ["local_cheap_implement", "local_strong_implement", "cloud_implement"]:
    graph.add_edge(node, "run_tests")

graph.add_conditional_edges("run_tests", check_iteration, {
    "next_task": "next_task",
    "retry": "local_strong_implement",  # retry on stronger model
    "escalate": "escalate",
})

graph.add_edge("escalate", "run_tests")

graph.set_entry_point("decompose")
app = graph.compile()
```

### 6.4 Ollama Integration

```python
import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"

async def call_local_model(
    prompt: str,
    model: str = "qwen2.5-coder:7b",
    temperature: float = 0.1,
) -> str:
    """Call local Ollama model with minimal context."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(OLLAMA_URL, json={
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False,
        })
        return response.json()["response"]

def build_impl_prompt(
    task_spec: dict,
    test_code: str,
    codebase_rules: str,
    interfaces: str,
    error_output: str = None,
    previous_code: str = None,
) -> str:
    """Assemble minimal context for implementation."""
    prompt = f"""You are implementing a specific task. Follow the rules exactly.

TASK:
{task_spec['name']}

DONE CRITERIA:
{chr(10).join('- ' + c for c in task_spec['done_criteria'])}

FILES TO CREATE/MODIFY:
{', '.join(task_spec['files'])}

CODEBASE RULES:
{codebase_rules}

INTERFACES (dependencies you can use):
{interfaces}

TESTS (your code must pass these):
```python
{test_code}
```
"""
    if previous_code and error_output:
        prompt += f"""
PREVIOUS ATTEMPT (fix the errors):
```python
{previous_code}
```

ERRORS:
{error_output}
"""

    prompt += """
OUTPUT: Only the implementation code. No explanations. No markdown fences.
"""
    return prompt
```

### 6.5 Context Builder

```python
import yaml
import json
from pathlib import Path

class ContextBuilder:
    """Assembles minimal context for each LLM call."""
    
    def __init__(self, project_root: Path):
        self.root = project_root
        self.architecture = yaml.safe_load(
            (project_root / "ARCHITECTURE.yaml").read_text()
        )
        self.rules = (project_root / "CODEBASE_RULES.md").read_text()
        self.task_graph = json.loads(
            (project_root / "TASK_GRAPH.json").read_text()
        )
    
    def for_implementation(self, task_id: str, iteration: int = 1) -> dict:
        """Build context for Stage 4 implementation."""
        task = self._get_task(task_id)
        
        context = {
            "task_spec": task,
            "codebase_rules": self.rules,
            "interfaces": self._get_interfaces(task["module"]),
            "test_code": self._read_file(task["test_file"]),
        }
        
        if iteration > 1:
            context["previous_code"] = self._read_impl_files(task["files"])
            context["error_output"] = self._get_last_test_output(task_id)
        
        return context
    
    def _get_interfaces(self, module_name: str) -> str:
        """Extract only interface signatures for dependencies."""
        module = next(
            m for m in self.architecture["modules"]
            if m["name"] == module_name
        )
        dep_interfaces = []
        for dep_name in module.get("dependencies", []):
            dep = next(
                m for m in self.architecture["modules"]
                if m["name"] == dep_name
            )
            dep_interfaces.append(
                f"# {dep_name}\n" +
                "\n".join(f"  {i}" for i in dep["interfaces"])
            )
        return "\n\n".join(dep_interfaces)
    
    def _get_task(self, task_id: str) -> dict:
        return next(
            t for t in self.task_graph["tasks"]
            if t["id"] == task_id
        )
    
    def _read_file(self, path: str) -> str:
        full = self.root / path
        return full.read_text() if full.exists() else ""
    
    def _read_impl_files(self, files: list) -> str:
        parts = []
        for f in files:
            content = self._read_file(f)
            if content:
                parts.append(f"# {f}\n{content}")
        return "\n\n".join(parts)
    
    def _get_last_test_output(self, task_id: str) -> str:
        log_path = self.root / f".pipeline/logs/{task_id}_last_test.log"
        return log_path.read_text() if log_path.exists() else ""
```

### 6.6 Launch Checklist

Минимальный набор для запуска pipeline:

```
[ ] Ollama installed and running (ollama serve)
[ ] Models pulled (qwen2.5-coder:7b, qwen2.5-coder:32b)
[ ] Docker Desktop running on Mac
[ ] dev-sandbox image built
[ ] Python 3.12 + langgraph installed
[ ] Anthropic API key configured (for cloud tier)
[ ] Project structure created:
    project/
    ├── src/
    ├── tests/
    ├── artifacts/
    │   ├── PROJECT_BRIEF.md
    │   ├── ARCHITECTURE.yaml
    │   ├── TASK_GRAPH.json
    │   └── CODEBASE_RULES.md
    ├── .pipeline/
    │   ├── logs/
    │   └── config.yaml
    ├── dev-sandbox/
    │   └── Dockerfile
    └── pipeline/
        ├── graph.py
        ├── context_builder.py
        ├── ollama_client.py
        ├── docker_runner.py
        └── router.py
```

---

## 7. Anti-Patterns

Что pipeline явно запрещает:

1. **"Дай модели весь проект"** — контекст загрязняется, качество падает, cost растёт.
2. **"Одна модель делает всё"** — routing по tier существует не для красоты.
3. **"Бесконечный retry"** — 3 итерации максимум, потом escalation.
4. **"Монолитная задача"** — если >3 файлов, задача не готова к реализации.
5. **"Автономный агент без границ"** — каждый агент ограничен по scope, контексту и итерациям.
6. **"Skip TDD"** — без тестов implementation loop слепой.
7. **"Skip architecture"** — decomposition без архитектуры производит мусор.
8. **"Human checkpoint optional"** — checkpoint B (после архитектуры) критичен, пропуск = каскадная ошибка.

---

## 8. Metrics & Observability

Что трекать для оценки здоровья pipeline:

| Metric | Target | Red Flag |
|--------|--------|----------|
| Tasks resolved locally | ≥80% | <70% (модели не справляются или decomposition плохой) |
| Avg iterations per task | ≤2 | >2.5 (задачи слишком крупные или контекст плохой) |
| Escalation rate | ≤20% | >30% (архитектура нестабильна) |
| Test coverage on new code | ≥80% | <70% |
| Cloud API cost per feature | <$15 | >$30 (routing неэффективен) |
| Tasks returned to decomposition | ≤10% | >20% (decomposer не справляется) |
| Time per task (local) | <5 min | >10 min (модель слишком медленная или контекст раздут) |

---

*Blueprint version 1.0 — designed for Python / LangGraph / Ollama / Docker on Apple Silicon Mac.*

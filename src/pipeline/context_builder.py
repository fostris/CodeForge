"""Context builder for minimal LLM input assembly."""

import ast
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.config import config, get_logger
from src.artifacts import ArtifactLoader, get_module_interfaces


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Available packages in Docker sandbox (from dev-sandbox/Dockerfile)
# ---------------------------------------------------------------------------

AVAILABLE_PACKAGES = (
    "AVAILABLE PACKAGES IN DOCKER (ONLY use these — do NOT import anything else):\n"
    "  Testing: pytest, pytest-asyncio, pytest-cov, pytest-mock\n"
    "  Web: fastapi, uvicorn, httpx, python-multipart\n"
    "  Database: sqlalchemy, alembic\n"
    "  Validation: pydantic, pydantic-settings, email-validator\n"
    "  Auth: PyJWT (import as 'jwt'), passlib, bcrypt, python-jose\n"
    "  Other: python-dotenv\n\n"
    "FORBIDDEN PACKAGES (NOT installed, will crash with ModuleNotFoundError):\n"
    "  redis, celery, motor, mongoengine, aioredis, dramatiq, rq, kombu,\n"
    "  aiohttp, flask, django, tortoise-orm, databases, asyncpg, psycopg2\n\n"
    "If a task requires redis/celery/etc., implement an in-memory fallback instead.\n"
    "For rate limiting: use a simple dict with timestamps, NOT redis.\n"
    "For JWT: use PyJWT with HS256 algorithm and a string secret key, NOT RS256.\n"
)


# ---------------------------------------------------------------------------
# P0: Workspace scanner — provides real module structure to LLM prompts
# ---------------------------------------------------------------------------

def scan_workspace_exports(workspace_dir: Path) -> Dict[str, List[str]]:
    """
    Scan workspace/src/ to discover existing modules and their exports.
    
    Returns dict like:
        {"src.config": ["Settings", "get_settings"],
         "src.models.user": ["User", "Base"],
         ...}
    
    Re-scanned each time (files change between tasks).
    """
    exports: Dict[str, List[str]] = {}
    src_dir = workspace_dir / "src"
    if not src_dir.exists():
        return exports

    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue

        # Convert path to module path: workspace/src/models/user.py → src.models.user
        try:
            rel = py_file.relative_to(workspace_dir)
        except ValueError:
            continue
        module_path = str(rel).replace("/", ".").replace(".py", "")

        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:
            exports[module_path] = ["<parse error>"]
            continue

        names: List[str] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.ClassDef,)):
                names.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    names.append(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and (
                        target.id.isupper() or target.id == "Base"
                    ):
                        names.append(target.id)

        if names:
            exports[module_path] = names
        else:
            exports[module_path] = ["<empty module>"]

    return exports


def format_workspace_context(exports: Dict[str, List[str]]) -> str:
    """Format workspace exports as a prompt section."""
    if not exports:
        return ""

    lines = ["EXISTING MODULES IN WORKSPACE (use these EXACT import paths):"]
    for module_path, names in sorted(exports.items()):
        names_str = ", ".join(names)
        lines.append(f"  from {module_path} import {names_str}")

    lines.append("")
    lines.append(
        "CRITICAL IMPORT RULES:\n"
        "- ONLY import from paths listed above OR from stdlib / third-party packages.\n"
        "- Do NOT invent module names like 'src.main', 'src.db', 'src.schemas',\n"
        "  'src.models.user_model' — if the path is not listed above, it does NOT exist.\n"
        "- If you need something that isn't listed, define it yourself in your code."
    )
    return chr(10).join(lines)


class ContextBuilder:
    """Assemble minimal context for each pipeline stage."""

    def __init__(self, artifacts_dir: Optional[Path] = None):
        self.loader = ArtifactLoader(artifacts_dir)
        self.artifacts_dir = artifacts_dir or config.artifacts_dir

        # Cache loaded artifacts
        self._architecture = None
        self._codebase_rules = None
        self._task_graph = None

    @property
    def architecture(self) -> Dict[str, Any]:
        if self._architecture is None:
            self._architecture = self.loader.load_architecture()
        return self._architecture

    @property
    def codebase_rules(self) -> str:
        if self._codebase_rules is None:
            self._codebase_rules = self.loader.load_codebase_rules()
        return self._codebase_rules

    @property
    def task_graph(self) -> list:
        if self._task_graph is None:
            try:
                self._task_graph = self.loader.load_task_graph()
            except AttributeError:
                # TASK_GRAPH.json is a plain list (not {"tasks": [...]})
                # — load it directly
                tg_path = self.artifacts_dir / "TASK_GRAPH.json"
                if tg_path.exists():
                    data = json.loads(tg_path.read_text(encoding="utf-8"))
                    self._task_graph = data if isinstance(data, list) else data.get("tasks", [])
                else:
                    self._task_graph = []
        return self._task_graph

    # ------------------------------------------------------------------
    # Workspace context (freshly scanned each call)
    # ------------------------------------------------------------------

    def get_workspace_context(self) -> str:
        """Return formatted string of what modules exist in workspace."""
        exports = scan_workspace_exports(config.workspace_dir)
        return format_workspace_context(exports)

    def get_dependency_sources(self, task: Dict[str, Any]) -> str:
        """Read source code of files produced by dependency tasks.

        When T009 depends on [T005, T006, T007, T008], the LLM needs to see the
        actual method signatures of those modules — not just their export names.
        This reads the workspace files for each dependency task and returns a
        formatted prompt section with the source excerpts.
        """
        depends_on = task.get("depends_on") or []
        if not depends_on:
            return ""

        # Build task-id → files mapping from task graph
        task_files_map: Dict[str, List[str]] = {}
        for t in self.task_graph:
            tid = t.get("id", "")
            if tid in depends_on:
                task_files_map[tid] = t.get("files", [])

        if not task_files_map:
            return ""

        sections: List[str] = []
        total_chars = 0
        MAX_CHARS = 8000  # budget for dependency sources

        for tid in depends_on:
            files = task_files_map.get(tid, [])
            for fpath in files:
                full_path = config.workspace_dir / fpath
                if not full_path.exists():
                    continue
                try:
                    source = full_path.read_text(encoding="utf-8")
                except Exception:
                    continue

                # Truncate very large files — keep signatures, skip function bodies
                if len(source) > 2000:
                    source = source[:2000] + "\n# ... (truncated)"

                if total_chars + len(source) > MAX_CHARS:
                    break

                sections.append(
                    f"--- {fpath} (from {tid}) ---\n{source}"
                )
                total_chars += len(source)

            if total_chars >= MAX_CHARS:
                break

        if not sections:
            return ""

        header = (
            "DEPENDENCY SOURCE CODE (from tasks this task depends on).\n"
            "Your code MUST use the EXACT class names, method signatures, and\n"
            "constructor arguments shown below. Do NOT guess or invent APIs.\n\n"
        )
        return header + "\n\n".join(sections)

    # ------------------------------------------------------------------
    # Context assembly per stage
    # ------------------------------------------------------------------

    def for_spec_review(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Context for human review of normalized spec."""
        return {
            "task": "review_spec",
            "spec": spec,
            "checklist": [
                "Scope is clear and bounded",
                "Acceptance criteria are testable",
                "No ambiguities in requirements",
                "Stack and constraints are documented",
            ],
        }

    def for_architecture(self, spec: Dict[str, Any], codebase_rules: Optional[str] = None) -> Dict[str, Any]:
        """Context for architecture stage."""
        rules = codebase_rules or self.codebase_rules

        return {
            "task": "design_architecture",
            "spec": spec,
            "codebase_rules": rules,
            "rules": [
                "Each module <=5 public interfaces",
                "Dependencies form DAG (no cycles)",
                "High-risk modules (auth, payments, migrations) marked 'high'",
                "Output: ARCHITECTURE.yaml",
            ],
        }

    def for_decomposition(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Context for task decomposition stage."""
        return {
            "task": "decompose_architecture",
            "architecture": architecture,
            "rules": [
                "Each task touches <=3 files",
                "Each task modifies <=1 public interface",
                "Each task is independently testable",
                "Size: S (1 file), M (2-3 files), L (split further)",
                "Risk level assigned (low/medium/high)",
                "Output: TASK_GRAPH.json with DAG",
            ],
        }

    def for_test_generation(
        self,
        task: Dict[str, Any],
        module_name: str,
        existing_implementation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Context for TDD-first test generation.
        
        Args:
            existing_implementation: If provided (during test regeneration after
                implementation already exists), the test prompt will include this
                code so the new test matches the real class/function signatures.
        """
        interfaces = get_module_interfaces(self.architecture, module_name)

        ctx = {
            "task": "generate_tests",
            "task_spec": task,
            "interfaces": interfaces,
            "codebase_rules": self.codebase_rules,
            "workspace_context": self.get_workspace_context(),
            "rules": [
                "Tests in Arrange-Act-Assert pattern",
                "Cover all done_criteria",
                "Mock at boundaries (DB, APIs)",
                "Use pytest fixtures",
                "Each test is independent",
            ],
        }
        if existing_implementation:
            ctx["existing_implementation"] = existing_implementation
        return ctx

    def for_implementation(
        self,
        task: Dict[str, Any],
        test_code: str,
        iteration: int = 1,
        previous_code: Optional[str] = None,
        error_output: Optional[str] = None,
        diff: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Context for implementation stage."""
        module_name = task.get("module", "")
        interfaces = get_module_interfaces(self.architecture, module_name)

        context = {
            "task": "implement_task",
            "task_spec": task,
            "interfaces": interfaces,
            "test_code": test_code or "",
            "codebase_rules": self.codebase_rules,
            "workspace_context": self.get_workspace_context(),
            "iteration": iteration,
        }

        if iteration > 1 and previous_code:
            context["previous_code"] = previous_code
            context["error_output"] = error_output
            context["diff"] = diff

        return context

    def for_single_call(
        self,
        task: Dict[str, Any],
        iteration: int = 1,
        previous_impl: Optional[str] = None,
        previous_tests: Optional[str] = None,
        error_output: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Context for single-call impl+tests generation."""
        module_name = task.get("module", "")
        interfaces = get_module_interfaces(self.architecture, module_name)

        context = {
            "task": "single_call",
            "task_spec": task,
            "interfaces": interfaces,
            "codebase_rules": self.codebase_rules,
            "workspace_context": self.get_workspace_context(),
            "dependency_sources": self.get_dependency_sources(task),
            "iteration": iteration,
        }

        if iteration > 1:
            context["previous_impl"] = previous_impl
            context["previous_tests"] = previous_tests
            context["error_output"] = error_output

        return context

    # ------------------------------------------------------------------
    # Prompt assembly
    # ------------------------------------------------------------------

    def assemble_prompt(self, context: Dict[str, Any]) -> str:
        """Assemble final prompt from context."""
        task_type = context.get("task", "unknown")

        if task_type == "design_architecture":
            return self._architecture_prompt(context)
        elif task_type == "decompose_architecture":
            return self._decomposition_prompt(context)
        elif task_type == "generate_tests":
            return self._test_prompt(context)
        elif task_type == "implement_task":
            return self._implementation_prompt(context)
        elif task_type == "single_call":
            return self._single_call_prompt(context)
        else:
            return json.dumps(context, indent=2)

    def _architecture_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for architecture stage."""
        spec_str = json.dumps(context['spec'], indent=2)
        rules_str = context['codebase_rules'][:1000]
        reqs = chr(10).join('- ' + r for r in context['rules'])
        return (
            "Design a modular architecture for the following specification.\n\n"
            f"SPECIFICATION:\n{spec_str}\n\n"
            f"CODEBASE RULES:\n{rules_str}\n\n"
            f"REQUIREMENTS:\n{reqs}\n\n"
            "OUTPUT: YAML format only, parseable structure."
        )

    def _decomposition_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for task decomposition."""
        arch = context.get("architecture", {})
        rules = context.get("rules", [])
        arch_str = json.dumps(arch, indent=2) if isinstance(arch, dict) else str(arch)[:3000]
        rules_str = chr(10).join('- ' + r for r in rules)

        return (
            "Decompose this architecture into atomic implementation tasks.\n\n"
            f"ARCHITECTURE:\n{arch_str}\n\n"
            f"DECOMPOSITION RULES:\n{rules_str}\n\n"
            "OUTPUT REQUIREMENTS:\n"
            "- Respond with ONLY a valid JSON object, nothing else\n"
            "- No markdown fences, no explanations before or after\n"
            "- Start with { and end with }\n"
            "- Use this exact structure:\n\n"
            '{\n'
            '  "tasks": [\n'
            '    {\n'
            '      "id": "T001",\n'
            '      "name": "Short task name",\n'
            '      "module": "module_name",\n'
            '      "files": ["src/module/file.py"],\n'
            '      "depends_on": [],\n'
            '      "size": "S",\n'
            '      "risk_level": "low",\n'
            '      "description": "What to implement",\n'
            '      "done_criteria": ["criterion 1", "criterion 2"],\n'
            '      "test_file": "tests/unit/test_module.py"\n'
            '    }\n'
            '  ]\n'
            '}\n\n'
            "IMPORTANT RULES:\n"
            "- Every task MUST have a 'test_file' field\n"
            "- MAXIMUM 15 tasks total. If you need more, merge related tasks.\n"
            "- File paths MUST use simple flat structure: 'src/module/file.py' (max 2 levels under src/)\n"
            "- Test paths MUST be flat: 'tests/unit/test_name.py' (no deep nesting)\n"
            "- Do NOT use deeply nested paths like src/service/sub/sub2/file.py\n"
            "- Examples of GOOD paths: 'src/config.py', 'src/auth/service.py', 'src/models/user.py'\n"
            "- Examples of BAD paths: 'src/auth_service/core/config/settings.py'\n"
            "- For JWT tasks: use HS256 algorithm with a string secret key. Do NOT use RS256.\n"
            "  Do NOT mention RS256 in task names or descriptions.\n"
            "- Do NOT include migration files (e.g. migrations/001_create_users.py) in task 'files' lists.\n"
            "  Migration files have numeric prefixes that break Python imports in tests."
        )

    def _test_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for test generation."""
        task = context["task_spec"]

        # Convert file paths to import paths for the model
        import_hints = []
        for f in task.get('files', []):
            module_path = f.replace('/', '.').replace('.py', '')
            if module_path.endswith('.__init__'):
                module_path = module_path[:-len('.__init__')]
            parts = module_path.split('.')
            if any(part[:1].isdigit() for part in parts):
                continue
            import_hints.append(f"from {module_path} import ...")

        import_hints_str = chr(10).join(import_hints)
        criteria_str = chr(10).join('- ' + c for c in task.get('done_criteria', []))
        interfaces_str = json.dumps(context['interfaces'], indent=2)

        # P0: Real workspace context
        workspace_ctx = context.get("workspace_context") or ""

        # P0: Existing implementation (available during test regeneration)
        existing_impl = context.get("existing_implementation") or ""
        impl_section = ""
        if existing_impl:
            impl_section = (
                "EXISTING IMPLEMENTATION (your tests MUST match this code's actual API):\n"
                "```python\n"
                f"{existing_impl[:3000]}\n"
                "```\n"
                "CRITICAL: Use the EXACT class names, method names, and signatures from the code above.\n"
                "Do NOT invent methods or attributes that don't exist in this implementation.\n"
                "Do NOT assume a different API — test what IS there, not what you think should be there.\n\n"
            )

        return (
            "Generate pytest unit tests for this task.\n\n"
            f"TASK: {task['name']}\n"
            f"DESCRIPTION: {task.get('description', '')}\n"
            f"IMPLEMENTATION FILES: {', '.join(task['files'])}\n\n"
            "The implementation will be located at these exact paths. Use these imports:\n"
            f"{import_hints_str}\n\n"
            # ── Workspace context ──
            + (f"{workspace_ctx}\n\n" if workspace_ctx else "")
            # ── Existing implementation (only during test regen) ──
            + impl_section
            +
            f"DONE CRITERIA (each must have at least one test):\n{criteria_str}\n\n"
            f"INTERFACES (use these for mocking):\n{interfaces_str}\n\n"
            f"{AVAILABLE_PACKAGES}\n"
            "RULES:\n"
            "- Use pytest with standard assertions\n"
            "- Use unittest.mock for mocking (from unittest.mock import patch, MagicMock)\n"
            "- Do NOT use pytest-mock or mocker fixture\n"
            "- Do NOT mock internal functions of standard libraries (bcrypt, hashlib, jwt, os, etc.)\n"
            "- Instead test BEHAVIOR: call the real function and check the output\n"
            "- Only mock EXTERNAL dependencies: databases, HTTP calls, file I/O\n"
            "- Do NOT instantiate classes that need external resources (DB, env vars) without mocking\n"
            "- Each test function must be independent\n"
            "- Import from the EXACT paths listed above\n"
            "- 'Field' must be imported from 'pydantic', NEVER from 'pydantic_settings'\n"
            "- 'BaseSettings' is from 'pydantic_settings', but 'BaseModel' and 'Field' are from 'pydantic'\n"
            "- We use PYDANTIC V2. NEVER use @validator or @root_validator (V1 API, removed).\n"
            "  Use @field_validator and @model_validator instead.\n"
            "- Every variable used in a test MUST be defined inside that test or in a fixture\n"
            "- NEVER reference a variable that was not created in the current scope\n"
            "- When importing from other project modules, ONLY use paths listed in EXISTING MODULES\n"
            "- For SQLAlchemy model tests: import Base FROM the implementation module\n"
            "  (the implementation defines Base). Do NOT define your own Base in the test.\n"
            "- For JWT tests: use algorithm='HS256' with a string secret. Do NOT use RS256.\n\n"
            #
            # ── ANTI-PATTERN CATALOG ──────────────────────────────────────
            #
            "COMMON BUGS — DO NOT MAKE THESE MISTAKES:\n\n"
            #
            "BUG 1 — called_once_with silently passes:\n"
            "  # WRONG — this is an attribute access, always truthy, NEVER asserts anything!\n"
            "  mock_obj.called_once_with('arg')       # ← SILENT BUG, test always passes\n"
            "  mock_obj.called_with('arg')             # ← SILENT BUG, same problem\n"
            "  # CORRECT — use assert_ prefix, this actually checks the call\n"
            "  mock_obj.assert_called_once_with('arg') # ← REAL assertion\n"
            "  mock_obj.assert_called_with('arg')      # ← REAL assertion\n\n"
            #
            "BUG 2 — wrong pydantic imports (we use PYDANTIC V2, not V1!):\n"
            "  # WRONG — these are all pydantic V1 API, removed in V2\n"
            "  from pydantic import validator           # ← REMOVED in V2\n"
            "  from pydantic_settings import Field      # ← Field is NOT in pydantic_settings\n"
            "  from pydantic_settings import validator   # ← does NOT exist\n"
            "  @validator('field_name')                  # ← REMOVED in V2\n"
            "  # CORRECT — pydantic V2 API\n"
            "  from pydantic import field_validator      # ← V2 replacement for @validator\n"
            "  from pydantic import Field               # ← Field is ALWAYS from pydantic\n"
            "  from pydantic_settings import BaseSettings # ← ONLY BaseSettings from here\n"
            "  @field_validator('field_name')            # ← V2 API\n\n"
            "  PYDANTIC V2 IMPORT CHEAT SHEET:\n"
            "    from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError\n"
            "    from pydantic_settings import BaseSettings\n"
            "  NEVER import: validator, root_validator, EmailError, EmailStr (use email_validator lib instead)\n"
            "  EmailError does NOT exist in pydantic v2. To validate emails, use:\n"
            "    from email_validator import validate_email, EmailNotValidError\n\n"
            #
            "BUG 3 — mocking stdlib internals:\n"
            "  # WRONG — do not mock bcrypt/hashlib/jwt internals\n"
            "  @patch('bcrypt.gensalt')\n"
            "  @patch('bcrypt.hashpw')\n"
            "  def test_hash(mock_hashpw, mock_gensalt): ...\n"
            "  # CORRECT — call the real function, check the result\n"
            "  def test_hash_password():\n"
            "      result = hash_password('secret')\n"
            "      assert isinstance(result, str)\n"
            "      assert len(result) > 0\n\n"
            #
            "BUG 4 — unprotected env var access:\n"
            "  # WRONG — crashes at import/instantiation if env var missing\n"
            "  settings = Settings()  # reads DATABASE_URL from env\n"
            "  # CORRECT — mock env vars or provide defaults\n"
            "  @patch.dict('os.environ', {'DATABASE_URL': 'sqlite://', 'SECRET_KEY': 'test'})\n"
            "  def test_settings():\n"
            "      settings = Settings()\n"
            "      assert settings.database_url == 'sqlite://'\n\n"
            #
            "BUG 5 — undefined variables in test:\n"
            "  # WRONG — 'engine' is never defined, causes NameError\n"
            "  def test_user_unique_email():\n"
            "      Base.metadata.create_all(bind=engine)  # ← NameError!\n"
            "  # CORRECT — each test creates its own engine and session\n"
            "  def test_user_unique_email():\n"
            "      from sqlalchemy import create_engine\n"
            "      from sqlalchemy.orm import sessionmaker\n"
            "      engine = create_engine('sqlite://')  # in-memory DB\n"
            "      Base.metadata.create_all(bind=engine)\n"
            "      Session = sessionmaker(bind=engine)\n"
            "      session = Session()\n"
            "      # ... test logic using session ...\n"
            "      session.close()\n\n"
            #
            "BUG 6 — test checks error MESSAGE text instead of error TYPE:\n"
            "  # WRONG — fragile, breaks if wording changes\n"
            "  assert str(exc.value) == 'Invalid credentials provided'\n"
            "  # CORRECT — check the exception TYPE, not the exact message\n"
            "  with pytest.raises(InvalidCredentialsError):\n"
            "      authenticate(bad_user, bad_pass)\n"
            "  # ALSO CORRECT — if you must check message, use 'in'\n"
            "  assert 'invalid' in str(exc.value).lower()\n\n"
            #
            "BUG 7 — asserting on .message attribute of custom exceptions:\n"
            "  # WRONG — custom exceptions may not have a 'message' attribute\n"
            "  exc = AuthenticationError('test')\n"
            "  assert exc.message == 'test'             # ← AttributeError if no .message\n"
            "  assert str(exc) == 'test'                 # ← may differ based on __str__\n"
            "  # CORRECT — check args tuple (works for ALL Python exceptions)\n"
            "  exc = AuthenticationError('test')\n"
            "  assert exc.args[0] == 'test'\n"
            "  assert isinstance(exc, AuthenticationError)\n"
            "  # ALSO CORRECT — check that it IS an Exception subclass\n"
            "  assert issubclass(AuthenticationError, Exception)\n\n"
            #
            # ── TEMPLATE FOR DB/MODEL TESTS ───────────────────────────────
            #
            "TEMPLATE — SQLAlchemy model test (use this pattern for any DB model test):\n"
            "  import pytest\n"
            "  from sqlalchemy import create_engine\n"
            "  from sqlalchemy.orm import sessionmaker\n"
            "  from src.auth.models import Base, User  # import Base AND model from implementation\n\n"
            "  @pytest.fixture\n"
            "  def db_session():\n"
            "      engine = create_engine('sqlite://')  # in-memory, no file needed\n"
            "      Base.metadata.create_all(bind=engine)\n"
            "      Session = sessionmaker(bind=engine)\n"
            "      session = Session()\n"
            "      yield session\n"
            "      session.close()\n"
            "      Base.metadata.drop_all(bind=engine)\n\n"
            "  def test_create_user(db_session):\n"
            "      user = User(email='a@b.com', hashed_password='hash123')\n"
            "      db_session.add(user)\n"
            "      db_session.commit()\n"
            "      assert user.id is not None\n"
            "      assert user.email == 'a@b.com'\n\n"
            "  def test_unique_email(db_session):\n"
            "      from sqlalchemy.exc import IntegrityError\n"
            "      db_session.add(User(email='dup@b.com', hashed_password='h1'))\n"
            "      db_session.commit()\n"
            "      db_session.add(User(email='dup@b.com', hashed_password='h2'))\n"
            "      with pytest.raises(IntegrityError):\n"
            "          db_session.commit()\n"
            "      db_session.rollback()\n\n"
            #
            "BUG 8 — forgetting to import pytest:\n"
            "  # WRONG — using pytest.raises without importing pytest\n"
            "  def test_something():\n"
            "      with pytest.raises(ValueError):  # ← NameError: name 'pytest' is not defined!\n"
            "          ...\n"
            "  # CORRECT — always import pytest at the top of every test file\n"
            "  import pytest\n"
            "  def test_something():\n"
            "      with pytest.raises(ValueError):\n"
            "          ...\n\n"
            #
            "BUG 9 — importing __init__ explicitly:\n"
            "  # WRONG — never spell out __init__ in an import path\n"
            "  from src.auth.models.__init__ import Base, User  # ← ModuleNotFoundError\n"
            "  # CORRECT — Python resolves __init__.py automatically\n"
            "  from src.auth.models import Base, User\n\n"
            #
            "BUG 10 — importing files whose names start with a digit:\n"
            "  # WRONG — Python identifiers cannot start with a digit\n"
            "  from migrations.001_create_users import upgrade  # ← SyntaxError: invalid decimal literal\n"
            "  # CORRECT — do NOT import migration scripts in tests. Only test models and services.\n\n"
            #
            "BUG 11 — passing wrong argument types to service functions in tests:\n"
            "  # WRONG — passing a Settings/config object when function expects simple args\n"
            "  token = create_access_token(settings, user_id)  # ← TypeError\n"
            "  # WRONG — calling with positional args when function uses keyword-only args\n"
            "  token = generate_token('user123', 'secret', 30)  # ← TypeError if kwargs-only\n"
            "  # CORRECT — match the EXACT function signature from the implementation\n"
            "  token = create_access_token(subject='123')\n"
            "  # For JWT tests: use simple string args and keyword arguments.\n"
            "  # Check INTERFACES section for the real signature before writing calls.\n\n"
            #
            "BUG 12 — raising pydantic ValidationError directly (broken in v2):\n"
            "  # WRONG — pydantic v2 ValidationError has NO simple string constructor\n"
            "  raise ValidationError('Invalid email')       # ← TypeError: No constructor defined\n"
            "  raise ValidationError(f'Bad value: {x}')     # ← TypeError: No constructor defined\n"
            "  ValidationError.from_exception_data(...)      # ← complex, fragile, avoid\n"
            "  # CORRECT — use ValueError for custom validation errors\n"
            "  raise ValueError('Invalid email')            # ← simple, works everywhere\n"
            "  # CORRECT — or raise a custom exception class\n"
            "  class EmailValidationError(Exception): pass\n"
            "  raise EmailValidationError('Invalid email')\n"
            "  # In tests: expect ValueError or the custom exception, NOT ValidationError\n"
            "  with pytest.raises(ValueError):\n"
            "      validate_email('bad-input')\n\n"
            #
            "BUG 13 — creating Settings/BaseSettings without mocking env vars:\n"
            "  # WRONG — Settings() reads env vars; if they are missing → ValidationError crash\n"
            "  def test_settings():\n"
            "      s = Settings()  # ← pydantic_core.ValidationError: SECRET_KEY missing!\n"
            "  # CORRECT — always mock env vars BEFORE creating Settings\n"
            "  from unittest.mock import patch\n"
            "  @patch.dict('os.environ', {\n"
            "      'SECRET_KEY': 'test-secret',\n"
            "      'DATABASE_URL': 'sqlite://',\n"
            "      'JWT_SECRET_KEY': 'jwt-test-secret',\n"
            "  })\n"
            "  def test_settings():\n"
            "      s = Settings()\n"
            "      assert s.secret_key == 'test-secret'\n"
            "  # ALSO CORRECT — pass values directly to constructor\n"
            "  def test_settings():\n"
            "      s = Settings(secret_key='test', database_url='sqlite://')\n\n"
            #
            "BUG 14 — writing performance/timing tests for crypto operations:\n"
            "  # WRONG — bcrypt is intentionally slow (100-300ms). Timing tests ALWAYS fail in Docker.\n"
            "  def test_hash_performance_under_50ms():\n"
            "      start = time.time()\n"
            "      hash_password('test')\n"
            "      assert (time.time() - start) * 1000 < 50  # ← ALWAYS FAILS\n"
            "  # CORRECT — do NOT write performance/timing tests. Test behavior only.\n"
            "  def test_hash_password_returns_string():\n"
            "      result = hash_password('test')\n"
            "      assert isinstance(result, str)\n"
            "      assert len(result) > 0\n\n"
            #
            "BUG 15 — asserting exact default message text of exceptions:\n"
            "  # WRONG — fragile, breaks if implementation uses slightly different wording\n"
            "  assert exc.detail == 'Token has expired'     # ← fails if impl says 'Token expired'\n"
            "  assert str(exc) == 'Invalid credentials provided'\n"
            "  # CORRECT — check exception TYPE and status code, not exact message\n"
            "  assert isinstance(exc, ExpiredTokenError)\n"
            "  assert exc.status_code == 401\n"
            "  # ALSO CORRECT — if you must check message, use substring match\n"
            "  assert 'expired' in str(exc.detail).lower()\n\n"
            #
            "BUG 16 — over-testing email validation edge cases:\n"
            "  # WRONG — testing RFC edge cases that email-validator handles differently\n"
            "  # The email-validator library is LENIENT: it accepts dots at start, double dots, etc.\n"
            "  assert not validate('.user@example.com')    # ← email-validator may ACCEPT this\n"
            "  assert not validate('user..name@example.com') # ← email-validator may ACCEPT this\n"
            "  # CORRECT — test only clear-cut cases that ANY validator would agree on\n"
            "  def test_valid_emails():\n"
            "      for email in ['user@example.com', 'a.b@c.com', 'user+tag@example.com']:\n"
            "          assert validate(email)  # clearly valid\n"
            "  def test_invalid_emails():\n"
            "      for email in ['', 'no-at-sign', '@no-local.com', 'user@', 'user @example.com']:\n"
            "          with pytest.raises((ValueError, Exception)):\n"
            "              validate(email)  # clearly invalid\n"
            "  # Do NOT test: leading dots, trailing dots, double dots, IP domains, quoted strings,\n"
            "  # or any RFC 5321 edge case — the library's behavior on these is implementation-specific.\n\n"
            #
            "OUTPUT: Pure Python code only. No markdown fences. No explanations.\n"
            "YOUR FIRST LINE MUST BE: import pytest\n"
            "Then add other imports. Then write test functions."
        )

    def _implementation_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for implementation."""
        task = context["task_spec"]
        test_code = context.get('test_code') or ''

        # Extract import lines from test code to show model what paths to use
        test_imports = [
            line.strip() for line in test_code.split('\n')
            if line.strip().startswith(('from ', 'import '))
            and 'pytest' not in line
            and 'unittest' not in line
            and 'mock' not in line.lower()
        ]

        imports_section = ""
        if test_imports:
            imports_str = chr(10).join(test_imports)
            imports_section = (
                "\nCRITICAL: The test file imports your code like this:\n"
                f"{imports_str}\n"
                "Your implementation MUST be importable at these exact paths.\n"
            )

        interfaces_str = json.dumps(context['interfaces'], indent=2)
        criteria_str = ', '.join(task.get('done_criteria', []))

        # P0: Real workspace context
        workspace_ctx = context.get("workspace_context") or ""

        prompt = (
            "Implement this task. The tests below must pass.\n\n"
            f"TASK: {task['name']}\n"
            f"FILES TO CREATE: {', '.join(task['files'])}\n"
            f"{imports_section}\n"
            # ── P0: Workspace context injected here ──
            + (f"{workspace_ctx}\n\n" if workspace_ctx else "")
            +
            f"DONE CRITERIA: {criteria_str}\n\n"
            f"INTERFACES:\n{interfaces_str}\n\n"
            f"TESTS (your code MUST pass these):\n{test_code[:2500]}\n\n"
            f"{AVAILABLE_PACKAGES}\n"
            "RULES:\n"
            "- Write ONLY the implementation code\n"
            "- Make sure your module is importable at the path the tests expect\n"
            "- CRITICAL PYTHON RULE: Define ALL classes and functions BEFORE referencing them.\n"
            "  Module-level code runs top-to-bottom. A class name used before its 'class' statement\n"
            "  causes NameError. WRONG:\n"
            "    _instance: Config | None = None  # ← NameError, Config not yet defined!\n"
            "    class Config: ...\n"
            "  CORRECT:\n"
            "    class Config: ...                 # ← define class FIRST\n"
            "    _instance: Config | None = None   # ← now it works\n"
            "- For singleton/get_settings patterns, put the cache variable and getter AFTER the class:\n"
            "    class Settings(BaseSettings): ...\n"
            "    _settings = None\n"
            "    def get_settings(): ...\n"
            "- Do NOT create global instances that require env vars or DB connections at import time\n"
            "- Use dependency injection or lazy initialization instead\n"
            "- When importing from other project modules, ONLY use paths listed in EXISTING MODULES\n"
            "- If a needed dependency doesn't exist yet, define the class/function locally\n"
            "- For SQLAlchemy models: ALWAYS define AND EXPORT Base in your module:\n"
            "    from sqlalchemy.orm import DeclarativeBase\n"
            "    class Base(DeclarativeBase): pass    # ← CORRECT: subclass it\n"
            "  WRONG patterns (will crash with TypeError):\n"
            "    Base = DeclarativeBase()              # ← WRONG: DeclarativeBase() takes no arguments\n"
            "    Base = declarative_base()              # ← WRONG: deprecated, removed in SQLAlchemy 2.0\n"
            "    from sqlalchemy.ext.declarative import declarative_base  # ← WRONG: removed\n"
            "  Do NOT import Base from another module unless it appears in EXISTING MODULES.\n"
            "  Tests will import Base from your module: 'from src.auth.models import Base, User'\n"
            "- For JWT: use 'import jwt' and algorithm='HS256' with a string secret key.\n"
            "  Do NOT use RS256 (requires RSA key pair). Do NOT use python-jose.\n"
            "- PYDANTIC V2 ONLY — the following are REMOVED and will crash:\n"
            "    @validator → use @field_validator instead (from pydantic import field_validator)\n"
            "    @root_validator → use @model_validator instead\n"
            "    from pydantic import validator → DOES NOT EXIST in V2\n"
            "    from pydantic import EmailError → DOES NOT EXIST in V2\n"
            "  Correct imports: from pydantic import BaseModel, Field, field_validator, ValidationError\n"
            "  Correct imports: from pydantic_settings import BaseSettings (ONLY BaseSettings from here)\n"
            "  For email validation: from email_validator import validate_email, EmailNotValidError\n\n"
            "- NEVER raise ValidationError() directly — pydantic v2 has NO simple string constructor.\n"
            "  raise ValidationError('msg') → TypeError: No constructor defined\n"
            "  Instead: raise ValueError('msg') or define a custom exception class.\n"
            "- For Settings (BaseSettings subclass): set defaults or use env_default for ALL fields,\n"
            "  so the class can be instantiated in tests without setting env vars.\n\n"
            "OUTPUT: Pure Python code only. No markdown fences. No explanations. "
            "Start with import statements."
        )

        iteration = context.get("iteration", 1)
        if iteration > 1:
            prev_code = (context.get('previous_code') or '')[:1500]
            error_out = (context.get('error_output') or '')[:1500]
            prompt += (
                f"\n\n=== ITERATION {iteration} -- FIX THE ERRORS BELOW ===\n\n"
                f"YOUR PREVIOUS CODE:\n{prev_code}\n\n"
                f"TEST OUTPUT / ERRORS:\n{error_out}\n\n"
                "Analyze the errors above. Fix your code so the tests pass. "
                "Common issues: wrong import path, missing class/function, "
                "wrong signature, unhandled edge case."
            )

        return prompt

    def _single_call_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for single-call implementation + tests generation."""
        task = context["task_spec"]
        interfaces_str = json.dumps(context['interfaces'], indent=2)
        criteria_str = chr(10).join('- ' + c for c in task.get('done_criteria', []))
        workspace_ctx = context.get("workspace_context") or ""
        dep_sources = context.get("dependency_sources") or ""

        # Build import hints from file paths
        import_hints = []
        for f in task.get('files', []):
            module_path = f.replace('/', '.').replace('.py', '')
            if module_path.endswith('.__init__'):
                module_path = module_path[:-len('.__init__')]
            parts = module_path.split('.')
            if any(part[:1].isdigit() for part in parts):
                continue
            import_hints.append(f"from {module_path} import ...")
        import_hints_str = chr(10).join(import_hints)

        impl_files = ', '.join(task.get('files', []))
        test_file = task.get('test_file', 'tests/unit/test_module.py')

        prompt = (
            "Generate BOTH the implementation AND pytest tests for this task.\n\n"
            f"TASK: {task['name']}\n"
            f"DESCRIPTION: {task.get('description', '')}\n"
            f"IMPLEMENTATION FILES: {impl_files}\n"
            f"TEST FILE: {test_file}\n\n"
            f"DONE CRITERIA:\n{criteria_str}\n\n"
            f"INTERFACES:\n{interfaces_str}\n\n"
            + (f"{workspace_ctx}\n\n" if workspace_ctx else "")
            + (f"{dep_sources}\n\n" if dep_sources else "")
            + f"{AVAILABLE_PACKAGES}\n"
            "CRITICAL RULES:\n"
            "- Your tests MUST import from the EXACT paths of your implementation\n"
            "- Your tests MUST use the EXACT class/function names from your implementation\n"
            "- PYDANTIC V2: use BaseModel, Field, field_validator (NOT @validator)\n"
            "- PYDANTIC V2: from pydantic_settings import BaseSettings (ONLY BaseSettings from here)\n"
            "- PYDANTIC V2: NEVER raise ValidationError() — use ValueError() instead\n"
            "- SQLAlchemy 2.0: class Base(DeclarativeBase): pass (NOT Base = DeclarativeBase())\n"
            "- JWT: use 'import jwt', algorithm='HS256', string secret key. NOT RS256.\n"
            "- For Settings (BaseSettings): provide defaults for ALL fields so tests work without env vars\n"
            "- Tests: use pytest, unittest.mock. Do NOT mock stdlib internals (bcrypt, jwt, hashlib)\n"
            "- Tests: do NOT write performance/timing tests. Test behavior only.\n"
            "- Tests: check exception TYPE and status code, NOT exact message text\n"
            "- Tests: do NOT check __repr__ output of exceptions — repr format is implementation-dependent\n"
            "- Tests: do NOT assert exact string content of repr(), str(), or error messages\n"
            "- Tests: for email validation, only test clear-cut valid/invalid cases\n"
            "- Tests: for Settings, use @patch.dict('os.environ', {...}) or pass values to constructor\n"
            "- Tests: each test must be independent. Use fixtures for shared setup.\n\n"
            "OUTPUT FORMAT — you MUST use these EXACT markers:\n\n"
            f"=== IMPLEMENTATION: {impl_files.split(',')[0].strip()} ===\n"
            "<your implementation code here>\n\n"
            f"=== TESTS: {test_file} ===\n"
            "<your test code here>\n\n"
            "Rules for output:\n"
            "- Pure Python code only inside each section\n"
            "- No markdown fences (no ```python)\n"
            "- Implementation starts with imports\n"
            "- Tests start with 'import pytest'\n"
            "- Both sections are REQUIRED\n"
        )

        iteration = context.get("iteration", 1)
        if iteration > 1:
            prev_impl = (context.get('previous_impl') or '')[:6000]
            prev_tests = (context.get('previous_tests') or '')[:6000]
            error_out = (context.get('error_output') or '')[:2000]

            # Extract just the FAILED/ERROR test names for focused fixing
            failed_tests = re.findall(r'(?:FAILED|ERROR) tests/\S+::(\S+)', error_out)
            failed_list = '\n'.join(f'  - {t}' for t in failed_tests[:10])

            prompt += (
                f"\n\n=== ITERATION {iteration} — MINIMAL FIX ONLY ===\n\n"
                f"YOUR CURRENT IMPLEMENTATION (this mostly works — do NOT rewrite from scratch):\n{prev_impl}\n\n"
                f"YOUR CURRENT TESTS (most of these PASS — do NOT rewrite passing tests):\n{prev_tests}\n\n"
                f"FAILING TESTS:\n{failed_list}\n\n"
                f"ERROR OUTPUT:\n{error_out}\n\n"
                "CRITICAL RULES FOR THIS FIX:\n"
                "1. Keep ALL passing tests EXACTLY as they are — do not rename, reorder, or rewrite them\n"
                "2. Fix ONLY the failing tests listed above, or fix the implementation to make them pass\n"
                "3. Do NOT add new test classes or test functions that didn't exist before\n"
                "4. Do NOT change function signatures, class names, or import paths that work\n"
                "5. Make the SMALLEST possible change to fix the failures\n"
                "6. Output the COMPLETE files (implementation + tests) with your minimal fixes applied\n"
            )

        return prompt

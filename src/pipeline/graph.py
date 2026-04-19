"""Main LangGraph pipeline orchestration."""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from langgraph.graph import StateGraph, END

from src.config import config, get_logger
from src.pipeline.state import PipelineState
from src.pipeline.router import Router
from src.pipeline.escalator import Escalator
from src.pipeline.context_builder import ContextBuilder
from src.models import OllamaClient, OpenRouterClient
from src.docker import DockerRunner
from src.artifacts import ArtifactLoader
from src.pipeline.json_parser import parse_llm_json
from src.pipeline.safety_nets import fix_impl_code, fix_test_code


logger = get_logger(__name__)


def _looks_like_task(item: dict) -> bool:
    """Check if a dict looks like a task definition."""
    task_keys = {"id", "task_id", "name", "title", "files", "module", "depends_on", "dependencies", "done_criteria"}
    return isinstance(item, dict) and len(set(item.keys()) & task_keys) >= 2


def _extract_tasks_from_data(data) -> list:
    """
    Recursively extract task-like dicts from arbitrary JSON structures.
    
    Handles formats like:
      {"tasks": [...]}
      {"task_graph": [...]}
      {"task_graph": {"tasks": [...]}}
      {"task_graph": {"phases": [{"tasks": [...]}]}}
      {"phases": [{"name": "...", "tasks": [...]}]}
      [task1, task2, ...]   (direct list)
    """
    if isinstance(data, list):
        if data and _looks_like_task(data[0]):
            return data
        result = []
        for item in data:
            result.extend(_extract_tasks_from_data(item))
        return result

    if not isinstance(data, dict):
        return []

    for key in ("tasks", "task_graph", "graph", "nodes", "phases", "stages",
                "implementation_order", "steps"):
        if key not in data:
            continue
        val = data[key]

        if isinstance(val, list):
            if val and _looks_like_task(val[0]):
                return val
            nested = []
            for item in val:
                nested.extend(_extract_tasks_from_data(item))
            if nested:
                return nested

        elif isinstance(val, dict):
            nested = _extract_tasks_from_data(val)
            if nested:
                return nested

    for key, val in data.items():
        if isinstance(val, list) and val and _looks_like_task(val[0]):
            return val

    return []


def _extract_code_from_response(response: str) -> str:
    """
    Extract Python code from an LLM response.
    Handles markdown code blocks, explanatory text, etc.
    """
    if not response:
        return ""

    blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', response, re.DOTALL)
    if blocks:
        return max(blocks, key=len).strip()

    lines = response.strip().split('\n')
    code_indicators = ('import ', 'from ', 'def ', 'class ', '#', '@', 'async ')
    if any(lines[0].startswith(ind) for ind in code_indicators):
        return response.strip()

    return response.strip()


def _write_code_to_file(filepath: str, code: str, project_root: Path) -> bool:
    """Write generated code to a file, creating directories as needed."""
    try:
        full_path = project_root / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(code, encoding='utf-8')

        for parent in full_path.relative_to(project_root).parents:
            if parent != Path('.'):
                init_file = project_root / parent / '__init__.py'
                if not init_file.exists():
                    init_file.write_text('', encoding='utf-8')

        return True
    except Exception as e:
        logger.error(f"Failed to write {filepath}: {e}")
        return False


def _parse_single_call_response(response: str) -> tuple[dict[str, str], str]:
    """
    Parse a single-call LLM response into (implementation_code_by_file, test_code).

    Supports both:
      - single implementation section
      - multi-file implementation sections:
          === IMPLEMENTATION: src/a.py ===
          ...
          === IMPLEMENTATION: src/b.py ===
          ...
          === TESTS: tests/unit/test_x.py ===
          ...

    Falls back to code-block extraction if markers are not found.
    """
    if not response:
        return {}, ""

    section_pattern = re.compile(
        r"===\s*(IMPLEMENTATION|TESTS)\s*:\s*([^=\n]+?)\s*===\s*\n",
        re.IGNORECASE,
    )
    matches = list(section_pattern.finditer(response))
    if matches:
        implementations: dict[str, str] = {}
        test_code = ""

        for idx, match in enumerate(matches):
            section_type = match.group(1).upper()
            section_file = match.group(2).strip()
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(response)
            section_body = response[start:end].strip()

            code = _extract_code_from_response(section_body) if "```" in section_body else section_body
            if section_type == "IMPLEMENTATION":
                if section_file:
                    implementations[section_file] = code
            elif section_type == "TESTS":
                test_code = code

        if implementations or test_code:
            return implementations, test_code

    # Fallback: try to split on code blocks with filename hints
    blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', response, re.DOTALL)
    if len(blocks) >= 2:
        # Heuristic: first block with 'class/def' is impl, block with 'test_' is tests
        impl_block = None
        test_block = None
        for block in blocks:
            if 'def test_' in block or 'import pytest' in block:
                test_block = block.strip()
            elif impl_block is None:
                impl_block = block.strip()
        if impl_block and test_block:
            return {"__default__": impl_block}, test_block
        # Just take first two
        return {"__default__": blocks[0].strip()}, blocks[1].strip()

    # Last resort: try to find the split point
    if 'import pytest' in response:
        idx = response.index('import pytest')
        # Walk back to find a blank line boundary
        before = response[:idx].rstrip()
        after = response[idx:].strip()
        if before and after:
            return {"__default__": _extract_code_from_response(before)}, after

    return {"__default__": _extract_code_from_response(response)}, ""


# ---------------------------------------------------------------------------
# Test-bug detection heuristics (Group C + P3)
# ---------------------------------------------------------------------------

# Patterns that ALWAYS indicate a test bug (no exclusions needed)
_TEST_BUG_PATTERNS_SAFE = [
    # called_once_with (silent no-op)
    (r"\.called_once_with\(",
     "Test uses .called_once_with() — should be .assert_called_once_with()"),
    # SyntaxError during test collection
    (r"SyntaxError:",
     "Test file has a syntax error"),
    # Explicit __init__ in import path
    (r"from \S+\.__init__\s+import",
     "Test imports from __init__ explicitly — should drop .__init__"),
    # "object is not callable"
    (r"object is not callable",
     "Test calls an object that is not callable — likely wrong API usage in test"),
    # TypeError: No constructor defined (pydantic v2 ValidationError)
    (r"TypeError: No constructor defined",
     "Test raises pydantic ValidationError() directly — must use ValueError instead"),
    # pydantic_core ValidationError during test ERROR (Settings without env vars)
    (r"ERROR tests/.*pydantic_core\._pydantic_core\.Validation",
     "Test triggers pydantic ValidationError — likely creating Settings without env var mock"),
    # TypeError in ERROR or FAILED lines (test calls API with wrong signature)
    (r"(?:ERROR|FAILED) tests/.*TypeError",
     "Test has TypeError — likely calling function with wrong arguments"),
    # No tests collected (exit_code=5)
    (r"no tests ran",
     "No tests collected — test file has no valid test functions"),
    # Performance/timing assertions (bcrypt is slow in Docker)
    (r"assert \d+\.\d+ < \d+",
     "Test has timing assertion — performance tests are unreliable in Docker"),
]

# Patterns that match import errors — need task-file exclusion to avoid false positives.
# If the failing import is for the task's OWN implementation file, the error is in the
# implementation (not the test), so we must NOT regenerate the test.
_TEST_BUG_IMPORT_PATTERN = (
    r"tests/.*\.py:\d+: in <module>\s*\n\s*from (src\.\S+) import"
)


def _task_files_to_modules(task_files: list) -> set:
    """Convert task file paths to module paths for comparison.
    
    'src/config.py' → 'src.config'
    'src/auth/schemas.py' → 'src.auth.schemas'
    """
    modules = set()
    for f in task_files:
        mod = f.replace("/", ".").replace(".py", "")
        modules.add(mod)
    return modules


def _should_regenerate_test(error_output: str, test_file: str, iteration: int,
                            prev_errors: list, task_files: list = None) -> tuple:
    """
    Decide whether the TEST itself is buggy (vs. the implementation).

    Returns (should_regen: bool, reason: str).
    
    IMPORTANT: Import errors that point to the task's OWN implementation files
    are NOT test bugs — they mean the implementation crashed at import time.
    """
    if not error_output:
        return False, ""

    task_modules = _task_files_to_modules(task_files or [])

    # 1. Check safe patterns (always indicate test bug)
    for pattern, reason_tpl in _TEST_BUG_PATTERNS_SAFE:
        m = re.search(pattern, error_output)
        if m:
            reason = reason_tpl.format(*m.groups()) if m.groups() else reason_tpl
            logger.info(f"Test-bug detected: {reason}")
            return True, reason

    # 1b. No tests collected (exit_code=5): output has no FAILED/ERROR/passed lines
    has_test_results = bool(
        re.search(r"(FAILED |ERROR tests/|\d+ passed)", error_output)
    )
    if not has_test_results and error_output.strip():
        logger.info("Test-bug detected: no test results in output (likely no tests collected)")
        return True, "No test results — likely no tests collected (exit_code=5)"

    # 2. Check import-error pattern WITH task-file exclusion
    m = re.search(_TEST_BUG_IMPORT_PATTERN, error_output)
    if m:
        imported_module = m.group(1)
        # Strip trailing punctuation that regex might capture
        imported_module = imported_module.rstrip(".,;:)")
        
        if imported_module in task_modules:
            # The test imports the task's own file, which crashed at import time.
            # This is an IMPLEMENTATION bug, not a test bug.
            logger.debug(f"Import error in task's own module {imported_module} — not a test bug")
        else:
            # The test imports a module that is NOT this task's file — likely wrong path
            logger.info(f"Test-bug detected: Test imports from non-existent module '{imported_module}'")
            return True, f"Test imports from non-existent module '{imported_module}'"

    # 3. Check NameError IN the test file itself (not cascading from implementation)
    #    Only trigger if the NameError line points to the test file, not src/ files
    test_file_base = test_file.split("/")[-1] if test_file else ""
    if test_file_base:
        # Match: test_file.py:42: in test_something\n    code_line\nE   NameError: ...
        pattern = rf"({re.escape(test_file_base)}:\d+: in (?!<module>)(\w+).*\n.*\nE\s+NameError)"
        if re.search(pattern, error_output):
            return True, f"NameError originates in test function ({test_file_base})"

    # 4. Same error message repeated across 2+ iterations → probably a test bug
    if len(prev_errors) >= 2 and iteration >= 3:
        def _extract_summary(err: str) -> str:
            lines = err.strip().split('\n')
            for line in lines:
                if line.startswith(("FAILED ", "ERROR tests/")):
                    return line.strip()
            return ""

        summaries = [_extract_summary(e) for e in prev_errors[-2:]]
        current_summary = _extract_summary(error_output)
        if current_summary and all(s == current_summary for s in summaries):
            return True, f"Same failure repeated {len(summaries)+1} iterations — likely test bug"

    return False, ""


def _build_stuck_hint(error_output: str, iters_stuck: int) -> str:
    """Build a hint to inject into the error output when the model is stuck.

    Analyzes the error pattern and gives targeted advice so the model
    tries a fundamentally different approach instead of repeating the same fix.
    """
    hints = [
        f"\n\n=== STUCK DETECTION: You have produced the SAME error for {iters_stuck}+ iterations ===\n",
        "Your previous approach is NOT working. You MUST try something FUNDAMENTALLY DIFFERENT.\n",
    ]

    # Pattern-specific hints
    if "DID NOT RAISE" in error_output:
        # Test expects an exception that impl doesn't raise
        exc_match = re.search(r"DID NOT RAISE <class '([^']+)'>", error_output)
        exc_name = exc_match.group(1).split(".")[-1] if exc_match else "the expected exception"
        hints.append(
            f"SPECIFIC ISSUE: Your test expects {exc_name} to be raised, but your implementation "
            f"does NOT raise it. You have two choices:\n"
            f"  1. FIX THE IMPLEMENTATION to actually raise {exc_name} for invalid inputs\n"
            f"  2. FIX THE TEST to match what your implementation actually does "
            f"(e.g. returns None, returns False, raises a different exception)\n"
            f"Pick whichever makes the code correct. Do NOT just repeat your previous attempt.\n"
        )

    if "AssertionError: assert" in error_output or "AssertionError" in error_output:
        hints.append(
            "SPECIFIC ISSUE: An assertion is failing — the actual value doesn't match expected.\n"
            "Either fix the implementation to return the expected value, or fix the test's expectation.\n"
        )

    if "AttributeError:" in error_output:
        attr_match = re.search(r"AttributeError: '(\w+)' object has no attribute '(\w+)'", error_output)
        if attr_match:
            hints.append(
                f"SPECIFIC ISSUE: '{attr_match.group(1)}' has no attribute '{attr_match.group(2)}'.\n"
                f"Your test assumes an API that doesn't exist. Change the test OR the implementation.\n"
            )

    if "TypeError:" in error_output:
        hints.append(
            "SPECIFIC ISSUE: TypeError — wrong argument types or wrong number of arguments.\n"
            "Your test and implementation disagree on the function signature. Align them.\n"
        )

    if "is an invalid keyword argument" in error_output:
        kw_match = re.search(r"'(\w+)' is an invalid keyword argument for (\w+)", error_output)
        if kw_match:
            hints.append(
                f"SPECIFIC ISSUE: '{kw_match.group(2)}' does not accept '{kw_match.group(1)}' as a field.\n"
                f"Check your model class definition — does it actually have this column/field?\n"
            )

    hints.append(
        "STRATEGY: Rewrite BOTH the implementation AND the failing test from scratch for the "
        "failing functionality. Keep all passing tests exactly as-is.\n"
    )

    return "\n".join(hints)


class PipelineOrchestrator:
    """Main pipeline orchestrator using LangGraph."""

    def __init__(self):
        self.context_builder = ContextBuilder()
        self.router = Router()
        self.escalator = Escalator()
        self.artifact_loader = ArtifactLoader()
        self.ollama = OllamaClient()
        self.openrouter = OpenRouterClient()
        self.docker_runner = DockerRunner()

    async def execute_spec_review(self, state: PipelineState) -> PipelineState:
        """Stage 0: Spec review (human checkpoint A)."""
        logger.info(f"[{state['execution_id']}] Entering spec review stage")

        state["current_stage"] = "intake"
        state["status"] = "in_progress"
        state["human_approval_required"] = True

        return state

    async def execute_architecture(self, state: PipelineState) -> PipelineState:
        """Stage 1: Design architecture (human checkpoint B)."""
        logger.info(f"[{state['execution_id']}] Designing architecture")

        state["current_stage"] = "architecture"
        state["status"] = "in_progress"

        context = self.context_builder.for_architecture(state["spec"])
        prompt = self.context_builder.assemble_prompt(context)

        logger.info("Routing architecture to cloud (high value reasoning)")

        try:
            response = await self.openrouter.generate_async(
                prompt=prompt,
                model=config.openrouter_model,
                temperature=0.2,
                max_tokens=8000,
            )

            state["response"] = response
            state["architecture"] = {"raw": response}
            state["status"] = "succeeding"

        except Exception as e:
            logger.error(f"Architecture generation failed: {e}")
            state["last_error"] = str(e)
            state["status"] = "failing"

        state["human_approval_required"] = True
        return state

    async def execute_decomposition(self, state: PipelineState) -> PipelineState:
        """Stage 2: Decompose into tasks."""
        logger.info(f"[{state['execution_id']}] Decomposing architecture into tasks")

        state["current_stage"] = "decomposition"
        state["status"] = "in_progress"

        # --- P3: Cache decomposition — if TASK_GRAPH.json exists, reuse it ---
        task_graph_path = config.artifacts_dir / "TASK_GRAPH.json"
        if task_graph_path.exists():
            try:
                cached = json.loads(task_graph_path.read_text(encoding="utf-8"))
                tasks = cached if isinstance(cached, list) else cached.get("tasks", [])
                if tasks:
                    logger.info(f"Loaded cached decomposition from {task_graph_path} ({len(tasks)} tasks)")
                    state["task_graph"] = tasks
                    state["current_task_index"] = 0
                    state["current_task"] = tasks[0]
                    state["status"] = "succeeding"
                    logger.info(f"Starting with task {tasks[0]['id']}: {tasks[0]['name']}")
                    return state
            except Exception as e:
                logger.warning(f"Failed to load cached TASK_GRAPH.json, regenerating: {e}")

        logger.info("Routing decomposition to cloud")

        context = self.context_builder.for_decomposition(state["architecture"])
        prompt = self.context_builder.assemble_prompt(context)

        try:
            response = await self.openrouter.generate_async(
                prompt=prompt,
                model=config.openrouter_model,
                temperature=0.2,
                max_tokens=8000,
            )

            state["response"] = response

            logger.info(f"Decomposition response length: {len(response)}")
            logger.debug(f"Decomposition response: {response[:500]}...")

            task_data = parse_llm_json(response)

            if task_data is None:
                logger.warning("JSON parse failed, retrying with explicit JSON instruction")
                retry_response = await self.openrouter.generate_async(
                    prompt=prompt + "\n\nCRITICAL: Respond with ONLY a valid JSON object. "
                           "No text before or after. No markdown fences. "
                           "Start with { and end with }. "
                           "Keep it compact — no unnecessary whitespace or long descriptions.",
                    model=config.openrouter_model,
                    temperature=0.1,
                    max_tokens=8000,
                )
                task_data = parse_llm_json(retry_response)

            if task_data is None:
                logger.error("All JSON parsing attempts failed")
                state["task_graph"] = []
                state["last_error"] = "Invalid JSON in decomposition response after retry"
                state["status"] = "failing"
                return state

            logger.info(f"Parsed JSON keys: {list(task_data.keys()) if isinstance(task_data, dict) else 'array'}")

            raw_tasks = _extract_tasks_from_data(task_data)

            if not raw_tasks:
                if isinstance(task_data, dict):
                    for k, v in task_data.items():
                        vtype = type(v).__name__
                        vlen = len(v) if isinstance(v, (list, dict, str)) else "N/A"
                        logger.warning(f"  key '{k}': type={vtype}, len={vlen}")
                logger.warning("No tasks extracted from parsed JSON")

            logger.info(f"Found {len(raw_tasks)} raw tasks")

            tasks = []
            for raw_task in raw_tasks:
                task = {
                    "id": raw_task.get("id", raw_task.get("task_id", f"T{len(tasks)+1:03d}")),
                    "name": raw_task.get("name", raw_task.get("title", raw_task.get("description", "Unnamed task"))),
                    "module": raw_task.get("module", ""),
                    "files": raw_task.get("files", []),
                    "depends_on": raw_task.get("depends_on", raw_task.get("dependencies", [])),
                    "size": raw_task.get("size", "M"),
                    "risk_level": raw_task.get("risk_level", "medium"),
                    "description": raw_task.get("description", raw_task.get("title", "")),
                    "done_criteria": raw_task.get("done_criteria", []),
                    "test_file": raw_task.get("test_file", f"tests/test_{raw_task.get('module', 'task')}.py"),
                }
                tasks.append(task)

            logger.info(f"Normalized {len(tasks)} tasks")

            # Hard cap: too many tasks create cascade failures
            MAX_TASKS = 15
            if len(tasks) > MAX_TASKS:
                logger.warning(f"Decomposition produced {len(tasks)} tasks, capping at {MAX_TASKS}")
                tasks = tasks[:MAX_TASKS]

            state["task_graph"] = tasks

            # --- P3: Save to TASK_GRAPH.json for future runs ---
            try:
                task_graph_path.parent.mkdir(parents=True, exist_ok=True)
                task_graph_path.write_text(
                    json.dumps({"tasks": tasks}, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                logger.info(f"Saved decomposition to {task_graph_path}")
            except Exception as e:
                logger.warning(f"Failed to save TASK_GRAPH.json: {e}")

            if tasks:
                state["current_task_index"] = 0
                state["current_task"] = tasks[0]
                logger.info(f"Starting with task {tasks[0]['id']}: {tasks[0]['name']}")
            else:
                logger.warning("No tasks found in parsed JSON")

            state["status"] = "succeeding"

        except Exception as e:
            logger.error(f"Decomposition failed, escalating: {e}")
            state["last_error"] = str(e)
            state["status"] = "failing"

        return state

    async def execute_task(self, state: PipelineState) -> PipelineState:
        """Execute all tasks in sequence."""

        tasks = state.get("task_graph", [])
        if not tasks:
            logger.warning("No tasks to execute")
            state["status"] = "done"
            return state

        current_index = state.get("current_task_index", 0)

        # Track per-task results for honest reporting
        task_results = []
        # P1: Track failed task IDs so dependents can be skipped
        failed_task_ids = set()

        for i in range(current_index, len(tasks)):
            task = tasks[i]
            state["current_task"] = task
            state["current_task_index"] = i

            logger.info(f"[{state['execution_id']}] Executing task {i+1}/{len(tasks)}: {task['id']} - {task['name']}")

            # --- P1: Skip tasks whose dependencies failed ---
            depends_on = task.get("depends_on") or []
            blocked_by = [dep for dep in depends_on if dep in failed_task_ids]
            if blocked_by:
                reason = f"Skipped: depends on failed task(s) {', '.join(blocked_by)}"
                logger.warning(f"⊘ {task['id']}: {reason}")
                task_results.append({
                    "id": task["id"],
                    "name": task["name"],
                    "passed": False,
                    "skipped": True,
                    "reason": reason,
                })
                failed_task_ids.add(task["id"])
                continue

            # Execute single task
            task_result = await self._execute_single_task(state)

            passed = task_result.get("test_passed", False)
            task_results.append({
                "id": task["id"],
                "name": task["name"],
                "passed": passed,
                "skipped": False,
                "reason": "" if passed else (task_result.get("last_error") or "unknown")[-200:],
            })

            if not passed:
                failed_task_ids.add(task["id"])
                logger.warning(f"Task {task['id']} failed, continuing to next task")
                state["status"] = "in_progress"

        # --- Honest summary ---
        passed_count = sum(1 for r in task_results if r["passed"])
        skipped_count = sum(1 for r in task_results if r.get("skipped"))
        failed_count = len(task_results) - passed_count - skipped_count

        logger.info(f"[{state['execution_id']}] Task execution complete: "
                     f"{passed_count}/{len(task_results)} passed, "
                     f"{failed_count} failed, {skipped_count} skipped")

        for r in task_results:
            if r["passed"]:
                icon = "✓"
            elif r.get("skipped"):
                icon = "⊘"
            else:
                icon = "✗"
            logger.info(f"  {icon} {r['id']}: {r['name']}"
                        + (f" — {r['reason'][:100]}" if not r["passed"] else ""))

        state["task_results"] = task_results
        state["status"] = "done" if (failed_count + skipped_count) == 0 else "done_with_errors"
        return state

    async def _execute_single_task(self, state: PipelineState) -> PipelineState:
        """Execute a single task using single-call (impl + tests in one LLM call)."""
        task = state["current_task"]

        logger.info(f"[{state['execution_id']}] Starting task {task['id']}: {task['name']}")

        # Reset task-level state to prevent leaks between tasks
        state["test_passed"] = False
        state["test_code"] = None
        state["test_code_clean"] = None
        state["implementation_code"] = None
        state["implementation_code_clean"] = None
        state["last_error"] = None
        state["error_count"] = 0
        state["iteration"] = 0
        state["test_results"] = None
        state["model_tier"] = None
        state["response"] = None

        # Special case: if test_file IS the implementation file (e.g. conftest.py)
        task_files = task.get("files", [])
        test_file = task.get("test_file", "")
        if test_file and test_file in task_files:
            logger.info(f"Task {task['id']}: test_file == implementation file ({test_file}), generating directly")
            state = await self._generate_tests(state)
            if state.get("test_code_clean"):
                state["test_passed"] = True
                state["status"] = "succeeding"
                logger.info(f"✓ Task {task['id']} auto-passed (test_file == impl file)")
                return state

        # ── SINGLE-CALL LOOP ──
        max_iterations = config.max_iterations_per_task + 5  # complex tasks need room to converge

        # Best-result tracking: prevent LLM from regressing
        # Uses composite score: (passed_count, -failed_count) — higher is better.
        # A collection error (SyntaxError, 0 passed) is NEVER treated as "best"
        # because it means no tests actually ran.
        best_score = (-1, -999)  # (passed, -failed) — impossibly bad default
        best_impl = None
        best_tests = None
        best_error = None

        # Stuck detection: if best_score hasn't improved for N iterations,
        # the rollback target itself is the problem — reset and try fresh.
        iters_since_improvement = 0
        STUCK_THRESHOLD = 2  # reset after 2 iterations without progress

        for iteration in range(1, max_iterations + 1):
            state["iteration"] = iteration
            logger.info(f"Single-call iteration {iteration}/{max_iterations}")

            # Generate impl + tests in one call
            success = await self._generate_impl_and_tests(state)
            if not success:
                logger.warning(f"Task {task['id']}: Generation failed on iteration {iteration}, retrying...")
                continue  # retry instead of giving up

            # Run tests
            await self._run_tests(state)

            if state.get("test_passed"):
                logger.info(f"✓ Task {task['id']} passed on iteration {iteration}")
                state["status"] = "succeeding"
                return state

            # Count failures AND passes for composite score
            error_output = state.get("last_error") or ""
            current_failed = len(re.findall(r'(?:FAILED|ERROR) tests/', error_output))
            passed_match = re.search(r'(\d+) passed', error_output)
            current_passed = int(passed_match.group(1)) if passed_match else 0

            # Composite score: more passes is better; fewer failures breaks ties
            current_score = (current_passed, -current_failed)

            if current_score > best_score:
                # Genuine progress — save as new best
                best_score = current_score
                best_impl = state.get("implementation_code_clean") or ""
                best_tests = state.get("test_code_clean") or ""
                best_error = error_output
                iters_since_improvement = 0
                logger.info(f"New best: {current_passed} passed, {current_failed} failures")
            elif current_score < best_score and best_impl:
                iters_since_improvement += 1

                # Stuck detection: no improvement for N iterations — reset best
                # AND inject a hint so the model tries a different approach
                if iters_since_improvement >= STUCK_THRESHOLD:
                    hint = _build_stuck_hint(error_output, iters_since_improvement)
                    logger.warning(
                        f"Stuck: no improvement for {iters_since_improvement} iterations "
                        f"(best {best_score[0]}p/{-best_score[1]}f) — resetting with hint"
                    )
                    best_score = current_score
                    best_impl = state.get("implementation_code_clean") or ""
                    best_tests = state.get("test_code_clean") or ""
                    best_error = error_output
                    # Inject hint into last_error so the model sees it on next iteration
                    state["last_error"] = error_output + hint
                    iters_since_improvement = 0
                else:
                    # Normal regression — rollback to best version
                    logger.warning(f"Regression: {current_passed}p/{current_failed}f "
                                   f"< {best_score[0]}p/{-best_score[1]}f — rolling back")
                    state["implementation_code_clean"] = best_impl
                    state["test_code_clean"] = best_tests
                    state["last_error"] = best_error
            else:
                # Same score — count as no improvement too
                iters_since_improvement += 1
                if iters_since_improvement >= STUCK_THRESHOLD:
                    hint = _build_stuck_hint(error_output, iters_since_improvement)
                    logger.warning(
                        f"Plateau: same score for {iters_since_improvement} iterations — injecting hint"
                    )
                    # Inject hint — do NOT reset best (same score means best IS this version)
                    state["last_error"] = error_output + hint
                    iters_since_improvement = 0

            if error_output:
                logger.info(f"Test error (tail): {error_output[-500:]}")

        state["status"] = "failing"
        state["last_error"] = f"Max iterations ({max_iterations}) exceeded"
        return state

    async def _generate_impl_and_tests(self, state: PipelineState) -> bool:
        """Generate implementation and tests in a single LLM call.
        
        Returns True if generation succeeded, False otherwise.
        """
        task = state["current_task"]
        iteration = state.get("iteration", 1)

        context = self.context_builder.for_single_call(
            task,
            iteration=iteration,
            previous_impl=state.get("implementation_code_clean") if iteration > 1 else None,
            previous_tests=state.get("test_code_clean") if iteration > 1 else None,
            error_output=state.get("last_error") if iteration > 1 else None,
        )
        prompt = self.context_builder.assemble_prompt(context)

        try:
            response = await self.openrouter.generate_async(
                prompt=prompt,
                model=config.openrouter_model,
                temperature=0.1,
                max_tokens=12000,
            )

            if not response or not response.strip():
                logger.error("Cloud model returned empty response for single-call")
                state["last_error"] = "Cloud model returned empty response"
                return False

            state["response"] = response

            # Parse response into impl + tests
            impl_code_map, test_code = _parse_single_call_response(response)

            if not impl_code_map:
                logger.error("Failed to extract implementation from single-call response")
                state["last_error"] = "No implementation code in response"
                return False

            if not test_code:
                logger.error("Failed to extract tests from single-call response")
                state["last_error"] = "No test code in response"
                return False

            required_impl_files = task.get("files", [])

            # Single-file fallback compatibility for non-marker responses
            if (
                len(required_impl_files) == 1
                and "__default__" in impl_code_map
                and required_impl_files[0] not in impl_code_map
            ):
                impl_code_map[required_impl_files[0]] = impl_code_map.pop("__default__")

            missing_files = [f for f in required_impl_files if f not in impl_code_map]
            if missing_files:
                logger.error(f"Missing implementation sections for files: {missing_files}")
                state["last_error"] = f"Missing implementation code for files: {', '.join(missing_files)}"
                return False

            cleaned_impl_map = {
                filepath: fix_impl_code(code)
                for filepath, code in impl_code_map.items()
                if filepath in required_impl_files
            }
            # Keep state field string-compatible for existing flow/rollback
            state["implementation_code_clean"] = "\n\n".join(
                cleaned_impl_map[f] for f in required_impl_files if f in cleaned_impl_map
            )

            # Apply safety nets to tests
            test_code = fix_test_code(test_code)
            state["test_code_clean"] = test_code

            # Write implementation files
            for filepath in required_impl_files:
                impl_code = cleaned_impl_map.get(filepath)
                if impl_code and _write_code_to_file(filepath, impl_code, config.workspace_dir):
                    logger.info(f"Wrote implementation file: {filepath}")

            # Write test file
            test_file = task.get("test_file")
            if test_file:
                if _write_code_to_file(test_file, test_code, config.workspace_dir):
                    logger.info(f"Wrote test file: {test_file}")

            return True

        except Exception as e:
            logger.error(f"Single-call generation failed: {e}")
            state["last_error"] = str(e)
            return False

    async def _generate_tests(self, state: PipelineState,
                              existing_impl: str = None) -> PipelineState:
        """Generate test suite for task using TDD.
        
        Args:
            existing_impl: If provided (during test regeneration), the test prompt
                will include this code so the new test matches the real API.
        """
        task = state["current_task"]

        logger.info(f"Generating tests for {task['name']}")

        context = self.context_builder.for_test_generation(
            task,
            task["module"],
            existing_implementation=existing_impl,
        )
        prompt = self.context_builder.assemble_prompt(context)

        try:
            # Route to cloud when force_cloud is enabled
            if getattr(config, 'force_cloud', False):
                logger.info("Generating tests with cloud (force_cloud=True)")
                response = await self.openrouter.generate_async(
                    prompt=prompt,
                    model=config.openrouter_model,
                    temperature=0.1,
                    max_tokens=6000,
                )
            else:
                response = await self.ollama.generate_async(
                    prompt=prompt,
                    model=config.ollama_model_strong,
                    temperature=0.1,
                    max_tokens=6000,
                )

            state["test_code"] = response

            test_file = task.get("test_file")
            if test_file and response:
                code = _extract_code_from_response(response)
                code = fix_test_code(code)
                state["test_code_clean"] = code
                if _write_code_to_file(test_file, code, config.workspace_dir):
                    logger.info(f"Wrote test file: {test_file}")
                else:
                    logger.warning(f"Could not write test file: {test_file}")

            return state

        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            state["status"] = "failing"
            state["last_error"] = str(e)
            return state

    async def _generate_implementation(self, state: PipelineState) -> PipelineState:
        """Generate implementation code."""
        task = state["current_task"]
        iteration = state["iteration"]

        model_tier = self.router.route_task(task)
        state["model_tier"] = model_tier

        # Force all tasks to cloud when force_cloud is enabled
        if getattr(config, 'force_cloud', False):
            return await self._generate_implementation_cloud(state)

        if model_tier == "local_cheap":
            model_name = config.ollama_model_cheap
            client = self.ollama
        elif model_tier == "local_strong":
            model_name = config.ollama_model_strong
            client = self.ollama
        else:
            return await self._generate_implementation_cloud(state)

        logger.info(f"Generating implementation with {model_tier} ({model_name})")

        previous_code = state.get("implementation_code_clean") if iteration > 1 else None
        error_output = state.get("last_error") if iteration > 1 else None

        context = self.context_builder.for_implementation(
            task,
            state.get("test_code_clean") or state.get("test_code") or "",
            iteration,
            previous_code,
            error_output,
        )
        prompt = self.context_builder.assemble_prompt(context)

        try:
            response = await client.generate_async(
                prompt=prompt,
                model=model_name,
                temperature=0.1,
                max_tokens=4000,
            )

            if not response or not response.strip():
                logger.error(f"Local model ({model_name}) returned empty response")
                state["last_error"] = "Local model returned empty response"
                state["test_passed"] = False
                state["error_count"] = state.get("error_count", 0) + 1
                return state

            state["implementation_code"] = response
            state["response"] = response

            code = _extract_code_from_response(response)
            code = fix_impl_code(code)
            state["implementation_code_clean"] = code
            for filepath in task.get("files", []):
                if _write_code_to_file(filepath, code, config.workspace_dir):
                    logger.info(f"Wrote implementation file: {filepath}")

            await self._run_tests(state)

            if not state.get("test_passed") and state.get("last_error"):
                logger.info(f"Test error (tail): {state['last_error'][-500:]}")

            return state

        except Exception as e:
            logger.error(f"Implementation failed: {e}")
            state["last_error"] = str(e)
            state["test_passed"] = False
            state["error_count"] = state.get("error_count", 0) + 1
            return state

    async def _generate_implementation_cloud(self, state: PipelineState) -> PipelineState:
        """Generate implementation using cloud model."""
        task = state["current_task"]
        iteration = state["iteration"]

        logger.info("Generating implementation with cloud (Claude)")

        previous_code = state.get("implementation_code_clean")
        error_output = state.get("last_error")

        context = self.context_builder.for_implementation(
            task,
            state.get("test_code_clean") or state.get("test_code") or "",
            iteration,
            previous_code,
            error_output,
        )
        prompt = self.context_builder.assemble_prompt(context)

        try:
            response = await self.openrouter.generate_async(
                prompt=prompt,
                model=config.openrouter_model,
                temperature=0.1,
                max_tokens=12000,
            )

            if not response or not response.strip():
                logger.error("Cloud model returned empty response")
                state["last_error"] = "Cloud model returned empty response"
                state["test_passed"] = False
                state["status"] = "failing"
                return state

            state["implementation_code"] = response
            state["response"] = response

            code = _extract_code_from_response(response)
            code = fix_impl_code(code)
            state["implementation_code_clean"] = code
            task = state["current_task"]
            for filepath in task.get("files", []):
                if _write_code_to_file(filepath, code, config.workspace_dir):
                    logger.info(f"Wrote implementation file: {filepath}")

            await self._run_tests(state)

            if not state.get("test_passed") and state.get("last_error"):
                logger.info(f"Test error (tail): {state['last_error'][-500:]}")

            return state

        except Exception as e:
            logger.error(f"Cloud implementation failed: {e}")
            state["status"] = "failing"
            state["test_passed"] = False
            state["last_error"] = str(e)
            return state

    async def _run_tests(self, state: PipelineState):
        """Run tests in Docker sandbox."""
        task = state["current_task"]
        test_file = task.get("test_file")

        if not test_file:
            logger.warning(f"No test file for task {task['id']}")
            state["test_passed"] = True
            return

        logger.info(f"Running tests in Docker: {test_file}")

        try:
            result = self.docker_runner.run_tests(test_file)
            state["test_results"] = result.output
            state["test_passed"] = result.passed

            if result.passed:
                logger.info(f"✓ Tests passed for task {task['id']}")
            else:
                logger.warning(f"✗ Tests failed for task {task['id']}")
                output = result.output or ""
                state["last_error"] = output[-3000:] if len(output) > 3000 else output
                if output:
                    logger.debug(f"Test output (tail): {output[-500:]}")

        except Exception as e:
            logger.error(f"Failed to run tests: {e}")
            state["test_passed"] = False
            state["last_error"] = str(e)

    async def execute_final_review(self, state: PipelineState) -> PipelineState:
        """Stage 5: Final review (human checkpoint C)."""
        logger.info(f"[{state['execution_id']}] Final review")

        state["current_stage"] = "final_review"
        state["human_approval_required"] = True
        state["end_time"] = datetime.now().isoformat()

        # Preserve done/done_with_errors from execute_task
        if state.get("status") not in ("done", "done_with_errors"):
            state["status"] = "in_progress"

        return state

    async def build_pipeline(self) -> object:
        """Build and return compiled LangGraph pipeline."""

        logger.info("Building LangGraph pipeline")

        workflow = StateGraph(PipelineState)

        workflow.add_node("spec_review", self.execute_spec_review)
        workflow.add_node("architecture", self.execute_architecture)
        workflow.add_node("decomposition", self.execute_decomposition)
        workflow.add_node("execute_task", self.execute_task)
        workflow.add_node("final_review", self.execute_final_review)

        workflow.set_entry_point("spec_review")
        workflow.add_edge("spec_review", "architecture")
        workflow.add_edge("architecture", "decomposition")
        workflow.add_edge("decomposition", "execute_task")
        workflow.add_edge("execute_task", "final_review")
        workflow.add_edge("final_review", END)

        logger.info("Pipeline graph built")
        return workflow.compile()


async def run_pipeline(initial_state: PipelineState) -> PipelineState:
    """Execute the pipeline with initial state."""

    orchestrator = PipelineOrchestrator()
    pipeline = await orchestrator.build_pipeline()

    logger.info(f"Starting pipeline execution: {initial_state['execution_id']}")

    result = await pipeline.ainvoke(initial_state)

    logger.info(f"Pipeline execution completed: {initial_state['execution_id']}")

    return result

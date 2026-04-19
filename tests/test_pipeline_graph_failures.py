"""Regression tests for pipeline failure classification and diagnostics."""

from types import SimpleNamespace

import pytest

from src.config import config
from src.pipeline.graph import PipelineOrchestrator, _is_collection_or_import_failure


@pytest.mark.parametrize(
    "output",
    [
        "ERROR tests/unit/test_auth_password.py\nInterrupted: 1 error during collection",
        "ImportError while importing test module 'tests/unit/test_auth_password.py'",
        "SyntaxError: invalid syntax",
        "collected 0 items\n\n============================ no tests ran",
    ],
)
def test_collection_and_import_failures_are_detected(output):
    assert _is_collection_or_import_failure(output)


@pytest.mark.asyncio
async def test_collection_failure_does_not_replace_best_snapshot(monkeypatch):
    orchestrator = PipelineOrchestrator()

    call_state = {"count": 0}

    async def fake_generate(state):
        call_state["count"] += 1
        if call_state["count"] == 1:
            state["implementation_code_clean"] = "impl_v1"
            state["test_code_clean"] = "test_v1"
            return True
        if call_state["count"] == 2:
            state["implementation_code_clean"] = "impl_v2_bad"
            state["test_code_clean"] = "test_v2_bad"
            return True
        # On the third generation call, regression logic should have rolled back.
        assert state["implementation_code_clean"] == "impl_v1"
        assert state["test_code_clean"] == "test_v1"
        state["implementation_code_clean"] = "impl_v1"
        state["test_code_clean"] = "test_v1"
        return True

    async def fake_run_tests(state):
        iteration = state["iteration"]
        if iteration == 1:
            state["test_passed"] = False
            state["last_error"] = "=== 2 passed, 1 failed in 0.12s ==="
        elif iteration == 2:
            state["test_passed"] = False
            state["last_error"] = (
                "ERROR tests/unit/test_auth_password.py\n"
                "ImportError while importing test module\n"
                "Interrupted: 1 error during collection"
            )
        else:
            state["test_passed"] = True
            state["last_error"] = ""

    monkeypatch.setattr(orchestrator, "_generate_impl_and_tests", fake_generate)
    monkeypatch.setattr(orchestrator, "_run_tests", fake_run_tests)

    state = {
        "execution_id": "run-test",
        "current_task": {
            "id": "T008",
            "name": "Auth password",
            "files": ["src/auth/password.py"],
            "test_file": "tests/unit/test_auth_password.py",
        },
    }

    result = await orchestrator._execute_single_task(state)
    assert result["test_passed"] is True


@pytest.mark.asyncio
async def test_run_tests_persists_full_output_and_summary(monkeypatch, tmp_path):
    orchestrator = PipelineOrchestrator()

    huge_output = "A" * 8000 + "\nInterrupted: 1 error during collection"

    class DummyRunner:
        def run_tests(self, _test_file):
            return SimpleNamespace(passed=False, output=huge_output)

    monkeypatch.setattr(orchestrator, "docker_runner", DummyRunner())
    monkeypatch.setattr(config, "artifacts_dir", tmp_path)

    state = {
        "iteration": 2,
        "current_task": {
            "id": "T008",
            "name": "Auth password",
            "test_file": "tests/unit/test_auth_password.py",
        },
    }

    await orchestrator._run_tests(state)

    assert state["last_error"] == huge_output
    assert state["test_run_summary"]["is_collection_or_import_failure"] is True

    log_path = tmp_path / "test_logs" / "T008_iter_2.log"
    assert log_path.exists()
    assert log_path.read_text(encoding="utf-8") == huge_output

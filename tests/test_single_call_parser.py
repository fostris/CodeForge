"""Tests for single-call response parsing in pipeline graph."""

from src.pipeline.graph import _parse_single_call_response


def test_parse_multi_file_single_call_response():
    response = (
        "=== IMPLEMENTATION: src/a.py ===\n"
        "import os\n\nVALUE = 1\n"
        "=== IMPLEMENTATION: src/b.py ===\n"
        "from src.a import VALUE\n\n"
        "def get_value():\n"
        "    return VALUE\n"
        "=== TESTS: tests/unit/test_ab.py ===\n"
        "import pytest\n\n"
        "def test_get_value():\n"
        "    assert True\n"
    )

    impl_map, test_code = _parse_single_call_response(response)

    assert set(impl_map.keys()) == {"src/a.py", "src/b.py"}
    assert "=== IMPLEMENTATION:" not in impl_map["src/a.py"]
    assert "=== IMPLEMENTATION:" not in impl_map["src/b.py"]
    assert test_code.startswith("import pytest")


def test_parse_single_file_single_call_response():
    response = (
        "=== IMPLEMENTATION: src/only.py ===\n"
        "def run():\n"
        "    return 1\n"
        "=== TESTS: tests/unit/test_only.py ===\n"
        "import pytest\n\n"
        "def test_run():\n"
        "    assert True\n"
    )

    impl_map, test_code = _parse_single_call_response(response)

    assert list(impl_map.keys()) == ["src/only.py"]
    assert impl_map["src/only.py"].startswith("def run")
    assert test_code.startswith("import pytest")


def test_parse_missing_required_implementation_file_detectable():
    required_files = ["src/a.py", "src/b.py"]
    response = (
        "=== IMPLEMENTATION: src/a.py ===\n"
        "def a():\n"
        "    return 1\n"
        "=== TESTS: tests/unit/test_ab.py ===\n"
        "import pytest\n"
    )

    impl_map, _ = _parse_single_call_response(response)
    missing = [f for f in required_files if f not in impl_map]

    assert missing == ["src/b.py"]


def test_parser_strips_marker_lines_from_code_bodies():
    response = (
        "=== IMPLEMENTATION: src/a.py ===\n"
        "import os\n"
        "=== IMPLEMENTATION: src/b.py ===\n"
        "def b():\n"
        "    return 2\n"
        "=== TESTS: tests/unit/test_ab.py ===\n"
        "import pytest\n"
    )

    impl_map, _ = _parse_single_call_response(response)
    assert "=== TESTS:" not in impl_map["src/b.py"]
    assert "=== IMPLEMENTATION:" not in impl_map["src/a.py"]

"""Tests for task graph loading in context builder."""

import json

from src.pipeline.context_builder import ContextBuilder


def test_context_builder_task_graph_reads_object_format(tmp_path):
    path = tmp_path / "TASK_GRAPH.json"
    path.write_text(json.dumps({"tasks": [{"id": "T001", "name": "Task"}]}), encoding="utf-8")

    builder = ContextBuilder(artifacts_dir=tmp_path)
    tasks = builder.task_graph

    assert len(tasks) == 1
    assert tasks[0]["id"] == "T001"


def test_context_builder_task_graph_reads_plain_list_backward_compatible(tmp_path):
    path = tmp_path / "TASK_GRAPH.json"
    path.write_text(json.dumps([{"id": "T001", "name": "Task"}]), encoding="utf-8")

    builder = ContextBuilder(artifacts_dir=tmp_path)
    tasks = builder.task_graph

    assert len(tasks) == 1
    assert tasks[0]["id"] == "T001"

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.run_stage_p_scope_graph_case01_probe_v1_1 import CASE_ID, construct
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_durable_executor_v1_1 import (
    DEPENDENCY_IDENTITIES, RUNNER_RELATIVE, RUNNER_SHA256, VENV_PYTHON, WSL_DISTRIBUTION,
    DurableScopeGraphStagePExecutorV1_1,
)


ROOT = Path(__file__).resolve().parents[1]


def test_executor_checks_all_v1_1_identities_without_events(tmp_path):
    lifecycle = tmp_path / "life"
    executor = DurableScopeGraphStagePExecutorV1_1(project_root=ROOT, durable_lifecycle_root=lifecycle)
    assert executor and lifecycle.is_dir() and list(lifecycle.iterdir()) == []
    assert hashlib.sha256((ROOT / RUNNER_RELATIVE).read_bytes()).hexdigest() == RUNNER_SHA256
    for relative, expected in DEPENDENCY_IDENTITIES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    assert WSL_DISTRIBUTION == "Ubuntu-24.04" and VENV_PYTHON.endswith("/.venv/bin/python3")


def test_one_shot_construct_selects_only_case01_without_execution(tmp_path):
    request, binding, evaluator = construct(project_root=ROOT, evidence_root=tmp_path)
    assert binding["case_id"] == CASE_ID == "HMCV1-SASC-01"
    assert binding["runner_binding_identity"] == "57891ab6d928cde37a7d388e2f97a3da87d130e8debc1ab29b90bec850dc288a"
    assert binding["maximum_provider_calls"] == 1
    assert binding["retry_count"] == binding["repair_count"] == binding["selection_count"] == 0
    assert binding["stage_c_constructed"] is binding["stage_c_called"] is False
    assert request["candidate"] and request["factual_summary"] and evaluator.render_prompt(request)
    assert list((tmp_path / "durable-lifecycle").iterdir()) == []


def test_probe_has_one_capture_path_no_case10_or_stage_c_edge():
    import pastila_scout.semantic_admission_v2.run_stage_p_scope_graph_case01_probe_v1_1 as module
    source = inspect.getsource(module)
    assert source.count("execute_and_capture_stage_p_v2(") == 1 and "HMCV1-SASC-10" not in source
    scrubbed = source.lower().replace('"stage_c_constructed": false', '').replace('"stage_c_called": false', '')
    assert "stage_c" not in scrubbed


def test_identity_drift_fails_before_launch(tmp_path, monkeypatch):
    import pastila_scout.semantic_admission_v2.stage_p_scope_graph_durable_executor_v1_1 as module
    monkeypatch.setattr(module, "RUNNER_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="identity drift"):
        module.DurableScopeGraphStagePExecutorV1_1(project_root=ROOT, durable_lifecycle_root=tmp_path / "life")

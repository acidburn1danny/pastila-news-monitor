from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.run_stage_p_role_coherence_case01_probe_v1 import CASE_ID, construct
from pastila_scout.semantic_admission_v2.stage_p_role_coherence_durable_executor_v1 import (
    DEPENDENCY_IDENTITIES, RUNNER_RELATIVE, RUNNER_SHA256, DurableRoleCoherenceStagePExecutorV1,
)


ROOT = Path(__file__).resolve().parents[1]


def test_executor_construction_checks_all_identities_without_events(tmp_path: Path) -> None:
    lifecycle = tmp_path / "life"
    executor = DurableRoleCoherenceStagePExecutorV1(project_root=ROOT, durable_lifecycle_root=lifecycle)
    assert executor is not None and lifecycle.is_dir() and list(lifecycle.iterdir()) == []
    assert hashlib.sha256((ROOT / RUNNER_RELATIVE).read_bytes()).hexdigest() == RUNNER_SHA256
    for relative, expected in DEPENDENCY_IDENTITIES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_one_shot_construct_selects_only_case01_and_does_not_execute(tmp_path: Path) -> None:
    request, binding, evaluator = construct(project_root=ROOT, evidence_root=tmp_path)
    assert binding["case_id"] == CASE_ID == "HMCV1-SASC-01"
    assert binding["maximum_provider_calls"] == 1
    assert binding["retry_count"] == binding["repair_count"] == binding["selection_count"] == 0
    assert binding["projector_bound"] is False and binding["stage_c_constructed"] is False and binding["stage_c_called"] is False
    assert request["candidate"] and request["factual_summary"] and evaluator.render_prompt(request)
    assert list((tmp_path / "durable-lifecycle").iterdir()) == []


def test_probe_has_one_capture_path_and_no_stage_c_or_case10_edge() -> None:
    import pastila_scout.semantic_admission_v2.run_stage_p_role_coherence_case01_probe_v1 as module
    source = inspect.getsource(module)
    assert source.count("execute_and_capture_stage_p_v2(") == 1
    assert "retry" not in source.lower() or '"retry_count": 0' in source
    assert "HMCV1-SASC-10" not in source and "stage_c" not in source.lower().replace('"stage_c_constructed": false', '').replace('"stage_c_called": false', '')


def test_identity_drift_fails_before_any_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pastila_scout.semantic_admission_v2.stage_p_role_coherence_durable_executor_v1 as module
    monkeypatch.setattr(module, "RUNNER_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="identity drift"):
        module.DurableRoleCoherenceStagePExecutorV1(project_root=ROOT, durable_lifecycle_root=tmp_path / "life")

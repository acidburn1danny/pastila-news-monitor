from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_role_durable_executor_v1 import (
    DEPENDENCY_IDENTITIES, RUNNER_RELATIVE, RUNNER_SHA256, DurableConstructionRoleStagePExecutorV1,
)


ROOT = Path(__file__).resolve().parents[1]


def test_runner_and_every_executor_dependency_are_exactly_bound(tmp_path):
    assert hashlib.sha256((ROOT / RUNNER_RELATIVE).read_bytes()).hexdigest() == RUNNER_SHA256
    for relative, expected in DEPENDENCY_IDENTITIES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    executor = DurableConstructionRoleStagePExecutorV1(
        project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")
    assert executor._max_output_tokens == 3200


def test_dependency_drift_fails_before_any_launch(monkeypatch, tmp_path):
    monkeypatch.setitem(DEPENDENCY_IDENTITIES, Path("missing-construction-role-dependency.py"), "0" * 64)
    with pytest.raises(RuntimeError, match="dependency identity drift"):
        DurableConstructionRoleStagePExecutorV1(
            project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")

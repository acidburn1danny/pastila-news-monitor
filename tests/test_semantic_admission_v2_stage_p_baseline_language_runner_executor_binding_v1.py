from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_durable_executor_v1_3 import (
    DEPENDENCY_IDENTITIES,
    RUNNER_RELATIVE,
    RUNNER_SHA256,
    DurableScopeGraphStagePExecutorV1_3,
)


ROOT = Path(__file__).resolve().parents[1]


def test_runner_and_executor_dependencies_are_byte_exact():
    assert hashlib.sha256((ROOT / RUNNER_RELATIVE).read_bytes()).hexdigest() == RUNNER_SHA256
    for relative, expected in DEPENDENCY_IDENTITIES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_runner_loads_diagnostic_types_without_model_stack():
    before = set(sys.modules)
    spec = importlib.util.spec_from_file_location("baseline_language_runner_binding_test", ROOT / RUNNER_RELATIVE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    State, Trie, Controller, Lifecycle = module._diagnostic_types()
    assert State.__name__ == "StagePScopeGraphConstraintStateV1_2"
    assert Trie.__name__ == "StagePDiagnosticTokenTrieProjectorV1"
    assert Controller.__name__ == "StagePScopeGraphDiagnosticCallbackControllerV1"
    assert Lifecycle.__name__ == "AppendOnlyLifecycleV1"
    assert not any(name.startswith(("transformers", "peft")) for name in set(sys.modules) - before)


def test_executor_construction_has_no_execution_edge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("construction must not launch a process")

    monkeypatch.setattr("subprocess.Popen", forbidden)
    DurableScopeGraphStagePExecutorV1_3(project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")


def test_executor_preserves_timeout_and_distinct_liveness_receipt():
    source = (ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_durable_executor_v1_3.py").read_text("utf-8")
    assert "timeout=authority.timeout_policy.timeout_seconds" in source
    assert "HOST_CONSTRAINT_LIVENESS_FAILURE_CLASSIFIED" in source
    assert "StagePConstraintLivenessExecutionErrorV1" in source
    assert "CASE01" not in source and "probe" not in source.lower()

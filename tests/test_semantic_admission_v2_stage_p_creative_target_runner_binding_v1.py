from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_creative_target_callback_controller_v1 import (
    StagePCreativeTargetCallbackControllerV1,
)
from pastila_scout.semantic_admission_v2.stage_p_creative_target_incremental_tracker_v1 import (
    StagePCreativeTargetIncrementalTrackerV1,
)
from pastila_scout.semantic_admission_v2.stage_p_creative_target_durable_executor_v1 import (
    DEPENDENCY_IDENTITIES, RUNNER_RELATIVE, RUNNER_SHA256, DurableCreativeTargetStagePExecutorV1,
)
import hashlib
import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src/pastila_scout/experimental_core_v1_2_stage_p_creative_target_runner_v1.py"


def _minimal_raw():
    entry = {"entry_id": "P1", "entry_type": "CONTAINED_CREATIVE", "candidate_span": "metafora",
        "authority_support": None, "commitment": "Transformare.", "scope_basis": "CREATIVE_CONTAINED",
        "event_alignment": "CREATIVE_VEHICLE_ONLY", "authority_modality": "NOT_APPLICABLE",
        "candidate_modality": "NOT_APPLICABLE", "authority_timing": "NOT_APPLICABLE",
        "candidate_timing": "NOT_APPLICABLE", "independence_group": "G1", "scope_relation": "CREATIVE_HOST",
        "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}
    return json.dumps({"stage_id": "PROPOSITION_LEDGER", "entries": [entry], "creative_target_audits": [{
        "audit_id": "T1", "creative_host_entry_id": "P1", "vehicle_span": "metafora",
        "semantic_target": "Evaluare editoriala.", "target_class": "NONFACTUAL_EDITORIAL_OR_CREATIVE",
        "survival_basis": "DOES_NOT_SURVIVE_AS_FACT", "proposition_entry_id": None,
        "resolution": "RETAINED_NONFACTUAL"}], "coverage_receipt": {
        "candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
        "creative_scope_checked": True, "unresolved_scope_present": False,
        "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
        "factual_return_tests_completed": True, "creative_targets_enumerated": True,
        "target_classes_reviewed": True, "target_to_ledger_reconciled": True},
        "coverage_decision": "COMPLETE"}, separators=(",", ":"))


def test_tracker_uses_creative_target_dfa_incrementally():
    raw = _minimal_raw(); tracker = StagePCreativeTargetIncrementalTrackerV1()
    first = raw[:len(raw)//2]; one = tracker.state_for([1], lambda _: first)
    two = tracker.state_for([1, 2], lambda _: raw)
    assert one.path == two.path == "INCREMENTAL"
    assert two.state.can_eos and tracker.incremental_steps == 2 and tracker.rebuild_steps == 0


def test_runner_loads_exact_types_without_host_or_model_dependencies():
    before = set(sys.modules)
    spec = importlib.util.spec_from_file_location("creative_target_runner_binding_test", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); module.ROOT = ROOT
    State, Trie, Controller, Lifecycle = module._creative_target_types()
    assert State.__name__ == "StagePCreativeTargetConstraintStateV1"
    assert Trie.__name__ == "StagePDiagnosticTokenTrieProjectorV1"
    assert Controller.__name__ == "StagePCreativeTargetCallbackControllerV1"
    assert Lifecycle.__name__ == "AppendOnlyLifecycleV1"
    newly_loaded = set(sys.modules) - before
    assert not any(name.startswith(("pydantic", "transformers", "peft")) for name in newly_loaded)


def test_controller_is_bound_to_new_tracker():
    assert StagePCreativeTargetCallbackControllerV1.__init__.__annotations__["projector"] == "StagePDiagnosticTokenTrieProjectorV1"
    source = RUNNER.read_text("utf-8")
    assert "base.run(*map(Path, arguments))" in source
    assert "AutoModel" not in source and "PeftModel" not in source


def test_executor_dependencies_are_byte_exact_and_construction_does_not_launch(tmp_path, monkeypatch):
    assert hashlib.sha256((ROOT / RUNNER_RELATIVE).read_bytes()).hexdigest() == RUNNER_SHA256
    for relative, expected in DEPENDENCY_IDENTITIES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("launch forbidden")))
    DurableCreativeTargetStagePExecutorV1(project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")


def test_executor_source_preserves_distinct_liveness_and_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    DurableCreativeTargetStagePExecutorV1(project_root=ROOT, durable_lifecycle_root=tmp_path / "lifecycle")
    source = (ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_creative_target_durable_executor_v1.py").read_text("utf-8")
    assert "HOST_CONSTRAINT_LIVENESS_FAILURE_CLASSIFIED" in source
    assert "timeout=authority.timeout_policy.timeout_seconds" in source
    assert "CASE01" not in source and "stage_c" not in source.lower()

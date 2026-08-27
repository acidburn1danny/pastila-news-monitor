from __future__ import annotations

import inspect
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_callback_controller_v1 import StagePScopeGraphCallbackControllerV1
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_constraint_v1 import StagePScopeGraphConstraintStateV1
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_incremental_tracker_v1 import StagePScopeGraphIncrementalTrackerV1
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src/pastila_scout/experimental_core_v1_2_stage_p_scope_graph_runner_v1.py"


def _raw():
    entry = {"entry_id": "P1", "entry_type": "CONTAINED_CREATIVE", "candidate_span": "metaforă",
             "authority_support": None, "commitment": "Vehicul editorial.", "scope_basis": "CREATIVE_CONTAINED",
             "event_alignment": "CREATIVE_VEHICLE_ONLY", "authority_modality": "NOT_APPLICABLE",
             "candidate_modality": "NOT_APPLICABLE", "authority_timing": "NOT_APPLICABLE",
             "candidate_timing": "NOT_APPLICABLE", "independence_group": "G1", "scope_relation": "CREATIVE_HOST",
             "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}
    value = {"stage_id": "PROPOSITION_LEDGER", "entries": [entry],
             "coverage_receipt": {"candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
                                  "creative_scope_checked": True, "unresolved_scope_present": False,
                                  "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
                                  "factual_return_tests_completed": True}, "coverage_decision": "COMPLETE"}
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def test_scope_graph_controller_tracks_fixture_to_terminal_eos():
    raw = _raw()
    pieces = {0: "<eos>", **{index: char for index, char in enumerate(sorted(set(raw)), 1)}}
    inverse = {char: index for index, char in pieces.items() if index}
    projector = StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=0)
    controller = StagePScopeGraphCallbackControllerV1(projector=projector)
    ids = []
    for char in raw:
        ids.append(inverse[char])
        receipt = controller.allowed(ids, lambda values: "".join(pieces[item] for item in values))
    assert StagePScopeGraphConstraintStateV1().feed(raw).can_eos
    assert receipt.allowed_token_ids == (0,) and receipt.tracker_rebuilds == 0


def test_tracker_rebuilds_safely_when_prefix_is_replaced():
    tracker = StagePScopeGraphIncrementalTrackerV1()
    raw = _raw()
    first = tracker.state_for(tuple(range(5)), lambda _: raw[:5])
    second = tracker.state_for(tuple(range(6)), lambda _: raw[:6])
    replaced = tracker.state_for((99,), lambda _: raw[:1])
    assert first.path == second.path == "INCREMENTAL"
    assert replaced.path == "FULL_REBUILD" and tracker.rebuild_steps == 1


def test_runner_binds_exact_scope_graph_types_and_durable_base():
    source = RUNNER.read_text("utf-8")
    for name in ("StagePScopeGraphConstraintStateV1", "StagePScopeGraphCallbackControllerV1",
                 "StagePTokenTrieProjectorV1", "AppendOnlyLifecycleV1"):
        assert name in source
    assert "experimental_core_v1_2_stage_p_constrained_runner_v3.py" in source
    assert "base._types = _scope_graph_types" in source and "base.run(" in source
    assert "229595d7220e0121257f40d15dcdcd8d6fb40e4943b660b48e17450554354ada" in source


def test_callback_and_tracker_have_no_model_provider_or_process_edge():
    combined = inspect.getsource(StagePScopeGraphCallbackControllerV1) + inspect.getsource(StagePScopeGraphIncrementalTrackerV1)
    for forbidden in ("transformers", "torch", "subprocess", "provider", "model.generate"):
        assert forbidden not in combined


def test_importing_runner_does_not_load_transformers_or_execute_main():
    import importlib
    import sys
    before = set(sys.modules)
    module = importlib.import_module("pastila_scout.experimental_core_v1_2_stage_p_scope_graph_runner_v1")
    assert hasattr(module, "main") and "transformers" not in set(sys.modules) - before

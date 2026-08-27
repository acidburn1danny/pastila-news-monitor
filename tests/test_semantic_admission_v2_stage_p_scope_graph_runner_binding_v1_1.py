from __future__ import annotations

import importlib
import inspect
import json
import sys
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_callback_controller_v1_1 import StagePScopeGraphCallbackControllerV1_1
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_constraint_v1_1 import StagePScopeGraphConstraintStateV1_1
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_incremental_tracker_v1_1 import StagePScopeGraphIncrementalTrackerV1_1
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src/pastila_scout/experimental_core_v1_2_stage_p_scope_graph_runner_v1_1.py"


def _raw():
    entry = {"entry_id": "P1", "entry_type": "REAL_WORLD_COMMITMENT", "candidate_span": "fapt",
             "authority_support": None, "commitment": "Propoziție nouă.", "scope_basis": "ASSERTED",
             "event_alignment": "NEW_UNSUPPORTED_EVENT", "authority_modality": "NOT_APPLICABLE",
             "candidate_modality": "CERTAIN_OR_ACTUAL", "authority_timing": "NOT_APPLICABLE",
             "candidate_timing": "PRESENT", "independence_group": "G1", "scope_relation": "STANDALONE",
             "creative_host_entry_id": None, "factual_return_basis": "ASSERTION_SURVIVES"}
    return json.dumps({"stage_id": "PROPOSITION_LEDGER", "entries": [entry],
        "coverage_receipt": {"candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
            "creative_scope_checked": True, "unresolved_scope_present": False,
            "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
            "factual_return_tests_completed": True}, "coverage_decision": "COMPLETE"},
        ensure_ascii=False, separators=(",", ":"))


def test_v1_1_controller_tracks_valid_fixture_to_terminal_eos():
    raw = _raw(); pieces = {0: "<eos>", **{index: char for index, char in enumerate(sorted(set(raw)), 1)}}
    inverse = {char: index for index, char in pieces.items() if index}
    controller = StagePScopeGraphCallbackControllerV1_1(
        projector=StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=0))
    ids = []
    for char in raw:
        ids.append(inverse[char]); receipt = controller.allowed(ids, lambda values: "".join(pieces[item] for item in values))
    assert StagePScopeGraphConstraintStateV1_1().feed(raw).can_eos
    assert receipt.allowed_token_ids == (0,) and receipt.tracker_rebuilds == 0


def test_v1_1_tracker_rebuilds_divergent_prefix_safely():
    tracker = StagePScopeGraphIncrementalTrackerV1_1(); raw = _raw()
    assert tracker.state_for((1,), lambda _: raw[:1]).path == "INCREMENTAL"
    assert tracker.state_for((1, 2), lambda _: raw[:2]).path == "INCREMENTAL"
    assert tracker.state_for((9,), lambda _: raw[:1]).path == "FULL_REBUILD"


def test_runner_binds_exact_v1_1_types_and_approved_request():
    source = RUNNER.read_text("utf-8")
    for name in ("StagePScopeGraphConstraintStateV1_1", "StagePScopeGraphCallbackControllerV1_1",
                 "StagePTokenTrieProjectorV1", "AppendOnlyLifecycleV1"):
        assert name in source
    assert "2fee4188906353caed6effa393e877b523e4cede4a567702e06a7f9d9094ba5e" in source
    assert "base._types = _scope_graph_v1_1_types" in source and "base.run(" in source


def test_tracker_controller_have_no_execution_or_model_edge():
    source = inspect.getsource(StagePScopeGraphIncrementalTrackerV1_1) + inspect.getsource(StagePScopeGraphCallbackControllerV1_1)
    assert all(term not in source for term in ("transformers", "torch", "subprocess", "model.generate"))


def test_importing_runner_does_not_load_transformers_or_execute():
    before = set(sys.modules)
    module = importlib.import_module("pastila_scout.experimental_core_v1_2_stage_p_scope_graph_runner_v1_1")
    assert hasattr(module, "main") and "transformers" not in set(sys.modules) - before

from __future__ import annotations

import json

import pytest

from pastila_scout.semantic_admission_v2.stage_p_diagnostic_trie_projector_v1 import (
    StagePDiagnosticTokenTrieProjectorV1,
)
from pastila_scout.semantic_admission_v2.stage_p_liveness_trie_projector_v1 import StagePConstraintLivenessErrorV1
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_constraint_v1_2 import StagePScopeGraphConstraintStateV1_2
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_diagnostic_callback_controller_v1 import (
    StagePScopeGraphDiagnosticCallbackControllerV1,
)
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


def _ledger():
    return json.dumps({"stage_id": "PROPOSITION_LEDGER", "entries": [{
        "entry_id": "P1", "entry_type": "CONTAINED_CREATIVE", "candidate_span": "metafora",
        "authority_support": None, "commitment": "Transformare editoriala.",
        "scope_basis": "CREATIVE_CONTAINED", "event_alignment": "CREATIVE_VEHICLE_ONLY",
        "authority_modality": "NOT_APPLICABLE", "candidate_modality": "NOT_APPLICABLE",
        "authority_timing": "NOT_APPLICABLE", "candidate_timing": "NOT_APPLICABLE",
        "independence_group": "G1", "scope_relation": "CREATIVE_HOST",
        "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}],
        "coverage_receipt": {"candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
            "creative_scope_checked": True, "unresolved_scope_present": False,
            "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
            "factual_return_tests_completed": True}, "coverage_decision": "COMPLETE"}, separators=(",", ":"))


def test_diagnostic_adapter_matches_baseline_at_every_prefix_exactly():
    raw = _ledger(); pieces = {index + 1: char for index, char in enumerate(sorted(set(raw)))}
    baseline = StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=999)
    candidate = StagePDiagnosticTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=999)
    state = StagePScopeGraphConstraintStateV1_2()
    for char in raw:
        assert candidate.allowed_token_ids(state) == baseline.allowed_token_ids(state)
        state = state.feed(char)
    assert candidate.allowed_token_ids(state) == baseline.allowed_token_ids(state) == (999,)


def test_diagnostic_receipt_does_not_modify_empty_set_failure():
    projector = StagePDiagnosticTokenTrieProjectorV1(token_pieces={1: "x"}, eos_token_id=999)
    controller = StagePScopeGraphDiagnosticCallbackControllerV1(projector=projector)
    with pytest.raises(StagePConstraintLivenessErrorV1) as raised:
        controller.allowed([], lambda _: "")
    receipt = raised.value.receipt
    assert receipt.code == "CONSTRAINT_LIVENESS_FAILURE"
    assert receipt.decoded_utf8_bytes == 0 and len(receipt.decoded_sha256) == 64


def test_adapter_does_not_override_allowed_token_computation():
    assert "allowed_token_ids" not in StagePDiagnosticTokenTrieProjectorV1.__dict__

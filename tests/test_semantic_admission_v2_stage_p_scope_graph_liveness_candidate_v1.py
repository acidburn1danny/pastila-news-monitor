from __future__ import annotations

import json
from dataclasses import dataclass, replace

import pytest

from pastila_scout.semantic_admission_v2.stage_p_liveness_trie_projector_v1 import (
    StagePConstraintLivenessErrorV1,
    StagePLivenessTokenTrieProjectorV1,
)
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_constraint_v1_1 import (
    StagePScopeGraphConstraintStateV1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_constraint_v1_2 import (
    StagePScopeGraphConstraintStateV1_2,
)
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_liveness_callback_controller_v1 import (
    StagePScopeGraphLivenessCallbackControllerV1,
)
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


def _pieces(*values: str) -> dict[int, str]:
    return {index + 1: value for index, value in enumerate(values)}


@dataclass(frozen=True)
class _LiteralState:
    remaining: str = "coverage"
    characters: int = 0
    mode: str = "LITERAL"
    buffer: str = ""
    string_characters: int = 0

    @property
    def can_eos(self) -> bool:
        return not self.remaining

    def feed(self, text: str):
        state = self
        for char in text:
            if not state.remaining or char != state.remaining[0]:
                raise ValueError("LITERAL_MISMATCH")
            state = replace(
                state,
                remaining=state.remaining[1:],
                characters=state.characters + 1,
            )
        return state


def test_candidate_prunes_a_valid_now_but_tokenization_dead_next_token():
    state = _LiteralState()
    pieces = _pieces("co", "coverage")
    baseline = StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=999)
    candidate = StagePLivenessTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=999)
    assert 1 in baseline.allowed_token_ids(state)
    assert candidate.allowed_token_ids(state) == (2,)


def test_candidate_does_not_remove_null_support_unsupported_real_world_ledger():
    entry = {
        "entry_id": "P1",
        "entry_type": "REAL_WORLD_COMMITMENT",
        "candidate_span": "fapt",
        "authority_support": None,
        "commitment": "Propozitie reala nesustinuta.",
        "scope_basis": "ASSERTED",
        "event_alignment": "NEW_UNSUPPORTED_EVENT",
        "authority_modality": "NOT_APPLICABLE",
        "candidate_modality": "CERTAIN_OR_ACTUAL",
        "authority_timing": "NOT_APPLICABLE",
        "candidate_timing": "PRESENT",
        "independence_group": "G1",
        "scope_relation": "STANDALONE",
        "creative_host_entry_id": None,
        "factual_return_basis": "ASSERTION_SURVIVES",
    }
    raw = json.dumps(
        {
            "stage_id": "PROPOSITION_LEDGER",
            "entries": [entry],
            "coverage_receipt": {
                "candidate_reviewed_as_whole": True,
                "embedded_propositions_checked": True,
                "creative_scope_checked": True,
                "unresolved_scope_present": False,
                "overlapping_spans_reconciled": True,
                "integrated_creative_hosts_checked": True,
                "factual_return_tests_completed": True,
            },
            "coverage_decision": "COMPLETE",
        },
        separators=(",", ":"),
    )
    pieces = _pieces(*sorted(set(raw)))
    projector = StagePLivenessTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=999)
    state = StagePScopeGraphConstraintStateV1_1()
    for char in raw:
        assert projector.allowed_token_ids(state)
        state = state.feed(char)
    assert state.can_eos and projector.allowed_token_ids(state) == (999,)


def test_empty_set_is_reported_as_distinct_auditable_liveness_failure():
    projector = StagePLivenessTokenTrieProjectorV1(token_pieces={1: "x"}, eos_token_id=999)
    controller = StagePScopeGraphLivenessCallbackControllerV1(projector=projector)
    with pytest.raises(StagePConstraintLivenessErrorV1) as raised:
        controller.allowed([], lambda _: "")
    receipt = raised.value.receipt
    assert receipt.code == "CONSTRAINT_LIVENESS_FAILURE"
    assert receipt.decoded_utf8_bytes == 0
    assert len(receipt.decoded_sha256) == 64


def test_complete_receipts_project_out_indeterminate_before_emission():
    raw = json.dumps(
        {
            "stage_id": "PROPOSITION_LEDGER",
            "entries": [{
                "entry_id": "P1", "entry_type": "REAL_WORLD_COMMITMENT", "candidate_span": "fapt",
                "authority_support": None, "commitment": "Propozitie reala nesustinuta.",
                "scope_basis": "ASSERTED", "event_alignment": "NEW_UNSUPPORTED_EVENT",
                "authority_modality": "NOT_APPLICABLE", "candidate_modality": "CERTAIN_OR_ACTUAL",
                "authority_timing": "NOT_APPLICABLE", "candidate_timing": "PRESENT",
                "independence_group": "G1", "scope_relation": "STANDALONE",
                "creative_host_entry_id": None, "factual_return_basis": "ASSERTION_SURVIVES",
            }],
            "coverage_receipt": {
                "candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
                "creative_scope_checked": True, "unresolved_scope_present": False,
                "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
                "factual_return_tests_completed": True,
            },
            "coverage_decision": "COMPLETE",
        }, separators=(",", ":"),
    )
    prefix = raw.split('"coverage_decision":"', 1)[0] + '"coverage_decision":"'
    baseline = StagePScopeGraphConstraintStateV1_1().feed(prefix)
    candidate = StagePScopeGraphConstraintStateV1_2().feed(prefix)
    assert baseline.choices == ("COMPLETE", "INDETERMINATE")
    assert candidate.choices == ("COMPLETE",)
    with pytest.raises(ValueError, match="ENUM_MISMATCH"):
        candidate.feed("INDETERMINATE")
    assert StagePScopeGraphConstraintStateV1_2().feed(raw).can_eos

from __future__ import annotations

import json

import pytest

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_constraint_v1 import (
    StagePRoleCoherenceConstraintViolationV1,
    StagePScopeGraphConstraintStateV1,
)


def _creative(entry_id="P1", relation="CREATIVE_HOST"):
    return {"entry_id": entry_id, "entry_type": "CONTAINED_CREATIVE", "candidate_span": "metaforă",
            "authority_support": None, "commitment": "Vehicul editorial.", "scope_basis": "CREATIVE_CONTAINED",
            "event_alignment": "CREATIVE_VEHICLE_ONLY", "authority_modality": "NOT_APPLICABLE",
            "candidate_modality": "NOT_APPLICABLE", "authority_timing": "NOT_APPLICABLE",
            "candidate_timing": "NOT_APPLICABLE", "independence_group": "G1", "scope_relation": relation,
            "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}


def _real(entry_id="P2", host="P1", relation="FACTUAL_RETURN_WITHIN_CREATIVE_HOST"):
    return {"entry_id": entry_id, "entry_type": "REAL_WORLD_COMMITMENT", "candidate_span": "fapt",
            "authority_support": "fapt", "commitment": "Faptul rămâne afirmat.", "scope_basis": "ASSERTED",
            "event_alignment": "GOVERNED_EVENT", "authority_modality": "CERTAIN_OR_ACTUAL",
            "candidate_modality": "CERTAIN_OR_ACTUAL", "authority_timing": "PAST", "candidate_timing": "PAST",
            "independence_group": "G2", "scope_relation": relation,
            "creative_host_entry_id": host if relation == "FACTUAL_RETURN_WITHIN_CREATIVE_HOST" else None,
            "factual_return_basis": "ASSERTION_SURVIVES"}


def _raw(entries, complete=True):
    value = {"stage_id": "PROPOSITION_LEDGER", "entries": entries,
             "coverage_receipt": {"candidate_reviewed_as_whole": complete,
                                  "embedded_propositions_checked": complete,
                                  "creative_scope_checked": complete,
                                  "unresolved_scope_present": not complete,
                                  "overlapping_spans_reconciled": complete,
                                  "integrated_creative_hosts_checked": complete,
                                  "factual_return_tests_completed": complete},
             "coverage_decision": "COMPLETE" if complete else "INDETERMINATE"}
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def test_integrated_host_and_factual_return_reaches_terminal_eos():
    assert StagePScopeGraphConstraintStateV1().feed(_raw([_creative(), _real()])).can_eos


def test_case01_pure_creative_host_reaches_terminal_eos():
    assert StagePScopeGraphConstraintStateV1().feed(_raw([_creative()])).can_eos


def test_standalone_real_world_commitment_reaches_terminal_eos():
    assert StagePScopeGraphConstraintStateV1().feed(_raw([_real(entry_id="P1", relation="STANDALONE")])).can_eos


def test_relation_choices_are_conditioned_before_emission():
    for entry, expected in [(_creative(), ("STANDALONE", "CREATIVE_HOST")),
                            (_real(entry_id="P1", relation="STANDALONE"),
                             ("STANDALONE", "FACTUAL_RETURN_WITHIN_CREATIVE_HOST"))]:
        raw = _raw([entry])
        prefix = raw.split('"scope_relation":"', 1)[0] + '"scope_relation":"'
        assert StagePScopeGraphConstraintStateV1().feed(prefix).choices == expected


def test_factual_return_requires_host_choice_before_emission():
    raw = _raw([_creative(), _real()])
    prefix = raw.rsplit('"creative_host_entry_id":', 1)[0] + '"creative_host_entry_id":'
    state = StagePScopeGraphConstraintStateV1().feed(prefix)
    assert state.choices == tuple(f'"P{i}"' for i in range(1, 9))


@pytest.mark.parametrize("entries,code", [
    ([_creative(), _real(host="P8")], "MISSING_CREATIVE_HOST"),
    ([_creative(relation="STANDALONE"), _real()], "HOST_IS_NOT_CREATIVE_HOST"),
    ([_creative(), _creative(entry_id="P1", relation="STANDALONE")], "DUPLICATE_ENTRY_ID"),
])
def test_invalid_graphs_fail_closed(entries, code):
    with pytest.raises(StagePRoleCoherenceConstraintViolationV1, match=code):
        StagePScopeGraphConstraintStateV1().feed(_raw(entries))


def test_incomplete_scope_receipts_cannot_close_complete_document():
    value = json.loads(_raw([_creative()]))
    value["coverage_receipt"]["factual_return_tests_completed"] = False
    with pytest.raises(StagePRoleCoherenceConstraintViolationV1, match="INVALID_COMPLETE_SCOPE_RECEIPTS"):
        StagePScopeGraphConstraintStateV1().feed(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def test_trailing_bytes_are_rejected_after_terminal():
    state = StagePScopeGraphConstraintStateV1().feed(_raw([_creative()]))
    with pytest.raises(StagePRoleCoherenceConstraintViolationV1, match="TRAILING_BYTES"):
        state.feed(" ")

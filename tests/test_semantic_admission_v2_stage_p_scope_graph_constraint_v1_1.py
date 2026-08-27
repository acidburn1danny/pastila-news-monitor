from __future__ import annotations

import json

import pytest

from pastila_scout.semantic_admission_v2.stage_p_role_coherence_constraint_v1 import StagePRoleCoherenceConstraintViolationV1
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_constraint_v1_1 import StagePScopeGraphConstraintStateV1_1


def _creative(entry_id="P1"):
    return {"entry_id": entry_id, "entry_type": "CONTAINED_CREATIVE", "candidate_span": "metaforă",
            "authority_support": None, "commitment": "Vehicul editorial.", "scope_basis": "CREATIVE_CONTAINED",
            "event_alignment": "CREATIVE_VEHICLE_ONLY", "authority_modality": "NOT_APPLICABLE",
            "candidate_modality": "NOT_APPLICABLE", "authority_timing": "NOT_APPLICABLE",
            "candidate_timing": "NOT_APPLICABLE", "independence_group": "G1", "scope_relation": "CREATIVE_HOST",
            "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}


def _real(*, support=None, event="NEW_UNSUPPORTED_EVENT", relation="STANDALONE", entry_id="P1", host=None):
    supported = support is not None
    return {"entry_id": entry_id, "entry_type": "REAL_WORLD_COMMITMENT", "candidate_span": "fapt",
            "authority_support": support, "commitment": "Propoziție reală.", "scope_basis": "ASSERTED",
            "event_alignment": event, "authority_modality": "CERTAIN_OR_ACTUAL" if supported else "NOT_APPLICABLE",
            "candidate_modality": "CERTAIN_OR_ACTUAL", "authority_timing": "PAST" if supported else "NOT_APPLICABLE",
            "candidate_timing": "PAST", "independence_group": "G2", "scope_relation": relation,
            "creative_host_entry_id": host, "factual_return_basis": "ASSERTION_SURVIVES"}


def _raw(entries):
    return json.dumps({"stage_id": "PROPOSITION_LEDGER", "entries": entries,
                       "coverage_receipt": {"candidate_reviewed_as_whole": True,
                                            "embedded_propositions_checked": True,
                                            "creative_scope_checked": True,
                                            "unresolved_scope_present": False,
                                            "overlapping_spans_reconciled": True,
                                            "integrated_creative_hosts_checked": True,
                                            "factual_return_tests_completed": True},
                       "coverage_decision": "COMPLETE"}, ensure_ascii=False, separators=(",", ":"))


def test_null_support_projects_out_governed_event_before_emission():
    raw = _raw([_real()])
    prefix = raw.split('"event_alignment":"', 1)[0] + '"event_alignment":"'
    state = StagePScopeGraphConstraintStateV1_1().feed(prefix)
    assert state.choices == ("NEW_UNSUPPORTED_EVENT",)
    with pytest.raises(StagePRoleCoherenceConstraintViolationV1, match="ENUM_MISMATCH"):
        state.feed("GOVERNED_EVENT")


def test_supported_real_entry_retains_governed_and_new_unsupported_choices():
    raw = _raw([_real(support="fapt", event="GOVERNED_EVENT")])
    prefix = raw.split('"event_alignment":"', 1)[0] + '"event_alignment":"'
    state = StagePScopeGraphConstraintStateV1_1().feed(prefix)
    assert state.choices == ("GOVERNED_EVENT", "NEW_UNSUPPORTED_EVENT")
    assert StagePScopeGraphConstraintStateV1_1().feed(raw).can_eos


def test_null_support_new_unsupported_standalone_reaches_eos():
    assert StagePScopeGraphConstraintStateV1_1().feed(_raw([_real()])).can_eos


def test_supported_new_unsupported_with_partial_support_reaches_eos():
    assert StagePScopeGraphConstraintStateV1_1().feed(_raw([_real(support="fapt")])).can_eos


def test_integrated_creative_and_governed_literal_reaches_eos():
    entries = [_creative(), _real(support="fapt", event="GOVERNED_EVENT",
                                  relation="FACTUAL_RETURN_WITHIN_CREATIVE_HOST", entry_id="P2", host="P1")]
    assert StagePScopeGraphConstraintStateV1_1().feed(_raw(entries)).can_eos


def test_pure_integrated_creative_reaches_eos_unchanged():
    assert StagePScopeGraphConstraintStateV1_1().feed(_raw([_creative()])).can_eos

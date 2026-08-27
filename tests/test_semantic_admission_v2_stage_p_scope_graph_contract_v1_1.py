from __future__ import annotations

import json

import pytest

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_contract_v1_1 import (
    ScopeGraphLedgerV1_1,
    validate_scope_graph_sources,
)


SUMMARY = "Compania a concediat 40 de oameni ieri."
CANDIDATE = "Compania, care a concediat 40 de oameni ieri, și-a pus empatia la păstrare."


def _creative(entry_id="P1", span=CANDIDATE, relation="CREATIVE_HOST"):
    return {"entry_id": entry_id, "entry_type": "CONTAINED_CREATIVE", "candidate_span": span,
            "authority_support": None, "commitment": "Metafora transformă editorial evenimentul.",
            "scope_basis": "CREATIVE_CONTAINED", "event_alignment": "CREATIVE_VEHICLE_ONLY",
            "authority_modality": "NOT_APPLICABLE", "candidate_modality": "NOT_APPLICABLE",
            "authority_timing": "NOT_APPLICABLE", "candidate_timing": "NOT_APPLICABLE",
            "independence_group": "G1", "scope_relation": relation,
            "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}


def _real(*, entry_id="P2", span="care a concediat 40 de oameni ieri", support="a concediat 40 de oameni ieri",
          event="GOVERNED_EVENT", relation="FACTUAL_RETURN_WITHIN_CREATIVE_HOST", host="P1", basis="ASSERTION_SURVIVES"):
    supported = support is not None
    return {"entry_id": entry_id, "entry_type": "REAL_WORLD_COMMITMENT", "candidate_span": span,
            "authority_support": support, "commitment": "Compania a concediat 40 de oameni ieri.",
            "scope_basis": "ASSERTED", "event_alignment": event,
            "authority_modality": "CERTAIN_OR_ACTUAL" if supported else "NOT_APPLICABLE",
            "candidate_modality": "CERTAIN_OR_ACTUAL", "authority_timing": "PAST" if supported else "NOT_APPLICABLE",
            "candidate_timing": "PAST", "independence_group": "G2", "scope_relation": relation,
            "creative_host_entry_id": host if relation == "FACTUAL_RETURN_WITHIN_CREATIVE_HOST" else None,
            "factual_return_basis": basis}


def _ledger(entries, complete=True):
    return {"stage_id": "PROPOSITION_LEDGER", "entries": entries,
            "coverage_receipt": {"candidate_reviewed_as_whole": complete,
                                 "embedded_propositions_checked": complete,
                                 "creative_scope_checked": complete, "unresolved_scope_present": not complete,
                                 "overlapping_spans_reconciled": complete,
                                 "integrated_creative_hosts_checked": complete,
                                 "factual_return_tests_completed": complete},
            "coverage_decision": "COMPLETE" if complete else "INDETERMINATE"}


def _validate(value):
    return ScopeGraphLedgerV1_1.model_validate_json(json.dumps(value, ensure_ascii=False), strict=True)


def test_frozen_probe_failure_is_rejected_by_governed_support_invariant():
    raw = {"entry_id": "P1", "entry_type": "REAL_WORLD_COMMITMENT", "candidate_span": CANDIDATE,
           "authority_support": None, "commitment": SUMMARY, "scope_basis": "PRESUPPOSED",
           "event_alignment": "GOVERNED_EVENT", "authority_modality": "NOT_APPLICABLE",
           "candidate_modality": "PROPOSED", "authority_timing": "NOT_APPLICABLE", "candidate_timing": "PAST",
           "independence_group": "G1", "scope_relation": "STANDALONE", "creative_host_entry_id": None,
           "factual_return_basis": "PRESUPPOSITION_SURVIVES"}
    with pytest.raises(ValueError, match="GOVERNED_EVENT_REQUIRES_AUTHORITY_SUPPORT"):
        _validate(_ledger([raw]))


def test_required_integrated_creative_shape_remains_valid():
    ledger = _validate(_ledger([_creative()]))
    validate_scope_graph_sources(ledger, factual_summary=SUMMARY, candidate=CANDIDATE)


def test_governed_literal_nested_in_creative_host_requires_and_accepts_exact_support():
    ledger = _validate(_ledger([_creative(), _real()]))
    validate_scope_graph_sources(ledger, factual_summary=SUMMARY, candidate=CANDIDATE)


def test_unsupported_presupposition_nested_in_host_remains_representable():
    candidate = "Primarul, supărat că a pierdut alegerile, și-a descoperit modestia."
    real = _real(span="supărat că a pierdut alegerile", support=None, event="NEW_UNSUPPORTED_EVENT",
                 basis="PRESUPPOSITION_SURVIVES")
    real.update(commitment="Primarul este supărat și a pierdut alegerile.", scope_basis="PRESUPPOSED",
                candidate_timing="PAST")
    ledger = _validate(_ledger([_creative(span=candidate), real]))
    validate_scope_graph_sources(ledger, factual_summary="Primarul a vorbit.", candidate=candidate)


def test_standalone_governed_and_standalone_unsupported_both_remain_valid():
    governed = _real(entry_id="P1", span="Compania a concediat 40 de oameni ieri.",
                     support=SUMMARY, relation="STANDALONE", host=None)
    ledger = _validate(_ledger([governed]))
    validate_scope_graph_sources(ledger, factual_summary=SUMMARY, candidate=SUMMARY)
    unsupported = _real(entry_id="P1", span="Directorul regretă decizia.", support=None,
                        event="NEW_UNSUPPORTED_EVENT", relation="STANDALONE", host=None,
                        basis="ASSERTION_SURVIVES")
    unsupported.update(commitment="Directorul regretă decizia.", candidate_timing="PRESENT")
    _validate(_ledger([unsupported]))


def test_new_unsupported_event_may_retain_partial_exact_support():
    entry = _real(entry_id="P1", span="Compania regretă concedierea.", support="Compania",
                  event="NEW_UNSUPPORTED_EVENT", relation="STANDALONE", host=None)
    entry.update(commitment="Compania regretă concedierea.", candidate_timing="PRESENT")
    _validate(_ledger([entry]))

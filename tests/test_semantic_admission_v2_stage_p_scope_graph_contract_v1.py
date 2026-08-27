from __future__ import annotations

import json

import pytest

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_contract_v1 import (
    ScopeGraphLedgerV1,
    validate_scope_graph_sources,
)

SUMMARY = "Compania a concediat 40 de oameni ieri."
CANDIDATE = "Compania, care a concediat 40 de oameni ieri, și-a pus empatia la păstrare."


def _creative(entry_id="P1", span=CANDIDATE, relation="CREATIVE_HOST"):
    return {"entry_id": entry_id, "entry_type": "CONTAINED_CREATIVE", "candidate_span": span,
            "authority_support": None, "commitment": "Empatia pusă la păstrare este vehicul editorial.",
            "scope_basis": "CREATIVE_CONTAINED", "event_alignment": "CREATIVE_VEHICLE_ONLY",
            "authority_modality": "NOT_APPLICABLE", "candidate_modality": "NOT_APPLICABLE",
            "authority_timing": "NOT_APPLICABLE", "candidate_timing": "NOT_APPLICABLE",
            "independence_group": "G1", "scope_relation": relation,
            "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE"}


def _real(entry_id="P2", span="care a concediat 40 de oameni ieri", host="P1", support="a concediat 40 de oameni ieri"):
    return {"entry_id": entry_id, "entry_type": "REAL_WORLD_COMMITMENT", "candidate_span": span,
            "authority_support": support, "commitment": "Compania a concediat 40 de oameni ieri.",
            "scope_basis": "ASSERTED", "event_alignment": "GOVERNED_EVENT",
            "authority_modality": "CERTAIN_OR_ACTUAL", "candidate_modality": "CERTAIN_OR_ACTUAL",
            "authority_timing": "PAST", "candidate_timing": "PAST", "independence_group": "G2",
            "scope_relation": "FACTUAL_RETURN_WITHIN_CREATIVE_HOST", "creative_host_entry_id": host,
            "factual_return_basis": "ASSERTION_SURVIVES"}


def _ledger(entries, complete=True):
    return {"stage_id": "PROPOSITION_LEDGER", "entries": entries,
            "coverage_receipt": {"candidate_reviewed_as_whole": complete,
                                 "embedded_propositions_checked": complete,
                                 "creative_scope_checked": complete,
                                 "unresolved_scope_present": not complete,
                                 "overlapping_spans_reconciled": complete,
                                 "integrated_creative_hosts_checked": complete,
                                 "factual_return_tests_completed": complete},
            "coverage_decision": "COMPLETE" if complete else "INDETERMINATE"}


def _validate(value):
    return ScopeGraphLedgerV1.model_validate_json(json.dumps(value, ensure_ascii=False), strict=True)


def test_case01_pure_integrated_creative_shape():
    candidate = "Când banii se ascund în umbră, iar angajații rămân la lumină, pare că și hotelul ar avea nevoie de o cameră cu mai multă transparență."
    ledger = _validate(_ledger([_creative(span=candidate)]))
    validate_scope_graph_sources(ledger, factual_summary="plată la negru", candidate=candidate)
    assert len(ledger.entries) == 1


def test_governed_literal_clause_inside_creative_host():
    ledger = _validate(_ledger([_creative(), _real()]))
    validate_scope_graph_sources(ledger, factual_summary=SUMMARY, candidate=CANDIDATE)


def test_unsupported_presupposition_inside_creative_host_remains_representable():
    candidate = "Primarul, supărat că a pierdut alegerile, și-a descoperit modestia."
    host = _creative(span=candidate)
    real = _real(span="supărat că a pierdut alegerile", support=None)
    real.update(commitment="Primarul este supărat și a pierdut alegerile.", scope_basis="PRESUPPOSED",
                event_alignment="NEW_UNSUPPORTED_EVENT", authority_modality="NOT_APPLICABLE",
                authority_timing="NOT_APPLICABLE", factual_return_basis="PRESUPPOSITION_SURVIVES")
    ledger = _validate(_ledger([host, real]))
    validate_scope_graph_sources(ledger, factual_summary="Primarul a vorbit.", candidate=candidate)


def test_pure_creative_components_need_no_real_entries():
    candidate = "Bugetul intră pe ușă și transparența iese pe geam."
    ledger = _validate(_ledger([_creative(span=candidate)]))
    validate_scope_graph_sources(ledger, factual_summary="Buget aprobat.", candidate=candidate)


def test_unresolved_overlap_abstains():
    entry = {"entry_id": "P1", "entry_type": "UNRESOLVED_SCOPE", "candidate_span": "Compania",
             "authority_support": None, "commitment": "Relație nerezolvată.", "scope_basis": "UNRESOLVED",
             "event_alignment": "UNRESOLVED", "authority_modality": "NOT_APPLICABLE",
             "candidate_modality": "UNRESOLVED", "authority_timing": "NOT_APPLICABLE",
             "candidate_timing": "UNRESOLVED", "independence_group": "G1",
             "scope_relation": "UNRESOLVED_RELATION", "creative_host_entry_id": None,
             "factual_return_basis": "UNRESOLVED"}
    _validate(_ledger([entry], complete=False))


@pytest.mark.parametrize("mutation,match", [("missing", "MISSING_CREATIVE_HOST"),
                                               ("noncreative", "HOST_IS_NOT_CREATIVE_HOST")])
def test_bad_host_references_fail(mutation, match):
    real = _real(host="P8" if mutation == "missing" else "P3")
    entries = [_creative(), real]
    if mutation == "noncreative":
        entries.append(_real(entry_id="P3", host="P1"))
    with pytest.raises(ValueError, match=match):
        _validate(_ledger(entries))


def test_self_host_fails_locally():
    with pytest.raises(ValueError, match="SELF_HOST_REFERENCE"):
        _validate(_ledger([_creative(), _real(entry_id="P2", host="P2")]))


def test_nonoverlapping_host_fails_source_validation():
    candidate = "Fapt literal. Metaforă separată."
    ledger = _validate(_ledger([_creative(span="Metaforă separată."),
                                _real(span="Fapt literal.", support="Fapt literal.")]))
    with pytest.raises(ValueError, match="DOES_NOT_OVERLAP"):
        validate_scope_graph_sources(ledger, factual_summary="Fapt literal.", candidate=candidate)


def test_complete_requires_scope_receipts():
    value = _ledger([_creative()])
    value["coverage_receipt"]["overlapping_spans_reconciled"] = False
    with pytest.raises(ValueError, match="COMPLETE_SCOPE_GRAPH_INCOHERENT"):
        _validate(value)


def test_multiple_valid_segmentations_are_allowed():
    entries = [_creative(), _creative(entry_id="P2", span="și-a pus empatia la păstrare.",
                                      relation="STANDALONE")]
    ledger = _validate(_ledger(entries))
    validate_scope_graph_sources(ledger, factual_summary=SUMMARY, candidate=CANDIDATE)

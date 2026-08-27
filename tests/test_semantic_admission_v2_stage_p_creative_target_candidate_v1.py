from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_creative_target_constraint_v1 import (
    StagePCreativeTargetConstraintStateV1,
)
from pastila_scout.semantic_admission_v2.stage_p_creative_target_contract_v1 import (
    CreativeTargetLedgerV1, validate_creative_target_sources,
)
from pastila_scout.semantic_admission_v2.stage_p_creative_target_prompt_v1 import (
    StagePCreativeTargetPromptContractV1,
)
from pastila_scout.semantic_admission_v2.stage_p_creative_target_request_candidate_v1 import (
    StagePCreativeTargetRequestCandidateV1,
)
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "Banii se ascund în umbră, iar hotelul cere transparență."
FACT = "Hotelul a plătit salariile la negru."


def _entry(entry_id, kind, span, *, host=None):
    creative = kind == "creative"; unresolved = kind == "unresolved"; supported = kind == "supported"
    return {"entry_id": entry_id,
        "entry_type": "CONTAINED_CREATIVE" if creative else "UNRESOLVED_SCOPE" if unresolved else "REAL_WORLD_COMMITMENT",
        "candidate_span": span, "authority_support": "a plătit salariile la negru" if supported else None,
        "commitment": "Transformare editorială." if creative else "Ascundere financiară.",
        "scope_basis": "CREATIVE_CONTAINED" if creative else "UNRESOLVED" if unresolved else "ASSERTED",
        "event_alignment": "CREATIVE_VEHICLE_ONLY" if creative else "UNRESOLVED" if unresolved else "GOVERNED_EVENT" if supported else "NEW_UNSUPPORTED_EVENT",
        "authority_modality": "NOT_APPLICABLE" if not supported else "CERTAIN_OR_ACTUAL",
        "candidate_modality": "NOT_APPLICABLE" if creative else "UNRESOLVED" if unresolved else "CERTAIN_OR_ACTUAL",
        "authority_timing": "NOT_APPLICABLE" if not supported else "PAST",
        "candidate_timing": "NOT_APPLICABLE" if creative else "UNRESOLVED" if unresolved else "PRESENT",
        "independence_group": "G1" if entry_id == "P1" else "G2",
        "scope_relation": "CREATIVE_HOST" if creative and host is None else "UNRESOLVED_RELATION" if unresolved else "FACTUAL_RETURN_WITHIN_CREATIVE_HOST" if host else "STANDALONE",
        "creative_host_entry_id": host,
        "factual_return_basis": "NOT_APPLICABLE" if creative else "UNRESOLVED" if unresolved else "ASSERTION_SURVIVES"}


def _receipt(unresolved=False):
    return {"candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
        "creative_scope_checked": True, "unresolved_scope_present": unresolved,
        "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
        "factual_return_tests_completed": True, "creative_targets_enumerated": True,
        "target_classes_reviewed": True, "target_to_ledger_reconciled": True}


def _feed(value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    state = StagePCreativeTargetConstraintStateV1().feed(raw)
    assert state.can_eos
    return raw


def test_pure_creative_fixture_is_valid_and_dfa_live():
    value = {"stage_id": "PROPOSITION_LEDGER", "entries": [_entry("P1", "creative", CANDIDATE)],
        "creative_target_audits": [{"audit_id": "T1", "creative_host_entry_id": "P1",
            "vehicle_span": "Banii se ascund în umbră", "semantic_target": "Critică editorială a opacității.",
            "target_class": "NONFACTUAL_EDITORIAL_OR_CREATIVE", "survival_basis": "DOES_NOT_SURVIVE_AS_FACT",
            "proposition_entry_id": None, "resolution": "RETAINED_NONFACTUAL"}],
        "coverage_receipt": _receipt(), "coverage_decision": "COMPLETE"}
    ledger = CreativeTargetLedgerV1.model_validate_json(_feed(value), strict=True)
    validate_creative_target_sources(ledger, factual_summary=FACT, candidate=CANDIDATE)


def test_governed_embedded_return_fixture_is_valid_and_linked():
    value = {"stage_id": "PROPOSITION_LEDGER",
        "entries": [_entry("P1", "creative", CANDIDATE), _entry("P2", "supported", "Banii se ascund în umbră", host="P1")],
        "creative_target_audits": [{"audit_id": "T1", "creative_host_entry_id": "P1",
            "vehicle_span": "Banii se ascund în umbră", "semantic_target": "Ascundere financiară.",
            "target_class": "REAL_WORLD_PROPOSITION", "survival_basis": "ASSERTION_SURVIVES",
            "proposition_entry_id": "P2", "resolution": "RECONCILED_TO_LEDGER"}],
        "coverage_receipt": _receipt(), "coverage_decision": "COMPLETE"}
    ledger = CreativeTargetLedgerV1.model_validate_json(_feed(value), strict=True)
    validate_creative_target_sources(ledger, factual_summary=FACT, candidate=CANDIDATE)


def test_target_tuple_mismatches_fail_contract_and_constraint():
    value = {"stage_id": "PROPOSITION_LEDGER", "entries": [_entry("P1", "creative", CANDIDATE)],
        "creative_target_audits": [{"audit_id": "T1", "creative_host_entry_id": "P1",
            "vehicle_span": "Banii", "semantic_target": "Ascundere.",
            "target_class": "REAL_WORLD_PROPOSITION", "survival_basis": "ASSERTION_SURVIVES",
            "proposition_entry_id": None, "resolution": "RETAINED_NONFACTUAL"}],
        "coverage_receipt": _receipt(), "coverage_decision": "COMPLETE"}
    with pytest.raises(Exception):
        CreativeTargetLedgerV1.model_validate(value, strict=True)
    with pytest.raises(Exception):
        _feed(value)


def test_unresolved_target_requires_unresolved_entry_and_indeterminate():
    audit = {"audit_id": "T1", "creative_host_entry_id": "P1", "vehicle_span": "Banii",
        "semantic_target": "Relație semantică ambiguă.", "target_class": "UNRESOLVED_TARGET",
        "survival_basis": "UNRESOLVED", "proposition_entry_id": None,
        "resolution": "FAIL_CLOSED_UNRESOLVED"}
    invalid = {"stage_id": "PROPOSITION_LEDGER", "entries": [_entry("P1", "creative", CANDIDATE)],
        "creative_target_audits": [audit], "coverage_receipt": _receipt(unresolved=True),
        "coverage_decision": "INDETERMINATE"}
    with pytest.raises(Exception): CreativeTargetLedgerV1.model_validate(invalid, strict=True)
    with pytest.raises(Exception): _feed(invalid)
    valid = {**invalid, "entries": [_entry("P1", "creative", CANDIDATE),
        _entry("P2", "unresolved", "hotelul cere transparență")]}
    ledger = CreativeTargetLedgerV1.model_validate_json(_feed(valid), strict=True)
    validate_creative_target_sources(ledger, factual_summary=FACT, candidate=CANDIDATE)


def test_literal_ledger_allows_empty_target_collection():
    value = {"stage_id": "PROPOSITION_LEDGER",
        "entries": [_entry("P1", "supported", "Banii se ascund în umbră")],
        "creative_target_audits": [], "coverage_receipt": _receipt(), "coverage_decision": "COMPLETE"}
    ledger = CreativeTargetLedgerV1.model_validate_json(_feed(value), strict=True)
    validate_creative_target_sources(ledger, factual_summary=FACT, candidate=CANDIDATE)


def test_prompt_is_exactly_padded_candidate_first_and_hidden_labels_absent():
    contract = StagePCreativeTargetPromptContractV1(ROOT)
    rendered = contract.render(factual_summary=FACT, candidate=CANDIDATE)
    assert rendered.count(CANDIDATE) == 1 and rendered.count(FACT) == 1
    assert rendered.index(CANDIDATE) < rendered.index(FACT)
    assert "HMCV1-SASC-01" not in rendered and "owner-approved" not in rendered.lower()


def test_request_candidate_preserves_prompt_and_application_authority():
    candidate = StagePCreativeTargetRequestCandidateV1(project_root=ROOT)
    request = {"candidate": CANDIDATE, "factual_summary": FACT}
    authority = candidate.build_authority(request, requested_at=datetime(2026, 8, 26, tzinfo=UTC))
    unit = authority.request_envelope.request_units[0]
    assert "\n\n".join(message.content for message in unit.messages) == candidate.render_prompt(request)
    assert authority.timeout_policy.timeout_seconds == 240.0
    assert len(candidate.candidate_identity) == 64


def test_synthetic_token_trie_projects_each_prefix_without_model_or_tokenizer():
    value = {"stage_id": "PROPOSITION_LEDGER", "entries": [_entry("P1", "creative", CANDIDATE)],
        "creative_target_audits": [{"audit_id": "T1", "creative_host_entry_id": "P1",
            "vehicle_span": "Banii", "semantic_target": "Critică editorială.",
            "target_class": "NONFACTUAL_EDITORIAL_OR_CREATIVE", "survival_basis": "DOES_NOT_SURVIVE_AS_FACT",
            "proposition_entry_id": None, "resolution": "RETAINED_NONFACTUAL"}],
        "coverage_receipt": _receipt(), "coverage_decision": "COMPLETE"}
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    chars = sorted(set(raw)); pieces = {index + 1: char for index, char in enumerate(chars)}
    reverse = {char: token_id for token_id, char in pieces.items()}
    projector = StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=999999)
    state = StagePCreativeTargetConstraintStateV1()
    for char in raw:
        assert reverse[char] in projector.allowed_token_ids(state)
        state = state.feed(char)
    assert projector.allowed_token_ids(state) == (999999,)

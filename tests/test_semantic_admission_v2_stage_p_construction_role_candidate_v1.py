from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_role_constraint_v1 import (
    StagePConstructionRoleConstraintStateV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_role_contract_v1 import (
    ConstructionRoleLedgerV1,
    validate_construction_role_sources,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_role_prompt_v1 import (
    StagePConstructionRolePromptContractV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_role_request_candidate_v1 import (
    StagePConstructionRoleRequestCandidateV1,
)
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "Banii se ascund în umbră, iar hotelul cere transparență."
FACT = "Hotelul a plătit salariile la negru."


def _entry(entry_id: str, kind: str, span: str, *, host: str | None = None):
    creative = kind == "creative"; unresolved = kind == "unresolved"; supported = kind == "supported"
    return {"entry_id": entry_id,
        "entry_type": "CONTAINED_CREATIVE" if creative else "UNRESOLVED_SCOPE" if unresolved else "REAL_WORLD_COMMITMENT",
        "candidate_span": span, "authority_support": "a plătit salariile la negru" if supported else None,
        "commitment": "Transformare editorială." if creative else "Relație ambiguă." if unresolved else "Ascundere financiară.",
        "scope_basis": "CREATIVE_CONTAINED" if creative else "UNRESOLVED" if unresolved else "ASSERTED",
        "event_alignment": "CREATIVE_VEHICLE_ONLY" if creative else "UNRESOLVED" if unresolved else "GOVERNED_EVENT" if supported else "NEW_UNSUPPORTED_EVENT",
        "authority_modality": "NOT_APPLICABLE" if not supported else "CERTAIN_OR_ACTUAL",
        "candidate_modality": "NOT_APPLICABLE" if creative else "UNRESOLVED" if unresolved else "CERTAIN_OR_ACTUAL",
        "authority_timing": "NOT_APPLICABLE" if not supported else "PAST",
        "candidate_timing": "NOT_APPLICABLE" if creative else "UNRESOLVED" if unresolved else "PRESENT",
        "independence_group": "G1" if entry_id == "P1" else "G2",
        "scope_relation": "CREATIVE_HOST" if creative else "UNRESOLVED_RELATION" if unresolved else "FACTUAL_RETURN_WITHIN_CREATIVE_HOST" if host else "STANDALONE",
        "creative_host_entry_id": host,
        "factual_return_basis": "NOT_APPLICABLE" if creative else "UNRESOLVED" if unresolved else "ASSERTION_SURVIVES"}


def _receipt(unresolved: bool = False):
    return {"candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
        "creative_scope_checked": True, "unresolved_scope_present": unresolved,
        "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
        "factual_return_tests_completed": True, "creative_targets_enumerated": True,
        "target_classes_reviewed": True, "target_to_ledger_reconciled": True,
        "construction_roles_reviewed": True, "construction_to_ledger_reconciled": True}


def _feed(value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    state = StagePConstructionRoleConstraintStateV1().feed(raw)
    assert state.can_eos
    return raw


def _literal_value():
    return {"stage_id": "PROPOSITION_LEDGER", "construction_role_audit": {
        "candidate_reviewed_as_construction": True,
        "overall_disposition": "NO_MATERIAL_CREATIVE_CONSTRUCTION",
        "construction_records": [{"construction_id": "C1", "candidate_span": CANDIDATE,
            "construction_role": "LITERAL_ONLY", "role_basis": "Raportare literală fără transformare.",
            "creative_host_entry_id": None, "literal_or_return_entry_ids": ["P1"],
            "resolution": "LITERAL_PATH_RETAINED"}],
        "literal_path_basis": "Sensul comunicat este literal."},
        "entries": [_entry("P1", "supported", CANDIDATE)], "creative_target_audits": [],
        "coverage_receipt": _receipt(), "coverage_decision": "COMPLETE"}


def _mixed_value():
    return {"stage_id": "PROPOSITION_LEDGER", "construction_role_audit": {
        "candidate_reviewed_as_construction": True,
        "overall_disposition": "ONE_OR_MORE_MATERIAL_CONSTRUCTIONS",
        "construction_records": [{"construction_id": "C1", "candidate_span": CANDIDATE,
            "construction_role": "MIXED_CREATIVE_AND_REAL_WORLD",
            "role_basis": "Ascunderea este vehicul creativ cu o afirmație factuală integrată.",
            "creative_host_entry_id": "P1", "literal_or_return_entry_ids": ["P2"],
            "resolution": "MIXED_HOST_AND_RETURNS_REQUIRED"}], "literal_path_basis": None},
        "entries": [_entry("P1", "creative", CANDIDATE),
                    _entry("P2", "supported", "Banii se ascund în umbră", host="P1")],
        "creative_target_audits": [{"audit_id": "T1", "creative_host_entry_id": "P1",
            "vehicle_span": "Banii se ascund în umbră", "semantic_target": "Ascundere financiară.",
            "target_class": "REAL_WORLD_PROPOSITION", "survival_basis": "ASSERTION_SURVIVES",
            "proposition_entry_id": "P2", "resolution": "RECONCILED_TO_LEDGER"}],
        "coverage_receipt": _receipt(), "coverage_decision": "COMPLETE"}


@pytest.mark.parametrize("factory", [_literal_value, _mixed_value])
def test_literal_and_mixed_paths_are_contract_and_dfa_valid(factory):
    ledger = ConstructionRoleLedgerV1.model_validate_json(_feed(factory()), strict=True)
    validate_construction_role_sources(ledger, factual_summary=FACT, candidate=CANDIDATE)


def test_material_language_cannot_complete_without_mapped_host():
    value = _mixed_value()
    value["construction_role_audit"]["construction_records"][0]["creative_host_entry_id"] = None
    value["construction_role_audit"]["construction_records"][0]["literal_or_return_entry_ids"] = []
    with pytest.raises(Exception): ConstructionRoleLedgerV1.model_validate(value, strict=True)
    with pytest.raises(Exception): _feed(value)


def test_creative_host_cannot_escape_construction_mapping():
    value = _mixed_value()
    value["construction_role_audit"] = {"candidate_reviewed_as_construction": True,
        "overall_disposition": "NO_MATERIAL_CREATIVE_CONSTRUCTION", "construction_records": [],
        "literal_path_basis": "Pretins literal."}
    with pytest.raises(Exception): ConstructionRoleLedgerV1.model_validate(value, strict=True)
    with pytest.raises(Exception): _feed(value)


def test_prompt_padding_candidate_first_and_hidden_annotations_absent():
    contract = StagePConstructionRolePromptContractV1(ROOT)
    rendered = contract.render(factual_summary=FACT, candidate=CANDIDATE)
    assert rendered.index(CANDIDATE) < rendered.index(FACT)
    assert "HMCV1-SASC-01" not in rendered and "owner-quality" not in rendered.lower()


def test_request_identity_and_application_construction_are_zero_inference():
    candidate = StagePConstructionRoleRequestCandidateV1(project_root=ROOT)
    request = {"candidate": CANDIDATE, "factual_summary": FACT}
    authority = candidate.build_authority(request, requested_at=datetime(2026, 8, 26, tzinfo=UTC))
    unit = authority.request_envelope.request_units[0]
    assert "\n\n".join(message.content for message in unit.messages) == candidate.render_prompt(request)
    assert authority.timeout_policy.timeout_seconds == 240.0
    assert len(candidate.candidate_identity) == 64


def test_synthetic_trie_accepts_literal_and_mixed_ledgers_without_inference():
    for value in (_literal_value(), _mixed_value()):
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        pieces = {index + 1: char for index, char in enumerate(sorted(set(raw)))}
        reverse = {char: token_id for token_id, char in pieces.items()}
        projector = StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=999999)
        state = StagePConstructionRoleConstraintStateV1()
        for char in raw:
            assert reverse[char] in projector.allowed_token_ids(state)
            state = state.feed(char)
        assert projector.allowed_token_ids(state) == (999999,)

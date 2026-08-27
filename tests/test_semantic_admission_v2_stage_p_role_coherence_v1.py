from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_role_coherence_candidate_v1 import StagePRoleCoherenceCandidateV1
from pastila_scout.semantic_admission_v2.stage_p_role_coherence_constraint_v1 import (
    StagePRoleCoherenceConstraintStateV1,
    StagePRoleCoherenceConstraintViolationV1,
)
from pastila_scout.semantic_admission_v2.stage_p_role_coherence_contract_v1 import (
    RoleCoherentLedgerV1,
    validate_role_coherent_source_membership,
)
from pastila_scout.semantic_admission_v2.stage_p_role_coherence_prompt_v1 import StagePRoleCoherencePromptContractV1
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = "Un complex turistic din Vâlcea a plătit la negru salariile celor 70 de angajați, în ultimii 3 ani, cu 4,3 milioane de lei."
CANDIDATE = "Când banii se ascund în umbră, iar angajații rămân la lumină, pare că și hotelul ar avea nevoie de o cameră cu mai multă transparență."


def _entry(entry_type: str = "CONTAINED_CREATIVE", **changes) -> dict:
    value = {
        "entry_id": "P1",
        "entry_type": entry_type,
        "candidate_span": CANDIDATE,
        "authority_support": None,
        "commitment": "Relația story-locală leagă plata ascunsă de camera și transparența hotelului fără a afirma un eveniment nou.",
        "scope_basis": "CREATIVE_CONTAINED",
        "event_alignment": "CREATIVE_VEHICLE_ONLY",
        "authority_modality": "NOT_APPLICABLE",
        "candidate_modality": "NOT_APPLICABLE",
        "authority_timing": "NOT_APPLICABLE",
        "candidate_timing": "NOT_APPLICABLE",
        "independence_group": "G1",
    }
    value.update(changes)
    return value


def _ledger(entries=None, *, complete=True) -> dict:
    return {
        "stage_id": "PROPOSITION_LEDGER",
        "entries": entries or [_entry()],
        "coverage_receipt": {
            "candidate_reviewed_as_whole": complete,
            "embedded_propositions_checked": complete,
            "creative_scope_checked": complete,
            "unresolved_scope_present": not complete,
        },
        "coverage_decision": "COMPLETE" if complete else "INDETERMINATE",
    }


def _raw(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def test_case01_shape_is_complete_role_coherent_and_source_bound() -> None:
    raw = _raw(_ledger())
    assert StagePRoleCoherenceConstraintStateV1().feed(raw).can_eos
    ledger = RoleCoherentLedgerV1.model_validate_json(raw, strict=True)
    validate_role_coherent_source_membership(ledger, factual_summary=SUMMARY, candidate=CANDIDATE)


@pytest.mark.parametrize("axis", ["scope_basis", "event_alignment", "candidate_modality", "candidate_timing"])
def test_real_world_commitment_cannot_hide_an_unresolved_axis(axis: str) -> None:
    real = _entry(
        "REAL_WORLD_COMMITMENT", commitment="Propoziție reală", scope_basis="ASSERTED",
        event_alignment="NEW_UNSUPPORTED_EVENT", candidate_modality="CERTAIN_OR_ACTUAL",
        candidate_timing="PRESENT",
    )
    real[axis] = "UNRESOLVED"
    raw = _raw(_ledger([real]))
    with pytest.raises((StagePRoleCoherenceConstraintViolationV1, ValueError)):
        StagePRoleCoherenceConstraintStateV1().feed(raw)
    with pytest.raises(ValueError):
        RoleCoherentLedgerV1.model_validate_json(raw, strict=True)


def test_contained_creative_rejects_real_world_axes() -> None:
    raw = _raw(_ledger([_entry(scope_basis="ASSERTED", event_alignment="GOVERNED_EVENT")]))
    with pytest.raises(StagePRoleCoherenceConstraintViolationV1, match="CONTAINED_CREATIVE_ROLE_INCOHERENT"):
        StagePRoleCoherenceConstraintStateV1().feed(raw)
    with pytest.raises(ValueError, match="CONTAINED_CREATIVE_ROLE_INCOHERENT"):
        RoleCoherentLedgerV1.model_validate_json(raw, strict=True)


def test_unresolved_scope_is_indeterminate_and_explicit() -> None:
    entry = _entry(
        "UNRESOLVED_SCOPE", commitment="Rolul semantic nu poate fi stabilit", scope_basis="UNRESOLVED",
        event_alignment="UNRESOLVED", candidate_modality="UNRESOLVED", candidate_timing="UNRESOLVED",
    )
    raw = _raw(_ledger([entry], complete=False))
    assert StagePRoleCoherenceConstraintStateV1().feed(raw).can_eos
    RoleCoherentLedgerV1.model_validate_json(raw, strict=True)


def test_mixed_creative_and_embedded_real_world_proposition_is_representable() -> None:
    real_span = "angajații rămân la lumină"
    real = _entry(
        "REAL_WORLD_COMMITMENT", entry_id="P2", candidate_span=real_span,
        commitment="Subspanul este tratat separat când poartă o propoziție reală independentă.",
        scope_basis="NECESSARILY_IMPLIED", event_alignment="NEW_UNSUPPORTED_EVENT",
        candidate_modality="CERTAIN_OR_ACTUAL", candidate_timing="PRESENT", independence_group="G2",
    )
    raw = _raw(_ledger([_entry(), real]))
    ledger = RoleCoherentLedgerV1.model_validate_json(raw, strict=True)
    validate_role_coherent_source_membership(ledger, factual_summary=SUMMARY, candidate=CANDIDATE)


def test_coverage_is_structurally_after_entries_and_receipt() -> None:
    raw = _raw(_ledger())
    assert raw.index('"entries"') < raw.index('"coverage_receipt"') < raw.index('"coverage_decision"')
    with pytest.raises(StagePRoleCoherenceConstraintViolationV1):
        StagePRoleCoherenceConstraintStateV1().feed('{"stage_id":"PROPOSITION_LEDGER","coverage_decision"')


def test_prompt_identity_padding_unicode_and_request_are_zero_inference() -> None:
    contract = StagePRoleCoherencePromptContractV1(ROOT)
    prompt = contract.render(factual_summary=SUMMARY, candidate=CANDIDATE)
    assert prompt.endswith(CANDIDATE + "\n\nOUTPUT BYTES: first {, last }, exactly one JSON object, nothing else.")
    assert not prompt.endswith("\n") and "factual-return test" in prompt
    candidate = StagePRoleCoherenceCandidateV1(project_root=ROOT)
    authority = candidate.build_authority(
        {"factual_summary": SUMMARY, "candidate": CANDIDATE},
        requested_at=datetime(2026, 8, 26, 12, 0, tzinfo=UTC),
    )
    assert authority.request_envelope.request_units[0].messages[0].content == prompt
    assert candidate.prompt_identity.startswith("sha256:") and candidate.grammar_identity.startswith("sha256:")
    assert not hasattr(candidate, "execute") and not hasattr(candidate, "__call__")


def test_synthetic_constrained_trie_reaches_only_terminal_eos() -> None:
    raw = _raw(_ledger())
    pieces = {0: "<eos>", **{index: char for index, char in enumerate(sorted(set(raw)), 1)}}
    projector = StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=0)
    state = StagePRoleCoherenceConstraintStateV1()
    for char in raw:
        state = state.feed(char)
    assert projector.allowed_token_ids(state) == (0,)
    assert projector.trie_node_count > 1


def test_candidate_modules_have_no_executor_provider_or_stage_c_edge() -> None:
    import pastila_scout.semantic_admission_v2.stage_p_role_coherence_constraint_v1 as constraint
    import pastila_scout.semantic_admission_v2.stage_p_role_coherence_contract_v1 as contract
    import pastila_scout.semantic_admission_v2.stage_p_role_coherence_candidate_v1 as candidate
    assert "stage_c" not in inspect.getsource(candidate).lower()
    assert "executor" not in inspect.getsource(candidate).lower()
    assert "provider" not in inspect.getsource(constraint).lower()
    assert "provider" not in inspect.getsource(contract).lower()

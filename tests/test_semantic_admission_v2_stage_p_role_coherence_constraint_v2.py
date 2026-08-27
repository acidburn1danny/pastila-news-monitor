from __future__ import annotations

import json

import pytest

from pastila_scout.semantic_admission_v2.stage_p_role_coherence_constraint_v1 import StagePRoleCoherenceConstraintViolationV1
from pastila_scout.semantic_admission_v2.stage_p_role_coherence_constraint_v2 import (
    REAL_EVENTS, REAL_MODALITIES, REAL_SCOPES, REAL_TIMINGS, StagePRoleCoherenceConstraintStateV2,
)


def _entry(role: str, *, supported: bool = False, unresolved_axis: str = "scope_basis") -> dict:
    value = {
        "entry_id":"P1", "entry_type":role, "candidate_span":"hotelul",
        "authority_support":"complex turistic" if supported else None, "commitment":"Descriere semantică story-locală.",
        "scope_basis":"CREATIVE_CONTAINED", "event_alignment":"CREATIVE_VEHICLE_ONLY",
        "authority_modality":"NOT_APPLICABLE", "candidate_modality":"NOT_APPLICABLE",
        "authority_timing":"NOT_APPLICABLE", "candidate_timing":"NOT_APPLICABLE", "independence_group":"G1",
    }
    if role == "REAL_WORLD_COMMITMENT":
        value.update(scope_basis="ASSERTED", event_alignment="GOVERNED_EVENT", candidate_modality="CERTAIN_OR_ACTUAL",
                     candidate_timing="PRESENT", authority_modality="POSSIBLE" if supported else "NOT_APPLICABLE",
                     authority_timing="FUTURE" if supported else "NOT_APPLICABLE")
    elif role == "UNRESOLVED_SCOPE":
        value.update(scope_basis="ASSERTED", event_alignment="GOVERNED_EVENT", candidate_modality="POSSIBLE", candidate_timing="PRESENT")
        value[unresolved_axis] = "UNRESOLVED"
    return value


def _raw(entry: dict) -> str:
    unresolved = entry["entry_type"] == "UNRESOLVED_SCOPE"
    value = {"stage_id":"PROPOSITION_LEDGER", "entries":[entry], "coverage_receipt":{
        "candidate_reviewed_as_whole":not unresolved, "embedded_propositions_checked":not unresolved,
        "creative_scope_checked":not unresolved, "unresolved_scope_present":unresolved},
        "coverage_decision":"INDETERMINATE" if unresolved else "COMPLETE"}
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


@pytest.mark.parametrize("role,supported", [
    ("CONTAINED_CREATIVE", False), ("REAL_WORLD_COMMITMENT", False),
    ("REAL_WORLD_COMMITMENT", True), ("UNRESOLVED_SCOPE", False), ("UNRESOLVED_SCOPE", True),
])
def test_every_role_and_authority_state_has_a_terminal_path(role: str, supported: bool) -> None:
    raw = _raw(_entry(role, supported=supported))
    assert StagePRoleCoherenceConstraintStateV2().feed(raw).can_eos


@pytest.mark.parametrize("axis", ["scope_basis", "event_alignment", "candidate_modality", "candidate_timing"])
@pytest.mark.parametrize("supported", [False, True])
def test_unresolved_role_has_a_terminal_path_for_every_candidate_axis(axis: str, supported: bool) -> None:
    raw = _raw(_entry("UNRESOLVED_SCOPE", supported=supported, unresolved_axis=axis))
    assert StagePRoleCoherenceConstraintStateV2().feed(raw).can_eos


def test_observed_real_world_unresolved_choice_is_blocked_before_entry_closure() -> None:
    raw = _raw(_entry("REAL_WORLD_COMMITMENT"))
    prefix, suffix = raw.split('"candidate_modality":"', 1)
    state = StagePRoleCoherenceConstraintStateV2().feed(prefix + '"candidate_modality":"')
    assert state.mode == "CHOICE" and state.choices == REAL_MODALITIES
    with pytest.raises(StagePRoleCoherenceConstraintViolationV1, match="ENUM_MISMATCH"):
        state.feed("UNRESOLVED")
    assert suffix.startswith("CERTAIN_OR_ACTUAL")


def test_role_conditioned_choice_sets_are_exact() -> None:
    real = _raw(_entry("REAL_WORLD_COMMITMENT", supported=True))
    checkpoints = [
        ('"scope_basis":"', REAL_SCOPES), ('"event_alignment":"', REAL_EVENTS),
        ('"authority_modality":"', REAL_MODALITIES), ('"candidate_modality":"', REAL_MODALITIES),
        ('"authority_timing":"', REAL_TIMINGS), ('"candidate_timing":"', REAL_TIMINGS),
    ]
    for marker, expected in checkpoints:
        prefix = real.split(marker, 1)[0] + marker
        state = StagePRoleCoherenceConstraintStateV2().feed(prefix)
        assert state.mode == "CHOICE" and state.choices == expected


def test_contained_creative_choices_are_singletons() -> None:
    raw = _raw(_entry("CONTAINED_CREATIVE"))
    expected = {
        '"scope_basis":"':("CREATIVE_CONTAINED",), '"event_alignment":"':("CREATIVE_VEHICLE_ONLY",),
        '"authority_modality":"':("NOT_APPLICABLE",), '"candidate_modality":"':("NOT_APPLICABLE",),
        '"authority_timing":"':("NOT_APPLICABLE",), '"candidate_timing":"':("NOT_APPLICABLE",),
    }
    for marker, choices in expected.items():
        state = StagePRoleCoherenceConstraintStateV2().feed(raw.split(marker, 1)[0] + marker)
        assert state.mode == "CHOICE" and state.choices == choices


def test_null_authority_forces_not_applicable_axes() -> None:
    raw = _raw(_entry("REAL_WORLD_COMMITMENT", supported=False))
    for marker in ('"authority_modality":"', '"authority_timing":"'):
        state = StagePRoleCoherenceConstraintStateV2().feed(raw.split(marker, 1)[0] + marker)
        assert state.choices == ("NOT_APPLICABLE",)


def test_unresolved_role_cannot_reach_group_without_an_unresolved_axis() -> None:
    entry = _entry("UNRESOLVED_SCOPE")
    entry.update(scope_basis="ASSERTED", event_alignment="GOVERNED_EVENT", candidate_modality="POSSIBLE", candidate_timing="PRESENT")
    raw = _raw(entry)
    prefix = raw.split('"candidate_timing":"', 1)[0] + '"candidate_timing":"'
    state = StagePRoleCoherenceConstraintStateV2().feed(prefix)
    assert state.choices == ("UNRESOLVED",)
    with pytest.raises(StagePRoleCoherenceConstraintViolationV1, match="ENUM_MISMATCH"):
        state.feed("PRESENT")

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_constraint_v1 import (
    StagePConstructionObligationConstraintStateV1,
)
from pastila_scout.semantic_admission_v2.stage_p_trie_projector_v1 import StagePTokenTrieProjectorV1


ROOT = Path(__file__).resolve().parents[1]


CANDIDATE = "Banii se ascund în umbră, iar hotelul cere transparență."


def _entry(entry_id: str, kind: str, *, host: str | None = None):
    creative = kind == "creative"; unresolved = kind == "unresolved"
    return {"entry_id": entry_id,
        "entry_type": "CONTAINED_CREATIVE" if creative else "UNRESOLVED_SCOPE" if unresolved else "REAL_WORLD_COMMITMENT",
        "candidate_span": CANDIDATE, "authority_support": None,
        "commitment": "Transformare editorială." if creative else "Relație ambiguă." if unresolved else "Propoziție literală.",
        "scope_basis": "CREATIVE_CONTAINED" if creative else "UNRESOLVED" if unresolved else "ASSERTED",
        "event_alignment": "CREATIVE_VEHICLE_ONLY" if creative else "UNRESOLVED" if unresolved else "NEW_UNSUPPORTED_EVENT",
        "authority_modality": "NOT_APPLICABLE",
        "candidate_modality": "NOT_APPLICABLE" if creative else "UNRESOLVED" if unresolved else "CERTAIN_OR_ACTUAL",
        "authority_timing": "NOT_APPLICABLE",
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


def _construction(role: str, host: str | None, links: list[str], construction_id: str = "C1"):
    resolutions = {"LITERAL_ONLY": "LITERAL_PATH_RETAINED",
        "MATERIAL_CREATIVE_OR_EDITORIAL": "CREATIVE_HOST_REQUIRED",
        "MIXED_CREATIVE_AND_REAL_WORLD": "MIXED_HOST_AND_RETURNS_REQUIRED",
        "NON_MATERIAL_RHETORICAL_COLOR": "RHETORICAL_COLOR_RETAINED",
        "UNRESOLVED": "FAIL_CLOSED_UNRESOLVED"}
    return {"construction_id": construction_id, "candidate_span": CANDIDATE,
        "construction_role": role, "role_basis": "Bază semantică specifică.",
        "creative_host_entry_id": host, "literal_or_return_entry_ids": links,
        "resolution": resolutions[role]}


def _value(*, records, entries, disposition="ONE_OR_MORE_MATERIAL_CONSTRUCTIONS",
           literal_basis=None, unresolved=False):
    audits = []
    for entry in entries:
        if entry["entry_type"] == "CONTAINED_CREATIVE":
            audits.append({"audit_id": f"T{len(audits)+1}", "creative_host_entry_id": entry["entry_id"],
                "vehicle_span": CANDIDATE, "semantic_target": "Transformare editorială.",
                "target_class": "NONFACTUAL_EDITORIAL_OR_CREATIVE",
                "survival_basis": "DOES_NOT_SURVIVE_AS_FACT", "proposition_entry_id": None,
                "resolution": "RETAINED_NONFACTUAL"})
    return {"stage_id": "PROPOSITION_LEDGER", "construction_role_audit": {
        "candidate_reviewed_as_construction": True, "overall_disposition": disposition,
        "construction_records": records, "literal_path_basis": literal_basis},
        "entries": entries, "creative_target_audits": audits,
        "coverage_receipt": _receipt(unresolved),
        "coverage_decision": "INDETERMINATE" if unresolved else "COMPLETE"}


def _raw(value): return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _feed(value):
    state = StagePConstructionObligationConstraintStateV1().feed(_raw(value))
    assert state.can_eos
    return state


def test_literal_path_and_mixed_host_return_are_both_valid():
    literal = _value(records=[_construction("LITERAL_ONLY", None, ["P1"])],
        entries=[_entry("P1", "literal")], disposition="NO_MATERIAL_CREATIVE_CONSTRUCTION",
        literal_basis="Sensul este literal.")
    mixed = _value(records=[_construction("MIXED_CREATIVE_AND_REAL_WORLD", "P1", ["P2"])],
        entries=[_entry("P1", "creative"), _entry("P2", "literal", host="P1")])
    _feed(literal); _feed(mixed)


def test_mixed_entries_may_arrive_return_before_host():
    value = _value(records=[_construction("MIXED_CREATIVE_AND_REAL_WORLD", "P1", ["P2"])],
        entries=[_entry("P2", "literal", host="P1"), _entry("P1", "creative")])
    _feed(value)


def test_repeated_case01_shape_is_impossible_at_entry_type_not_coverage():
    value = _value(records=[_construction("MIXED_CREATIVE_AND_REAL_WORLD", "P1", ["P2"])],
        entries=[_entry("P1", "literal"), _entry("P2", "literal")])
    raw = _raw(value); prefix = raw.split('"entry_type":"REAL_WORLD_COMMITMENT"', 1)[0] + '"entry_type":"'
    state = StagePConstructionObligationConstraintStateV1().feed(prefix)
    assert state.next_step == "CANDIDATE_LITERAL" and state.choices == ("CONTAINED_CREATIVE",)
    with pytest.raises(Exception): StagePConstructionObligationConstraintStateV1().feed(raw)


def test_committed_historical_failure_is_blocked_at_declared_host_entry_type():
    freeze = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-role-case01-receipt-v1-1-run-v1-freeze.json").read_text("utf-8"))
    relative = freeze["immutable_evidence"]["durable_lifecycle_relative_path"]
    heartbeat = (ROOT / ".semantic-admission-v2-stage-p-construction-role-case01-receipt-v1-1-run-v1-evidence" /
                 "durable-lifecycle" / relative / "runner-00070-generation-heartbeat.json")
    partial = json.loads(heartbeat.read_text("utf-8"))["partial_output"]
    prefix = partial.split('"entry_type":"REAL_WORLD_COMMITMENT"', 1)[0] + '"entry_type":"'
    state = StagePConstructionObligationConstraintStateV1().feed(prefix)
    assert state.current_entry_id == "P1"
    assert state.choices == ("CONTAINED_CREATIVE",)
    with pytest.raises(Exception):
        state.feed("R")


def test_candidate_binds_committed_failure_review_and_freeze_without_rewriting_them():
    artifact = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-projection-candidate-v1.json").read_text("utf-8"))
    review = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-role-case01-failure-and-receipt-mismatch-review-v1.json"
    freeze = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-role-case01-receipt-v1-1-run-v1-freeze.json"
    assert artifact["source_failure_review_identity"] == "730b2e3ac7a067a51852edbcc57ba2fe9810264a85e35b090395b1a2a4bcff9a"
    assert artifact["source_frozen_run_identity"] == "cdd5ad4c483582784c3aff8bea6a9ef4eaa547e79c1d99e30206dd3e12d6cff6"
    assert hashlib.sha256(review.read_bytes()).hexdigest() == "5f165a1ba13c79c9565214b9649aec3eb14ac17ad6b44966d02e83dbb2e8dea0"
    assert hashlib.sha256(freeze.read_bytes()).hexdigest() == "b639bf078b4269fe2d5fed2c0e07ec5141baadedf5197a3250499641bf1cb2cf"


def test_missing_required_return_cannot_close_entries():
    value = _value(records=[_construction("MIXED_CREATIVE_AND_REAL_WORLD", "P1", ["P2"])],
        entries=[_entry("P1", "creative")])
    with pytest.raises(Exception, match="REQUIRED_CONSTRUCTION_ENTRY_MISSING"):
        StagePConstructionObligationConstraintStateV1().feed(_raw(value))


def test_conflicting_host_and_return_obligation_fails_before_entries():
    records = [_construction("MATERIAL_CREATIVE_OR_EDITORIAL", "P1", [], "C1"),
               _construction("MIXED_CREATIVE_AND_REAL_WORLD", "P2", ["P1"], "C2")]
    value = _value(records=records, entries=[_entry("P1", "creative"), _entry("P2", "creative")])
    raw = _raw(value); boundary = raw.split('"entries":[', 1)[0] + '"entries":['
    with pytest.raises(Exception, match="ENTRY_ROLE_OBLIGATION_CONFLICT"):
        StagePConstructionObligationConstraintStateV1().feed(boundary)


def test_synthetic_trie_projects_valid_mixed_fixture_without_inference():
    value = _value(records=[_construction("MIXED_CREATIVE_AND_REAL_WORLD", "P1", ["P2"])],
        entries=[_entry("P1", "creative"), _entry("P2", "literal", host="P1")])
    raw = _raw(value); pieces = {i + 1: char for i, char in enumerate(sorted(set(raw)))}
    reverse = {char: token_id for token_id, char in pieces.items()}
    projector = StagePTokenTrieProjectorV1(token_pieces=pieces, eos_token_id=999999)
    state = StagePConstructionObligationConstraintStateV1()
    for char in raw:
        assert reverse[char] in projector.allowed_token_ids(state)
        state = state.feed(char)
    assert projector.allowed_token_ids(state) == (999999,)

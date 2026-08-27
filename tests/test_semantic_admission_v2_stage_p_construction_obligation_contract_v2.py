from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1, SourceRoleV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_contract_v2 import (
    ConstructionObligationLedgerV2, ProjectionStatusV1,
    build_source_projection_receipt_v1, canonical_projection_receipt_bytes_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json"


def _captured_sources():
    pack = json.loads(PACK.read_bytes())
    case = next(item for item in pack["cases"] if item["case_id"] == "HMCV1-SASC-01")
    candidate = ImmutableUtf8SourceV1.bind(
        role=SourceRoleV1.CANDIDATE, data=case["candidate"].encode("utf-8"))
    authority = ImmutableUtf8SourceV1.bind(
        role=SourceRoleV1.FACTUAL_AUTHORITY, data=case["factual_summary"].encode("utf-8"))
    assert candidate.sha256 == case["candidate_sha256"]
    assert authority.sha256 == case["factual_summary_sha256"]
    return candidate, authority


def _ref(source, start=0, end=None):
    return {
        "source_role": source.role.value, "source_sha256": source.sha256,
        "start_utf8": start, "end_utf8": len(source.data) if end is None else end,
    }


def _ledger_dict(*, bad_p1_hash=False):
    candidate, authority = _captured_sources()
    candidate_ref = _ref(candidate)
    bad_ref = {**candidate_ref, "source_sha256": "0" * 64} if bad_p1_hash else candidate_ref
    authority_ref = _ref(authority)
    receipt = {
        "candidate_reviewed_as_whole": True, "embedded_propositions_checked": True,
        "creative_scope_checked": True, "unresolved_scope_present": False,
        "overlapping_spans_reconciled": True, "integrated_creative_hosts_checked": True,
        "factual_return_tests_completed": True, "creative_targets_enumerated": True,
        "target_classes_reviewed": True, "target_to_ledger_reconciled": True,
        "construction_roles_reviewed": True, "construction_to_ledger_reconciled": True,
    }
    return {
        "schema_name": "pastila-semantic-admission-v2-stage-p-construction-obligation-ledger",
        "schema_version": "2.0.0-evaluation.1", "stage_id": "PROPOSITION_LEDGER",
        "construction_role_audit": {
            "candidate_reviewed_as_construction": True,
            "overall_disposition": "ONE_OR_MORE_MATERIAL_CONSTRUCTIONS",
            "construction_records": [{
                "construction_id": "C1", "candidate_span_ref": candidate_ref,
                "construction_role": "MIXED_CREATIVE_AND_REAL_WORLD",
                "role_basis": "The creative host carries a factual return.",
                "creative_host_entry_id": "P1", "literal_or_return_entry_ids": ["P2"],
                "resolution": "MIXED_HOST_AND_RETURNS_REQUIRED",
            }], "literal_path_basis": None,
        },
        "entries": [{
            "entry_id": "P1", "entry_type": "CONTAINED_CREATIVE",
            "candidate_span_ref": bad_ref, "authority_support_ref": None,
            "commitment": "Contained hotel/transparency imagery.",
            "scope_basis": "CREATIVE_CONTAINED", "event_alignment": "CREATIVE_VEHICLE_ONLY",
            "authority_modality": "NOT_APPLICABLE", "candidate_modality": "NOT_APPLICABLE",
            "authority_timing": "NOT_APPLICABLE", "candidate_timing": "NOT_APPLICABLE",
            "independence_group": "G1", "scope_relation": "CREATIVE_HOST",
            "creative_host_entry_id": None, "factual_return_basis": "NOT_APPLICABLE",
        }, {
            "entry_id": "P2", "entry_type": "REAL_WORLD_COMMITMENT",
            "candidate_span_ref": candidate_ref, "authority_support_ref": authority_ref,
            "commitment": "The employer paid salaries off the books.",
            "scope_basis": "NECESSARILY_IMPLIED", "event_alignment": "GOVERNED_EVENT",
            "authority_modality": "CERTAIN_OR_ACTUAL", "candidate_modality": "CERTAIN_OR_ACTUAL",
            "authority_timing": "PAST", "candidate_timing": "PAST",
            "independence_group": "G1", "scope_relation": "FACTUAL_RETURN_WITHIN_CREATIVE_HOST",
            "creative_host_entry_id": "P1", "factual_return_basis": "NECESSARY_IMPLICATION_SURVIVES",
        }],
        "creative_target_audits": [{
            "audit_id": "T1", "creative_host_entry_id": "P1",
            "vehicle_span_ref": candidate_ref,
            "semantic_target": "The governed off-book salary practice.",
            "target_class": "REAL_WORLD_PROPOSITION",
            "survival_basis": "NECESSARY_IMPLICATION_SURVIVES",
            "proposition_entry_id": "P2", "resolution": "RECONCILED_TO_LEDGER",
        }],
        "coverage_receipt": receipt, "coverage_decision": "COMPLETE",
    }


def _ledger(*, bad_p1_hash=False):
    return ConstructionObligationLedgerV2.model_validate(_ledger_dict(bad_p1_hash=bad_p1_hash),
                                                          strict=False)


def test_v2_is_breaking_and_rejects_v1_provenance_field_names():
    value = _ledger_dict()
    value["entries"][0]["candidate_span"] = "copied text"
    with pytest.raises(ValidationError):
        ConstructionObligationLedgerV2.model_validate(value, strict=False)


def test_raw_ledger_identity_fields_are_explicitly_required():
    for missing in ("schema_name", "schema_version"):
        value = _ledger_dict(); value.pop(missing)
        with pytest.raises(ValidationError):
            ConstructionObligationLedgerV2.model_validate(value, strict=False)
    required = ConstructionObligationLedgerV2.model_json_schema()["required"]
    assert "schema_name" in required and "schema_version" in required


def test_hand_constructed_case01_fixture_projects_all_five_references():
    candidate, authority = _captured_sources()
    ledger = _ledger()
    raw = json.dumps(ledger.model_dump(mode="json"), ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt = build_source_projection_receipt_v1(
        raw_response=raw, ledger=ledger, candidate_source=candidate,
        factual_authority_source=authority)
    assert receipt.projection_status is ProjectionStatusV1.PASS
    assert receipt.reason_code is None
    assert len(receipt.projection_records) == 5
    assert [item.json_pointer for item in receipt.projection_records] == sorted(
        item.json_pointer for item in receipt.projection_records)
    assert all(item.status is ProjectionStatusV1.PASS for item in receipt.projection_records)
    assert receipt.raw_response_sha256 == hashlib.sha256(raw).hexdigest()


def test_one_bad_reference_does_not_short_circuit_and_fails_whole_projection():
    candidate, authority = _captured_sources()
    ledger = _ledger(bad_p1_hash=True)
    receipt = build_source_projection_receipt_v1(
        raw_response=b"captured-fixture", ledger=ledger, candidate_source=candidate,
        factual_authority_source=authority)
    assert receipt.projection_status is ProjectionStatusV1.FAIL
    assert receipt.reason_code == "STAGE_P_SOURCE_REFERENCE_IDENTITY_DRIFT"
    assert len(receipt.projection_records) == 5
    assert sum(item.status is ProjectionStatusV1.FAIL for item in receipt.projection_records) == 1
    assert sum(item.status is ProjectionStatusV1.PASS for item in receipt.projection_records) == 4


def test_canonical_receipt_bytes_are_deterministic_and_contain_no_projected_text():
    candidate, authority = _captured_sources(); ledger = _ledger()
    first = build_source_projection_receipt_v1(
        raw_response=b"raw", ledger=ledger, candidate_source=candidate,
        factual_authority_source=authority)
    second = build_source_projection_receipt_v1(
        raw_response=b"raw", ledger=ledger, candidate_source=candidate,
        factual_authority_source=authority)
    assert canonical_projection_receipt_bytes_v1(first) == canonical_projection_receipt_bytes_v1(second)
    assert candidate.data not in canonical_projection_receipt_bytes_v1(first)
    assert authority.data not in canonical_projection_receipt_bytes_v1(first)


def test_builder_does_not_mutate_raw_or_sources():
    candidate, authority = _captured_sources(); ledger = _ledger()
    raw = bytearray(b"immutable raw fixture")
    before = bytes(raw), candidate.data, authority.data
    build_source_projection_receipt_v1(
        raw_response=raw, ledger=ledger, candidate_source=candidate,
        factual_authority_source=authority)
    assert (bytes(raw), candidate.data, authority.data) == before


def test_top_level_source_roles_are_preconditions():
    candidate, authority = _captured_sources(); ledger = _ledger()
    with pytest.raises(ValueError, match="CANDIDATE_SOURCE_ROLE_MISMATCH"):
        build_source_projection_receipt_v1(
            raw_response=b"raw", ledger=ledger, candidate_source=authority,
            factual_authority_source=authority)
    with pytest.raises(ValueError, match="FACTUAL_AUTHORITY_SOURCE_ROLE_MISMATCH"):
        build_source_projection_receipt_v1(
            raw_response=b"raw", ledger=ledger, candidate_source=candidate,
            factual_authority_source=candidate)

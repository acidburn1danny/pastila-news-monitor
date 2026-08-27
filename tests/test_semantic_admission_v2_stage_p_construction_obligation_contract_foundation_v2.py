from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    SourceRoleV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_contract_v2 import (
    ConstructionObligationLedgerV2,
    ProjectionStatusV1,
    SourceProjectionReceiptV1,
    canonical_projection_receipt_bytes_v1,
)


def _receipt() -> SourceProjectionReceiptV1:
    return SourceProjectionReceiptV1(
        raw_response_sha256="0" * 64,
        raw_response_bytes=10,
        candidate_source_sha256="1" * 64,
        candidate_source_bytes=20,
        factual_authority_source_sha256="2" * 64,
        factual_authority_source_bytes=30,
        reference_candidate_identity="3" * 64,
        projection_records=(
            {
                "json_pointer": "/entries/0/candidate_span_ref",
                "required_source_role": SourceRoleV1.CANDIDATE,
                "observed_source_role": SourceRoleV1.CANDIDATE,
                "source_sha256": "1" * 64,
                "start_utf8": 0,
                "end_utf8": 4,
                "projected_bytes": 4,
                "projected_sha256": "4" * 64,
                "status": ProjectionStatusV1.PASS,
                "reason_code": None,
            },
        ),
        projection_status=ProjectionStatusV1.PASS,
        reason_code=None,
    )


def test_ledger_schema_requires_explicit_versioned_identity() -> None:
    schema = ConstructionObligationLedgerV2.model_json_schema()
    assert schema == ConstructionObligationLedgerV2.model_json_schema()
    assert schema["additionalProperties"] is False
    assert {"schema_name", "schema_version", "stage_id"} <= set(schema["required"])


def test_empty_or_v1_shaped_ledger_fails_closed() -> None:
    with pytest.raises(ValidationError):
        ConstructionObligationLedgerV2.model_validate(
            {"stage_id": "PROPOSITION_LEDGER", "candidate_span": "legacy"},
            strict=False,
        )


def test_projection_receipt_bytes_are_canonical_and_deterministic() -> None:
    first = canonical_projection_receipt_bytes_v1(_receipt())
    second = canonical_projection_receipt_bytes_v1(_receipt())
    assert first == second and first.endswith(b"\n")
    decoded = json.loads(first)
    assert decoded["projection_status"] == "PASS"
    assert decoded["projection_records"][0]["json_pointer"] == (
        "/entries/0/candidate_span_ref"
    )


def test_projection_receipts_are_frozen() -> None:
    with pytest.raises(ValidationError):
        _receipt().raw_response_bytes = 11

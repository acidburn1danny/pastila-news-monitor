from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_phase2_audit_contracts_v1 import (
    AuthorityReconciliationAuditReceiptV1,
    AuthorityReconciliationAuditResponseV1,
    CommitmentSpanAuditReceiptV1,
    CommitmentSpanAuditResponseV1,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-phase2-audit-contracts-controller-builders-v1.json"


def _canonical_schema_hash(model: type) -> str:
    data = json.dumps(model.model_json_schema(), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def test_phase2_contract_candidate_identity_and_source() -> None:
    value = json.loads(ARTIFACT.read_text("utf-8"))
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == value["canonical_identity"]
    source = ROOT / value["implementation"]["path"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == value["implementation"]["sha256"]


def test_all_four_schema_identities_and_zero_authority() -> None:
    value = json.loads(ARTIFACT.read_text("utf-8"))
    schemas = value["schema_identities"]
    assert _canonical_schema_hash(CommitmentSpanAuditResponseV1) == schemas["commitment_response"]
    assert _canonical_schema_hash(CommitmentSpanAuditReceiptV1) == schemas["commitment_controller_receipt"]
    assert _canonical_schema_hash(AuthorityReconciliationAuditResponseV1) == schemas["authority_response"]
    assert _canonical_schema_hash(AuthorityReconciliationAuditReceiptV1) == schemas["authority_controller_receipt"]
    assert not any(value["authority"].values())
    assert value["verification"]["inference_calls"] == 0

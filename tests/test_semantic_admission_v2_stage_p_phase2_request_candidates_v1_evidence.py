from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_phase2_request_candidates_v1 import (
    AuthorityReconciliationAuditRequestEnvelopeV1,
    CommitmentSpanAuditRequestEnvelopeV1,
    Phase2AuditRequestCandidateV1,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-phase2-audit-contracts-controller-builders-v1-freeze.json"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-phase2-prompt-request-candidates-v1.json"


def _identity(value: dict[str, object]) -> None:
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == value["canonical_identity"]


def _schema_hash(model: type) -> str:
    data = json.dumps(model.model_json_schema(), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def test_contract_freeze_and_request_candidate_identities() -> None:
    freeze = json.loads(FREEZE.read_text("utf-8"))
    value = json.loads(ARTIFACT.read_text("utf-8"))
    _identity(freeze)
    _identity(value)
    assert freeze["status"] == "FROZEN"
    source = ROOT / value["implementation"]["path"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == value["implementation"]["sha256"]
    candidate = Phase2AuditRequestCandidateV1(project_root=ROOT)
    assert candidate.candidate_identity == value["request_candidate_identity_240_seconds"]


def test_envelope_schemas_and_zero_execution_authority() -> None:
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert _schema_hash(CommitmentSpanAuditRequestEnvelopeV1) == value["envelope_schema_identities"]["commitment_span"]
    assert _schema_hash(AuthorityReconciliationAuditRequestEnvelopeV1) == value["envelope_schema_identities"]["authority_reconciliation"]
    assert value["context_budget"]["exact_token_context_proof"].startswith("PENDING_")
    assert not any(value["authority"].values())
    assert value["verification"]["inference_calls"] == 0

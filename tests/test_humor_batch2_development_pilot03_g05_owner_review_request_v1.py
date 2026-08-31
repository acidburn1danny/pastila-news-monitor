from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_g05_request_requires_explicit_owner_decision_and_preserves_limits() -> None:
    value = load("humor-mechanics-batch2-development-pilot03-candidate01-g05-owner-review-request-v1.json")
    identity = value.pop("g05_owner_review_request_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT03_CANDIDATE01_G05_OWNER_REVIEW_REQUEST_V1", value)
    assert value["g05_verdict"] == "AWAITING_EXPLICIT_OWNER_DECISION"
    assert value["owner_decision"] is None
    assert value["owner_decision_recorded"] is False
    assert all(item is None for item in value["owner_must_explicitly_confirm_or_reject"].values())
    assert value["bound_gate_results"]["g03c_pool"] == "POOL_PENDING_INSUFFICIENT_INDEPENDENT_POSITIVE_FAMILIES"
    assert value["eligibility"]["partition"] == "DEVELOPMENT"
    assert value["eligibility"]["pool_certified"] is False
    assert value["candidate_bytes_modified"] is False
    assert not any(value["performed"].values())
    assert not any(value["authority_matrix"].values())


def test_g05_request_audit_is_sealed_and_does_not_infer_approval() -> None:
    value = load("humor-mechanics-batch2-development-pilot03-candidate01-g05-owner-review-request-audit-v1.json")
    identity = value.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT03_CANDIDATE01_G05_OWNER_REVIEW_REQUEST_AUDIT_V1", value)
    assert value["explicit_owner_decision_present"] is False
    assert value["authorization_treated_as_substantive_approval"] is False
    assert value["pool_pending_preserved"] is True
    assert value["development_only_preserved"] is True
    assert value["downstream_authority_granted"] is False
    assert value["verdict"] == "PASS_FAIL_CLOSED_AWAITING_EXPLICIT_OWNER_DECISION"

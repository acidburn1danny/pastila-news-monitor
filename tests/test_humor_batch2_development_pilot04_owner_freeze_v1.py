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


def test_owner_freeze_binds_exact_decision_and_preserves_pool_pending() -> None:
    value = load("humor-mechanics-batch2-development-pilot04-candidate01-g05-owner-freeze-v1.json")
    identity = value.pop("g05_owner_freeze_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT04_CANDIDATE01_G05_OWNER_FREEZE_V1", value)
    assert value["owner_decision"] == "APPROVE PILOT04 OWNER_FROZEN DEVELOPMENT_ONLY G04B_PENDING"
    assert value["status"] == "OWNER_FROZEN_DEVELOPMENT_ONLY_G04B_PENDING"
    assert value["g05_verdict"] == "OWNER_APPROVED"
    assert all(value["owner_confirmations"].values())
    assert value["eligibility"]["partition"] == "DEVELOPMENT"
    assert value["eligibility"]["pool_certified"] is False
    assert value["eligibility"]["curriculum_eligible"] is False
    assert value["candidate_bytes_modified"] is False
    assert not any(value["authority_matrix"].values())


def test_owner_freeze_audit_is_sealed_and_grants_no_downstream_authority() -> None:
    value = load("humor-mechanics-batch2-development-pilot04-candidate01-g05-owner-freeze-audit-v1.json")
    identity = value.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT04_CANDIDATE01_G05_OWNER_FREEZE_AUDIT_V1", value)
    assert value["exact_owner_decision_bound"] is True
    assert value["development_only_preserved"] is True
    assert value["g04b_pending_preserved"] is True
    assert value["downstream_authority_granted"] is False
    assert value["verdict"] == "PASS_OWNER_FREEZE_WITH_FAIL_CLOSED_DOWNSTREAM_LIMITS"

"""Verify frozen Pilot 05 G01A/G01B admission artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot05_g01a_g01b_receipts_are_sealed_and_non_authorizing() -> None:
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot05-g01a-g01b-admission-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot05-g01a-g01b-admission-v1-audit.json").read_text(encoding="utf-8"))
    core = dict(receipt)
    identity = core.pop("admission_identity")
    assert seal("B2_DEVELOPMENT_PILOT05_G01A_G01B_ADMISSION_V1", core) == identity
    assert receipt["g01a"]["verdict"] == "PASS"
    assert receipt["g01b"]["verdict"] == "PASS"
    assert len(receipt["g01a"]["propositions"]) == 7
    assert receipt["g01b"]["creative_premise_family_id"] == "UNASSIGNED"
    assert receipt["post_g01_rebalancing_assignment_gate"] == "NOT_PERFORMED_SEPARATELY_AUTHORIZED_ONLY"
    assert receipt["eligibility_scope"] == "SEPARATE_OWNER_AUTHORIZATION_REQUIRED_POST_G01_REBALANCING_GATE_NOT_PERFORMED"
    assert all(value is False for value in receipt["authority_matrix"].values())
    audit_core = dict(audit)
    audit_identity = audit_core.pop("audit_identity")
    assert seal("B2_DEVELOPMENT_PILOT05_G01A_G01B_ADMISSION_AUDIT_V1", audit_core) == audit_identity
    assert audit["git_object_source_verification"] == "PASS"
    assert audit["span_coordinate_hash_verification"] == "PASS_7_PROPOSITIONS"
    assert audit["deterministic_blockers"] == []

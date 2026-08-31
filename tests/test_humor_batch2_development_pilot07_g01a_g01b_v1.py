"""Verify frozen Pilot 07 G01A/G01B admission artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot07_g01a_g01b_are_sealed_and_sufficiency_is_deferred() -> None:
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot07-g01a-g01b-admission-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot07-g01a-g01b-admission-v1-audit.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("admission_identity")
    assert seal("B2_DEVELOPMENT_PILOT07_G01A_G01B_ADMISSION_V1", core) == identity
    assert receipt["g01a"]["verdict"] == receipt["g01b"]["verdict"] == "PASS"
    assert len(receipt["g01a"]["propositions"]) == 6
    assert receipt["g01b"]["creative_premise_family_id"] == "UNASSIGNED"
    assert receipt["proposition_sufficiency_evaluated"] is False
    assert receipt["eligibility"].endswith("PROPOSITION_SUFFICIENCY_GATE_ONLY")
    assert all(value is False for value in receipt["authority_matrix"].values())
    core = dict(audit); identity = core.pop("audit_identity")
    assert seal("B2_DEVELOPMENT_PILOT07_G01A_G01B_ADMISSION_AUDIT_V1", core) == identity
    assert audit["span_coordinate_hash_verification"] == "PASS_6_PROPOSITIONS"
    assert audit["proposition_sufficiency_evaluated"] is False and audit["deterministic_blockers"] == []

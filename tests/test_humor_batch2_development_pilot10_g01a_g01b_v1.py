"""Verify the Pilot 10 G01A/G01B admission seals and authority boundary."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot10_g01_admission_is_sealed_and_non_authorizing():
    admission = json.loads((ART / "humor-mechanics-batch2-development-pilot10-g01a-g01b-admission-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot10-g01a-g01b-admission-v1-audit.json").read_text(encoding="utf-8"))
    core = dict(admission); identity = core.pop("admission_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_G01A_G01B_ADMISSION_V1", core)
    core = dict(audit); audit_identity = core.pop("audit_identity")
    assert audit_identity == seal("B2_DEVELOPMENT_PILOT10_G01A_G01B_ADMISSION_AUDIT_V1", core)
    assert admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS"
    assert len(admission["g01a"]["propositions"]) == 7
    assert admission["g01b"]["creative_premise_family_id"] == "UNASSIGNED"
    assert admission["g01b"]["partition"] == "DEVELOPMENT"
    assert admission["proposition_sufficiency_evaluated"] is False
    assert admission["constructor_v5_2_compatibility_evaluated"] is False
    assert all(value is False for value in admission["authority_matrix"].values())
    assert audit["deterministic_blockers"] == []

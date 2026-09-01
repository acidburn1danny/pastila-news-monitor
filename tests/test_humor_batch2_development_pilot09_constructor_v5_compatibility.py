import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot09_v5_compatibility_fails_closed_without_release_or_surface():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot09-constructor-v5-source-compatibility-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot09-constructor-v5-source-compatibility-audit-v1.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("compatibility_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_V5_SOURCE_COMPATIBILITY_V1", core)
    core = dict(audit); identity = core.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_V5_SOURCE_COMPATIBILITY_AUDIT_V1", core)
    assert receipt["verdict"] == "FAIL_FROZEN_V5_SOURCE_INCOMPATIBLE_NO_RELEASE"
    assert len(receipt["deterministic_blockers"]) == 2
    assert receipt["constructor_invoked"] is False and receipt["candidate_surface"] is None
    assert receipt["constructor_release"] is False and all(value is False for value in receipt["authority_matrix"].values())
    assert audit["verdict"] == "PASS_FAIL_CLOSED_ZERO_CONSTRUCTION_NO_RELEASE"

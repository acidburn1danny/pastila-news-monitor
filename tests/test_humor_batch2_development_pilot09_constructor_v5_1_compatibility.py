import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot09_v5_1_compatibility_is_sealed_and_non_authorizing():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot09-constructor-v5-1-source-compatibility-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot09-constructor-v5-1-source-compatibility-audit-v1.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("compatibility_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_V5_1_SOURCE_COMPATIBILITY_V1", core)
    core = dict(audit); identity = core.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_V5_1_SOURCE_COMPATIBILITY_AUDIT_V1", core)
    assert receipt["verdict"] == "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_1_NO_RELEASE"
    assert receipt["selected_proposition_id"] == "P5" and len(receipt["proposition_derived_abstract_plan"]) == 3
    assert receipt["constructor_invoked"] is False and receipt["candidate_surface"] is None
    assert receipt["constructor_release"] is False and all(value is False for value in receipt["authority_matrix"].values())
    assert audit["deterministic_blockers"] == [] and audit["candidate_surfaces_created"] == 0

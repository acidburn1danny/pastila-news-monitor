import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_postqualification_revalidation_artifacts_are_sealed_and_nonconsuming():
    schema = json.loads((ART / "humor-mechanics-batch2-development-pilot13-v5-3-3-release-hydration-schema.json").read_text(encoding="utf-8"))
    result = json.loads((ART / "humor-mechanics-batch2-development-pilot13-v5-3-3-postqualification-revalidation.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot13-v5-3-3-postqualification-revalidation-audit.json").read_text(encoding="utf-8"))
    core = dict(schema); identity = core.pop("schema_identity")
    assert identity == seal("B2_PILOT13_V5_3_3_RELEASE_HYDRATION_SCHEMA", core)
    core = dict(result); identity = core.pop("requalification_identity")
    assert identity == seal("B2_PILOT13_V5_3_3_POSTQUALIFICATION_REVALIDATION", core)
    core = dict(audit); identity = core.pop("audit_identity")
    assert identity == seal("B2_PILOT13_V5_3_3_POSTQUALIFICATION_REVALIDATION_AUDIT", core)
    assert result["PILOT13_INFRASTRUCTURE_READINESS_VERDICT"] == "PILOT13_READY_FOR_ONE_SHOT_CONSTRUCTION"
    assert result["pilot13_capability_state"] == "UNCONSUMED_0_OF_1_NOT_AUTHORIZED"
    assert result["actual_pilot13_invocations"] == "0/0/0"
    assert audit["pilot13_release_or_capability_exercised"] is False

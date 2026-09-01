import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot13_g01_admission_is_sealed_and_non_authorizing() -> None:
    admission = json.loads((ART / "humor-mechanics-batch2-development-pilot13-g01a-g01b-admission-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot13-g01a-g01b-admission-v1-audit.json").read_text(encoding="utf-8"))
    core = dict(admission); identity = core.pop("admission_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_G01A_G01B_ADMISSION_V1", core)
    core = dict(audit); audit_identity = core.pop("audit_identity")
    assert audit_identity == seal("B2_DEVELOPMENT_PILOT13_G01A_G01B_ADMISSION_AUDIT_V1", core)
    assert admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS"
    assert admission["g01a"]["source_git_object"] == "e3631174edc2adb56b1f28b803eafb9ceba487ff"
    assert len(admission["g01a"]["propositions"]) == 8
    assert admission["g01a"]["proposition_binding_state"] == "PASS_8_NOT_SELECTED"
    assert admission["g01a"]["rights_and_permitted_use"] == "PASS_WITH_STRICT_NON_INHERITANCE"
    assert admission["g01b"]["partition"] == "DEVELOPMENT"
    assert admission["g01b"]["partition_isolation"] == "PASS"
    assert admission["g01b"]["contamination_state"] == "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE"
    assert admission["proposition_sufficiency_evaluated"] is False
    assert admission["proposition_selected"] is False
    assert all(value is False for value in admission["authority_matrix"].values())
    assert audit["deterministic_blockers"] == []

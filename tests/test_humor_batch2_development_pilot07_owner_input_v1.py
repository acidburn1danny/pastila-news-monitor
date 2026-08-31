import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot07_owner_input_package_is_content_free_and_non_authorizing():
    base = ROOT / "docs/artifacts"
    template = json.loads((base / "humor-mechanics-batch2-development-pilot07-owner-declaration-template-v1.json").read_text(encoding="utf-8"))
    request = json.loads((base / "humor-mechanics-batch2-development-pilot07-owner-input-request-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((base / "humor-mechanics-batch2-development-pilot07-owner-input-request-audit-v1.json").read_text(encoding="utf-8"))
    tcore = dict(template); tid = tcore.pop("template_identity")
    assert tid == seal("B2_DEVELOPMENT_PILOT07_OWNER_DECLARATION_TEMPLATE_V1", tcore)
    rcore = dict(request); rid = rcore.pop("owner_input_request_identity")
    assert rid == seal("B2_DEVELOPMENT_PILOT07_OWNER_INPUT_REQUEST_V1", rcore)
    acore = dict(audit); aid = acore.pop("audit_identity")
    assert aid == seal("B2_DEVELOPMENT_PILOT07_OWNER_INPUT_REQUEST_AUDIT_V1", acore)
    assert request["content_accessed"] is False and request["source_family_created"] is False
    assert set(request["unassigned"].values()) == {"UNASSIGNED"}
    assert all(value is False for value in request["authority_matrix"].values())
    assert audit["audit_verdict"] == "PASS_CONTENT_FREE_STOP_REQUIRED"

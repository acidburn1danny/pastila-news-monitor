import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot10_owner_input_package_is_sealed_content_free_and_non_authorizing():
    template = json.loads((ART / "humor-mechanics-batch2-development-pilot10-owner-declaration-template-v1.json").read_text(encoding="utf-8"))
    request = json.loads((ART / "humor-mechanics-batch2-development-pilot10-owner-input-request-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot10-owner-input-request-audit-v1.json").read_text(encoding="utf-8"))
    core = dict(template); identity = core.pop("template_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_OWNER_DECLARATION_TEMPLATE_V1", core)
    core = dict(request); identity = core.pop("owner_input_request_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_OWNER_INPUT_REQUEST_V1", core)
    core = dict(audit); identity = core.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_OWNER_INPUT_REQUEST_AUDIT_V1", core)
    assert request["status"] == "BLOCKED_AWAITING_OWNER_INPUT"
    assert request["content_accessed"] is False and request["source_family_created"] is False
    assert request["unassigned"]["realization_plan"] == "UNASSIGNED"
    assert request["unassigned"]["witness_topology"] == "UNASSIGNED"
    assert all(value is False for value in request["authority_matrix"].values())
    assert audit["content_free"] is True
    assert audit["audit_verdict"] == "PASS_CONTENT_FREE_STOP_REQUIRED"

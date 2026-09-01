"""Verify content-free Pilot 09 owner-input preparation under Governance V5."""

import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot09_owner_package_is_content_free_and_non_authorizing():
    template = json.loads((ART / "humor-mechanics-batch2-development-pilot09-owner-declaration-template-v1.json").read_text(encoding="utf-8"))
    request = json.loads((ART / "humor-mechanics-batch2-development-pilot09-owner-input-request-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot09-owner-input-request-audit-v1.json").read_text(encoding="utf-8"))
    core = dict(template)
    identity = core.pop("template_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_OWNER_DECLARATION_TEMPLATE_V1", core)
    core = dict(request)
    identity = core.pop("owner_input_request_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_OWNER_INPUT_REQUEST_V1", core)
    core = dict(audit)
    identity = core.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_OWNER_INPUT_REQUEST_AUDIT_V1", core)
    assert request["status"] == "BLOCKED_AWAITING_OWNER_INPUT"
    assert request["content_accessed"] is False and request["source_family_created"] is False
    assert request["constructor_implementation_identity"] == "caf85ada6fcd296d3798b5d47838d7b8a39d029dac5f6ecae68ace58712b9d61"
    assert request["post_g01_boundary"]["constructor_source_compatibility_status"] == "NOT_PERFORMED"
    assert all(value == "UNASSIGNED" or value.endswith("PENDING_OWNER_BYTES") for value in request["unassigned"].values())
    assert all(value is False for value in request["authority_matrix"].values())
    assert audit["audit_verdict"] == "PASS_CONTENT_FREE_STOP_REQUIRED"
    assert audit["constructor_v5_identity_bound_but_not_released_or_invoked"] is True

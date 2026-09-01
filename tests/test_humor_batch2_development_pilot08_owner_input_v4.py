from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_pilot08_owner_package_is_content_free_v4_and_non_authorizing() -> None:
    cases = [
        ("humor-mechanics-batch2-development-pilot08-owner-declaration-template-v1.json", "template_identity", "B2_DEVELOPMENT_PILOT08_OWNER_DECLARATION_TEMPLATE_V1"),
        ("humor-mechanics-batch2-development-pilot08-owner-input-request-v1.json", "owner_input_request_identity", "B2_DEVELOPMENT_PILOT08_OWNER_INPUT_REQUEST_V1"),
        ("humor-mechanics-batch2-development-pilot08-owner-input-request-audit-v1.json", "audit_identity", "B2_DEVELOPMENT_PILOT08_OWNER_INPUT_REQUEST_AUDIT_V1"),
    ]
    values = {}
    for name, field, namespace in cases:
        value = json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))
        core = dict(value)
        identity = core.pop(field)
        assert identity == seal(namespace, core)
        values[name] = value

    request = values[cases[1][0]]
    assert request["status"] == "BLOCKED_AWAITING_OWNER_INPUT"
    assert request["preparation_verdict"] == "PASS_CONTENT_FREE_METADATA_FIRST_OWNER_PACKAGE_GOVERNANCE_V4"
    assert request["content_accessed"] is False
    assert request["source_family_created"] is False
    assert request["blind_material_accessed"] is False
    assert request["constructor_v1_preservation"] == "BYTE_EXACT_HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_RELEASE"
    assert request["post_g01_boundary"]["constructor_implementation_status"] == "NOT_PREPARED_V1_PROHIBITED_FOR_FUTURE_RELEASE"
    assert all(value is False for value in request["authority_matrix"].values())

    audit = values[cases[2][0]]
    assert audit["audit_verdict"] == "PASS_CONTENT_FREE_STOP_REQUIRED"
    assert audit["deterministic_blockers"] == []
    assert audit["constructor_implementation_or_release_performed"] is False
    assert audit["source_selection_uses_downstream_governance_target_or_marker"] is False

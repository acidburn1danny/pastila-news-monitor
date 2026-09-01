import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot11_owner_input_preparation_is_content_free_and_non_authorizing() -> None:
    items = [
        ("humor-mechanics-batch2-development-pilot11-owner-declaration-template-v1.json", "template_identity", "B2_DEVELOPMENT_PILOT11_OWNER_DECLARATION_TEMPLATE_V1"),
        ("humor-mechanics-batch2-development-pilot11-owner-input-request-v1.json", "owner_input_request_identity", "B2_DEVELOPMENT_PILOT11_OWNER_INPUT_REQUEST_V1"),
        ("humor-mechanics-batch2-development-pilot11-owner-input-request-audit-v1.json", "audit_identity", "B2_DEVELOPMENT_PILOT11_OWNER_INPUT_REQUEST_AUDIT_V1"),
    ]
    loaded = []
    for filename, field, namespace in items:
        artifact = json.loads((ART / filename).read_text(encoding="utf-8"))
        loaded.append(artifact)
        core = dict(artifact)
        identity = core.pop(field)
        assert identity == seal(namespace, core)
    request, audit = loaded[1], loaded[2]
    assert request["content_accessed"] is False
    assert request["source_family_created"] is False
    assert all(value is False for value in request["authority_matrix"].values())
    assert all(value == "UNASSIGNED" for value in request["unassigned"].values())
    assert "SEMANTIC_ROLE_SIGNATURE_OR_AFFORDANCE_TOPOLOGY" in request["source_content_requirements"]["prohibited_shaping"]
    assert audit["frozen_v5_3_identities_bound_but_not_released_or_invoked"] is True
    assert audit["release_authority"] is False

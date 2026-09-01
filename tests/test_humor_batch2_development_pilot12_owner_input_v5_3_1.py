import hashlib
import json
from pathlib import Path


ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot12_owner_input_preparation_is_content_free_and_non_authorizing():
    items = [
        ("humor-mechanics-batch2-development-pilot12-owner-declaration-template-v1.json", "template_identity", "B2_DEVELOPMENT_PILOT12_OWNER_DECLARATION_TEMPLATE_V1"),
        ("humor-mechanics-batch2-development-pilot12-owner-input-request-v1.json", "owner_input_request_identity", "B2_DEVELOPMENT_PILOT12_OWNER_INPUT_REQUEST_V1"),
        ("humor-mechanics-batch2-development-pilot12-owner-input-request-audit-v1.json", "audit_identity", "B2_DEVELOPMENT_PILOT12_OWNER_INPUT_REQUEST_AUDIT_V1"),
    ]
    loaded = []
    for filename, field, namespace in items:
        value = json.loads((ART / filename).read_text(encoding="utf-8")); loaded.append(value)
        core = dict(value); identity = core.pop(field)
        assert identity == seal(namespace, core)
    template, request, audit = loaded
    assert request["content_accessed"] is False and request["source_family_created"] is False
    assert all(value is False for value in request["authority_matrix"].values())
    assert all(value == "UNASSIGNED" for value in request["unassigned"].values())
    assert "MORPHOLOGICAL_ALIGNMENT_OPPORTUNITY" in request["source_content_requirements"]["prohibited_shaping"]
    assert "pilots_01_02_03_04_05_06_07_08_09_10_11" in " ".join(template["source_status_declarations"])
    assert audit["frozen_v5_3_1_identities_bound_but_not_released_or_invoked"] is True
    assert audit["constructor_provider_emitter_invocations"] == "0/0/0"
    assert audit["candidate_surfaces"] == 0 and audit["release_authority"] is False

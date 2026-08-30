from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_request_is_content_free_governance_v2_bound_and_unassigned() -> None:
    value = load("humor-mechanics-batch2-development-pilot03-owner-input-request-v1.json")
    identity = value.pop("owner_input_request_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT03_OWNER_INPUT_REQUEST_V1", value)
    assert value["preparation_verdict"] == "PASS_CONTENT_FREE_METADATA_FIRST_OWNER_PACKAGE"
    assert value["status"] == "BLOCKED_AWAITING_OWNER_INPUT"
    assert value["content_accessed"] is False and value["source_family_created"] is False
    assert value["governance_v2"]["obligation_governance_identity"] == "874c5d611c5ab955e0f9d82aa5aa086fad98e065f66e20e9e236f48798287024"
    assert value["unassigned"] == {
        "target_mechanism": True,
        "operational_obligation": True,
        "creative_premise_family_id": "UNASSIGNED",
    }
    assert not any(value["authority_matrix"].values())


def test_owner_template_requires_independent_owner_choices_and_both_pilot_freshness_declarations() -> None:
    value = load("humor-mechanics-batch2-development-pilot03-owner-declaration-template-v1.json")
    identity = value.pop("template_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT03_OWNER_DECLARATION_TEMPLATE_V1", value)
    assert value["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-03"
    for grant in value["independent_grants"].values():
        assert grant == "OWNER_MUST_CHOOSE_BOOLEAN_INDEPENDENTLY"
    status = value["source_status_declarations"]
    assert "source_has_no_pilot01_revision_sibling_same_event_or_syndication_relationship" in status
    assert "source_has_no_pilot02_revision_sibling_same_event_or_syndication_relationship" in status
    assert all(item.startswith("OWNER_MUST_") for item in status.values())


def test_source_selection_is_mechanism_neutral_and_audit_stops_before_acquisition() -> None:
    request = load("humor-mechanics-batch2-development-pilot03-owner-input-request-v1.json")
    requirements = request["source_content_requirements"]
    encoded = json.dumps(requirements, sort_keys=True).lower()
    assert "absurd_logical_extension" not in encoded
    assert "m13" not in encoded
    assert "TARGET_FRIENDLY_TOPIC_GRAMMAR_PROPOSITION_TOPOLOGY_OR_SHAPE" in requirements["selection_must_not_use"]

    audit = load("humor-mechanics-batch2-development-pilot03-owner-input-request-audit-v1.json")
    identity = audit.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT03_OWNER_INPUT_REQUEST_AUDIT_V1", audit)
    assert audit["audit_verdict"] == "PASS_CONTENT_FREE_STOP_REQUIRED"
    assert audit["deterministic_blockers"] == []
    assert audit["external_input_blocker"] == "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED"
    assert all(audit["checks"].values())

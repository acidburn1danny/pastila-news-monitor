from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_request_is_content_free_and_all_authorities_are_false() -> None:
    request = load("humor-mechanics-batch2-development-pilot02-owner-input-request-v1.json")
    core = {k: v for k, v in request.items() if k != "owner_input_request_identity"}
    expected = hashlib.sha256(canonical({"namespace": "B2_DEVELOPMENT_PILOT02_OWNER_INPUT_REQUEST_V1", "value": core})).hexdigest()
    assert request["owner_input_request_identity"] == expected
    assert request["status"] == "BLOCKED_AWAITING_OWNER_INPUT"
    assert not request["content_accessed"] and not request["source_family_created"]
    assert all(value is False for value in request["authority_matrix"].values())
    assert request["unassigned"] == {"target_mechanism": True, "operational_obligation": True, "creative_premise_family_id": "UNASSIGNED"}


def test_template_requires_owner_choice_for_substantive_declarations() -> None:
    template = load("humor-mechanics-batch2-development-pilot02-owner-declaration-template-v1.json")
    identity = template.pop("template_identity")
    assert identity == hashlib.sha256(canonical({"namespace": "B2_DEVELOPMENT_PILOT02_OWNER_DECLARATION_TEMPLATE_V1", "value": template})).hexdigest()
    for section in ("contributor", "ownership_declarations", "independent_grants", "rights_terms", "source_status_declarations", "owner_instruction", "owner_confirmation"):
        for key, value in template[section].items():
            if section == "owner_instruction" and key == "requested_action":
                assert value == "OWNER_MUST_CHOOSE_PREINGESTION_VALIDATION_ONLY"
            else:
                assert isinstance(value, str) and value.startswith("OWNER_MUST_"), (section, key, value)


def test_no_target_or_obligation_is_used_to_shape_owner_source() -> None:
    request = load("humor-mechanics-batch2-development-pilot02-owner-input-request-v1.json")
    source_requirements = canonical(request["source_content_requirements"]).lower()
    assert b"absurd_logical_extension" not in source_requirements
    assert b"m13" not in source_requirements
    assert "SUCCESSOR_OBLIGATION" in request["source_content_requirements"]["selection_must_not_use"]
    assert "TARGET_FRIENDLY_TOPIC_GRAMMAR_TOPOLOGY_OR_SHAPE" in request["source_content_requirements"]["selection_must_not_use"]


def test_audit_is_sealed_and_stops_before_g01() -> None:
    audit = load("humor-mechanics-batch2-development-pilot02-owner-input-request-audit-v1.json")
    core = {k: v for k, v in audit.items() if k != "audit_identity"}
    expected = hashlib.sha256(canonical({"namespace": "B2_DEVELOPMENT_PILOT02_OWNER_INPUT_REQUEST_AUDIT_V1", "value": core})).hexdigest()
    assert audit["audit_identity"] == expected
    assert audit["verdict"] == "PASS_CONTENT_FREE_STOP_REQUIRED"
    assert audit["blocker"] == "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED"
    assert all(audit["checks"].values())

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def seal(namespace: str, value: dict) -> str:
    return hashlib.sha256(json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def test_pilot05_request_is_content_free_independent_and_fail_closed() -> None:
    value = load("humor-mechanics-batch2-development-pilot05-owner-input-request-v1.json")
    identity = value.pop("owner_input_request_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT05_OWNER_INPUT_REQUEST_V1", value)
    assert value["status"] == "BLOCKED_AWAITING_OWNER_INPUT"
    assert value["content_accessed"] is False and value["source_family_created"] is False
    assert value["pool_status_preserved"] == "POOL_REBALANCING_REQUIRED_NO_CERTIFICATION"
    assert value["post_g01_rebalancing_gate"]["different_label_blind_realization_obligation_family_required"] is True
    assert value["post_g01_rebalancing_gate"]["different_close_alternative_profile_required"] is True
    assert value["post_g01_rebalancing_gate"]["must_not_influence_source_selection_or_wording"] is True
    assert value["unassigned"] == {"target_mechanism": True, "operational_obligation": True, "creative_premise_family_id": "UNASSIGNED"}
    assert value["g04b_pool_certification_performed"] is False
    assert not any(value["authority_matrix"].values())


def test_pilot05_template_requires_owner_choices_and_prior_pilot_independence() -> None:
    value = load("humor-mechanics-batch2-development-pilot05-owner-declaration-template-v1.json")
    identity = value.pop("template_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT05_OWNER_DECLARATION_TEMPLATE_V1", value)
    assert value["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-05"
    assert all(item == "OWNER_MUST_CHOOSE_BOOLEAN_INDEPENDENTLY" for item in value["independent_grants"].values())
    assert "pilots_01_02_03_04_04" in " ".join(value["source_status_declarations"]).lower()


def test_pilot05_audit_stops_for_owner_input_without_g04b() -> None:
    value = load("humor-mechanics-batch2-development-pilot05-owner-input-request-audit-v1.json")
    identity = value.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT05_OWNER_INPUT_REQUEST_AUDIT_V1", value)
    assert value["audit_verdict"] == "PASS_CONTENT_FREE_STOP_REQUIRED"
    assert value["external_input_blocker"] == "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED"
    assert value["g04b_performed"] is False
    assert value["blind_material_accessed"] is False
    assert value["rebalancing_requirement_deferred_until_post_g01"] is True
    assert value["source_selection_uses_rebalancing_target"] is False

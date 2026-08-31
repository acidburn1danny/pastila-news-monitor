"""Verify content-free Pilot 06 metadata-first preparation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def seal(namespace: str, value: Any) -> str:
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot06_request_is_content_free_ordered_and_non_authorizing() -> None:
    request = json.loads((ART / "humor-mechanics-batch2-development-pilot06-owner-input-request-v1.json").read_text(encoding="utf-8"))
    core = dict(request); identity = core.pop("owner_input_request_identity")
    assert seal("B2_DEVELOPMENT_PILOT06_OWNER_INPUT_REQUEST_V1", core) == identity
    assert request["status"] == "BLOCKED_AWAITING_OWNER_INPUT"
    assert request["content_accessed"] is False and request["source_family_created"] is False
    order = request["mandatory_phase_order"]
    assert order.index("G01B") < order.index("SEPARATELY_AUTHORIZED_PROPOSITION_SUFFICIENCY_GATE") < order.index("SEPARATELY_AUTHORIZED_ASSIGNMENT_DESIGN")
    assert request["proposition_sufficiency_boundary"]["current_status"] == "NOT_PERFORMED"
    assert request["unassigned"] == {"selected_proposition": "UNASSIGNED", "target_mechanism": "UNASSIGNED", "operational_obligation": "UNASSIGNED", "creative_premise_family_id": "UNASSIGNED"}
    assert not any(request["authority_matrix"].values())


def test_pilot06_template_and_audit_preserve_owner_choice_and_stop() -> None:
    template = json.loads((ART / "humor-mechanics-batch2-development-pilot06-owner-declaration-template-v1.json").read_text(encoding="utf-8"))
    core = dict(template); identity = core.pop("template_identity")
    assert seal("B2_DEVELOPMENT_PILOT06_OWNER_DECLARATION_TEMPLATE_V1", core) == identity
    assert all(value == "OWNER_MUST_CHOOSE_BOOLEAN_INDEPENDENTLY" for value in template["independent_grants"].values())
    assert all("01_02_03_04_05" in key for key in template["source_status_declarations"] if "pilots_" in key)
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot06-owner-input-request-audit-v1.json").read_text(encoding="utf-8"))
    core = dict(audit); identity = core.pop("audit_identity")
    assert seal("B2_DEVELOPMENT_PILOT06_OWNER_INPUT_REQUEST_AUDIT_V1", core) == identity
    assert audit["audit_verdict"] == "PASS_CONTENT_FREE_STOP_REQUIRED"
    assert audit["proposition_sufficiency_performed"] is False
    assert audit["external_input_blocker"] == "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED"

"""Verify the frozen zero-construction Pilot 02 assignment design."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot02_assignment_is_sealed_label_blind_and_zero_construction() -> None:
    mapping = json.loads((ART / "humor-mechanics-batch2-development-pilot02-sealed-assignment-mapping-v1.json").read_text(encoding="utf-8"))
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot02-constructor-facing-assignment-proposal-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot02-assignment-design-leakage-audit-v1.json").read_text(encoding="utf-8"))
    governance = json.loads((ART / "humor-mechanics-batch2-successor-obligation-governance-v1.json").read_text(encoding="utf-8"))

    mapping_core = dict(mapping)
    mapping_identity = mapping_core.pop("sealed_assignment_identity")
    assert seal("B2_DEVELOPMENT_PILOT02_SEALED_ASSIGNMENT_V1", mapping_core) == mapping_identity
    packet_core = dict(packet)
    packet_identity = packet_core.pop("constructor_facing_packet_identity")
    assert seal("B2_DEVELOPMENT_PILOT02_CONSTRUCTOR_PACKET_V1", packet_core) == packet_identity
    audit_core = dict(audit)
    audit_identity = audit_core.pop("audit_identity")
    assert seal("B2_DEVELOPMENT_PILOT02_ASSIGNMENT_DESIGN_AUDIT_V1", audit_core) == audit_identity

    visible = packet["unlabeled_operational_obligation"]
    instance = visible.pop("obligation_instance_identity")
    assert len(instance) == 64
    assert visible == governance["constructor_visible_obligation"]
    forbidden = ("ABSURD_LOGICAL_EXTENSION", "Absurd Logical Extension", "HMCV1-B02-M03", "M13", "conformance_schema", "removal_test")
    packet_text = canonical(packet).decode("utf-8")
    assert all(token.lower() not in packet_text.lower() for token in forbidden)
    assert packet["candidate_surface"] is None
    assert packet["creative_premise_family_id"] == "UNASSIGNED"
    assert all(value is False for value in packet["authority_matrix"].values())
    assert audit["verdict"] == "PASS_ZERO_CONSTRUCTION"
    assert audit["deterministic_blockers"] == []

"""Verify Pilot 03 Governance V2 assignment-design artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot03_assignment_is_label_blind_source_bound_and_non_authorizing() -> None:
    mapping = json.loads((ART / "humor-mechanics-batch2-development-pilot03-sealed-assignment-mapping-v1.json").read_text(encoding="utf-8"))
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot03-constructor-facing-assignment-proposal-v1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot03-assignment-design-leakage-audit-v1.json").read_text(encoding="utf-8"))
    mapping_core = dict(mapping)
    mapping_id = mapping_core.pop("sealed_assignment_identity")
    assert seal("B2_DEVELOPMENT_PILOT03_SEALED_ASSIGNMENT_V1", mapping_core) == mapping_id
    packet_core = dict(packet)
    packet_id = packet_core.pop("constructor_facing_packet_identity")
    assert seal("B2_DEVELOPMENT_PILOT03_CONSTRUCTOR_PACKET_V1", packet_core) == packet_id
    assert hashlib.sha256(packet["exact_source_utf8"].encode()).hexdigest() == packet["source_object"]["sha256"]
    assert packet["unlabeled_operational_obligation"]["obligation_version"] == "SUCCESSOR_FORMULATION_C_NATURAL_ROMANIAN_V2"
    assert packet["creative_premise_family_id"] == "UNASSIGNED"
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert all(value is False for value in packet["authority_matrix"].values())
    visible = canonical(packet).lower()
    for token in (b"m13", b"absurd_logical_extension", b"absurd logical extension", b"mechanism_id", b"blind_evaluation"):
        assert token not in visible
    audit_core = dict(audit)
    audit_id = audit_core.pop("audit_identity")
    assert seal("B2_DEVELOPMENT_PILOT03_ASSIGNMENT_DESIGN_AUDIT_V1", audit_core) == audit_id
    assert audit["verdict"] == "PASS_ZERO_CONSTRUCTION"
    assert audit["deterministic_blockers"] == []

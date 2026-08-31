from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(name: str) -> dict[str, Any]:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_pilot05_rebalancing_assignment_is_distinct_blind_and_non_authorizing() -> None:
    formulation = load("humor-mechanics-batch2-development-pilot05-rebalancing-obligation-family-v1.json")
    mapping = load("humor-mechanics-batch2-development-pilot05-sealed-rebalancing-assignment-v1.json")
    packet = load("humor-mechanics-batch2-development-pilot05-constructor-facing-rebalancing-assignment-proposal-v1.json")
    audit = load("humor-mechanics-batch2-development-pilot05-rebalancing-assignment-design-audit-v1.json")
    core = dict(formulation); identity = core.pop("obligation_family_identity")
    assert seal("B2_DEVELOPMENT_PILOT05_REBALANCING_OBLIGATION_FAMILY_V1", core) == identity
    assert formulation["family_version"] == "REVERSE_DISCLOSURE_DEPENDENCY_V1"
    core = dict(mapping); mapping_id = core.pop("sealed_assignment_identity")
    assert seal("B2_DEVELOPMENT_PILOT05_SEALED_REBALANCING_ASSIGNMENT_V1", core) == mapping_id
    assert mapping["close_alternative_profile"]["primary_neighbor"] == "MISDIRECTION"
    assert mapping["close_alternative_profile"]["comic_reclassification_excluded_as_designed_support"] is True
    core = dict(packet); packet_id = core.pop("constructor_facing_packet_identity")
    assert seal("B2_DEVELOPMENT_PILOT05_REBALANCING_CONSTRUCTOR_PACKET_V1", core) == packet_id
    assert packet["creative_premise_family_id"] == "UNASSIGNED"
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert all(value is False for value in packet["authority_matrix"].values())
    visible = canonical(packet).lower()
    for token in (b"m13", b"absurd_logical_extension", b"absurd logical extension", b"misdirection", b"escalation", b"hyperbole", b"comic_reclassification", b"reclasific", b"rebalanc", b"g04b", b"pool", b"mechanism_id", b"blind_evaluation"):
        assert token not in visible
    core = dict(audit); audit_id = core.pop("audit_identity")
    assert seal("B2_DEVELOPMENT_PILOT05_REBALANCING_ASSIGNMENT_DESIGN_AUDIT_V1", core) == audit_id
    assert audit["verdict"] == "PASS_SAFE_REBALANCING_ASSIGNMENT_ZERO_CONSTRUCTION"
    assert audit["g04b_certification_performed"] is False
    assert audit["deterministic_blockers"] == []

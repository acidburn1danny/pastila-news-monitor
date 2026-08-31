import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot06_rebalancing_assignment_is_bound_blind_and_non_authorizing():
    base = ROOT / "docs/artifacts"
    mapping = json.loads((base / "humor-mechanics-batch2-development-pilot06-sealed-rebalancing-assignment-v2.json").read_text(encoding="utf-8"))
    packet = json.loads((base / "humor-mechanics-batch2-development-pilot06-constructor-facing-rebalancing-assignment-proposal-v2.json").read_text(encoding="utf-8"))
    audit = json.loads((base / "humor-mechanics-batch2-development-pilot06-rebalancing-assignment-design-audit-v2.json").read_text(encoding="utf-8"))
    assert mapping["selected_proposition_id"] == packet["selected_proposition_id"] == "P3"
    assert mapping["sufficiency_receipt_identity"] == packet["sufficiency_receipt_identity"] == "240ee7a3eaf7ec8869235212c466aee8be0e0c8126a5bee80c560c36c8043b9a"
    assert len(packet["closed_factual_authority_envelope"]["propositions"]) == 1
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert packet["creative_premise_family_id"] == "UNASSIGNED"
    assert all(value is False for value in packet["authority_matrix"].values())
    mapping_core = dict(mapping); mapping_id = mapping_core.pop("sealed_assignment_identity")
    assert mapping_id == seal("B2_DEVELOPMENT_PILOT06_SEALED_REBALANCING_ASSIGNMENT_V2", mapping_core)
    packet_core = dict(packet); packet_id = packet_core.pop("constructor_facing_packet_identity")
    assert packet_id == seal("B2_DEVELOPMENT_PILOT06_REBALANCING_CONSTRUCTOR_PACKET_V2", packet_core)
    audit_core = dict(audit); audit_id = audit_core.pop("audit_identity")
    assert audit_id == seal("B2_DEVELOPMENT_PILOT06_REBALANCING_ASSIGNMENT_DESIGN_AUDIT_V2", audit_core)
    assert audit["verdict"] == "PASS_SAFE_REBALANCING_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE"

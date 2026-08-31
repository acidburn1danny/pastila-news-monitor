import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot07_rebalancing_assignment_is_bound_blind_and_non_authorizing():
    base = ROOT / "docs/artifacts"
    mapping = json.loads((base / "humor-mechanics-batch2-development-pilot07-sealed-rebalancing-assignment-v3.json").read_text(encoding="utf-8"))
    packet = json.loads((base / "humor-mechanics-batch2-development-pilot07-constructor-facing-rebalancing-assignment-proposal-v3.json").read_text(encoding="utf-8"))
    audit = json.loads((base / "humor-mechanics-batch2-development-pilot07-rebalancing-assignment-design-audit-v3.json").read_text(encoding="utf-8"))
    assert mapping["selected_proposition_id"] == packet["selected_proposition_id"] == "P5"
    assert mapping["sufficiency_receipt_identity"] == packet["sufficiency_receipt_identity"] == "a242e3019b6d204dc6b1673da1c235bbd182887c12bbfdbb19680e48392a9d04"
    assert len(packet["closed_factual_authority_envelope"]["propositions"]) == 1
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert packet["creative_premise_family_id"] == "UNASSIGNED"
    assert all(value is False for value in packet["authority_matrix"].values())
    mapping_core = dict(mapping); mapping_id = mapping_core.pop("sealed_assignment_identity")
    assert mapping_id == seal("B2_DEVELOPMENT_PILOT07_SEALED_REBALANCING_ASSIGNMENT_V3", mapping_core)
    packet_core = dict(packet); packet_id = packet_core.pop("constructor_facing_packet_identity")
    assert packet_id == seal("B2_DEVELOPMENT_PILOT07_REBALANCING_CONSTRUCTOR_PACKET_V3", packet_core)
    audit_core = dict(audit); audit_id = audit_core.pop("audit_identity")
    assert audit_id == seal("B2_DEVELOPMENT_PILOT07_REBALANCING_ASSIGNMENT_DESIGN_AUDIT_V3", audit_core)
    assert audit["verdict"] == "PASS_SAFE_REBALANCING_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE"
    visible = canonical(packet).upper()
    for token in (b"HMCV1", b"M13", b"ABSURD_LOGICAL_EXTENSION", b"LITERALIZATION", b"MISDIRECTION", b"ESCALATION"):
        assert token not in visible

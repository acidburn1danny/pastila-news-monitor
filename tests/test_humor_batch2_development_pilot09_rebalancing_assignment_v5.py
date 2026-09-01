
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot09_rebalancing_assignment_is_bound_blind_and_non_authorizing():
    base = ROOT / "docs/artifacts"
    mapping = json.loads((base / "humor-mechanics-batch2-development-pilot09-sealed-rebalancing-assignment-v5.json").read_text(encoding="utf-8"))
    packet = json.loads((base / "humor-mechanics-batch2-development-pilot09-constructor-facing-rebalancing-assignment-proposal-v5.json").read_text(encoding="utf-8"))
    audit = json.loads((base / "humor-mechanics-batch2-development-pilot09-rebalancing-assignment-design-audit-v5.json").read_text(encoding="utf-8"))
    assert mapping["selected_proposition_id"] == packet["selected_proposition_id"] == "P5"
    assert mapping["sufficiency_receipt_identity"] == packet["sufficiency_receipt_identity"] == "f197280f8069ed15635ab32d9811bed83a5e77c6e9be737844c757d2b2292566"
    assert len(packet["closed_factual_authority_envelope"]["propositions"]) == 1
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert packet["creative_premise_family_id"] == "UNASSIGNED"
    assert packet["creative_marker_family_id"] == "UNASSIGNED_UNTIL_POSTCONSTRUCTION"
    assert packet["construction_revision_family_id"] == mapping["construction_revision_family_id"]
    assert packet["constructor_implementation_identity"].startswith("UNASSIGNED_")
    assert packet["constructor_v5_source_compatibility_evaluated"] is False
    assert packet["fragment_denyset_identity"].startswith("UNASSIGNED_")
    assert all(value is False for value in packet["authority_matrix"].values())
    mapping_core = dict(mapping); mapping_id = mapping_core.pop("sealed_assignment_identity")
    assert mapping_id == seal("B2_DEVELOPMENT_PILOT09_SEALED_REBALANCING_ASSIGNMENT_V5", mapping_core)
    packet_core = dict(packet); packet_id = packet_core.pop("constructor_facing_packet_identity")
    assert packet_id == seal("B2_DEVELOPMENT_PILOT09_REBALANCING_CONSTRUCTOR_PACKET_V5", packet_core)
    audit_core = dict(audit); audit_id = audit_core.pop("audit_identity")
    assert audit_id == seal("B2_DEVELOPMENT_PILOT09_REBALANCING_ASSIGNMENT_DESIGN_AUDIT_V5", audit_core)
    assert audit["verdict"] == "PASS_SAFE_REBALANCING_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE"
    visible = canonical(packet).upper()
    for token in (b"HMCV1", b"M13", b"ABSURD_LOGICAL_EXTENSION", b"LITERALIZATION", b"MISDIRECTION", b"ESCALATION", b"LITERALIZATION", b"PERSONIFICATION"):
        assert token not in visible



"""Verify Pilot 10 assignment is exact, label-blind, and non-authorizing."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot10_assignment_is_bound_blind_and_non_authorizing():
    mapping = json.loads((ART / "humor-mechanics-batch2-development-pilot10-sealed-assignment-v5-2.json").read_text(encoding="utf-8"))
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot10-constructor-facing-assignment-proposal-v5-2.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot10-assignment-design-audit-v5-2.json").read_text(encoding="utf-8"))
    assert mapping["selected_proposition_id"] == packet["selected_proposition_id"] == "P3"
    assert mapping["sufficiency_receipt_identity"] == packet["sufficiency_receipt_identity"] == "a3ce7039e7e01af1f32d5063022b86a0eb463da72ed5e182c32882776b3d1b1f"
    assert len(packet["closed_factual_authority_envelope"]["propositions"]) == 1
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert packet["creative_premise_family_id"] == "UNASSIGNED"
    assert packet["creative_marker_family_id"] == "UNASSIGNED_UNTIL_POSTCONSTRUCTION"
    assert packet["realization_plan"] is None and packet["witness_topology"] is None
    assert packet["constructor_implementation_identity"].startswith("UNASSIGNED_")
    assert packet["constructor_v5_2_source_compatibility_evaluated"] is False
    assert all(value is False for value in packet["authority_matrix"].values())
    core = dict(mapping); identity = core.pop("sealed_assignment_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_SEALED_ASSIGNMENT_V5_2", core)
    core = dict(packet); packet_id = core.pop("constructor_facing_packet_identity")
    assert packet_id == seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_FACING_ASSIGNMENT_PROPOSAL_V5_2", core)
    core = dict(audit); audit_id = core.pop("audit_identity")
    assert audit_id == seal("B2_DEVELOPMENT_PILOT10_ASSIGNMENT_DESIGN_AUDIT_V5_2", core)
    assert audit["verdict"] == "PASS_SAFE_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE_NO_PLANNING"
    visible = canonical(packet).upper()
    for token in (b"HMCV1", b"M13", b"ABSURD_LOGICAL_EXTENSION", b"MECHANISM_ID", b"MECHANISM_NAME", b"TARGET_MAPPING", b"POOL_OUTCOME"):
        assert token not in visible

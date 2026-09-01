import hashlib
import json
from pathlib import Path


ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: dict) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot12_assignment_is_bound_blind_and_non_authorizing() -> None:
    mapping = json.loads((ART / "humor-mechanics-batch2-development-pilot12-sealed-assignment-v5-3-1.json").read_text(encoding="utf-8"))
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot12-constructor-facing-assignment-proposal-v5-3-1.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot12-assignment-design-audit-v5-3-1.json").read_text(encoding="utf-8"))
    assert mapping["selected_proposition_id"] == packet["selected_proposition_id"] == "P5"
    assert mapping["sufficiency_receipt_identity"] == packet["sufficiency_receipt_identity"] == "f8f754e005fd50031c8a7a0daf180c325eb0b0d49c9eaea8dbcbcbf2ac45998c"
    assert mapping["eligible_but_unselected_propositions"] == ["P6"] and mapping["fallback_authority"] == "NONE"
    assert len(packet["closed_factual_authority_envelope"]["propositions"]) == 1
    assert packet["unselected_proposition_or_fallback_authority"] == "ABSENT"
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert packet["creative_premise_family_id"] == "UNASSIGNED"
    assert packet["semantic_role_signature"] is packet["affordance_topology"] is None
    assert packet["realization_plan"] is packet["witness_topology"] is packet["morphological_alignment_opportunity"] is None
    assert packet["constructor_implementation_identity"].startswith("UNASSIGNED_")
    assert packet["constructor_v5_3_1_source_compatibility_evaluated"] is False
    assert all(value is False for value in packet["authority_matrix"].values())
    core = dict(mapping); identity = core.pop("sealed_assignment_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT12_SEALED_ASSIGNMENT_V5_3_1", core)
    core = dict(packet); packet_id = core.pop("constructor_facing_packet_identity")
    assert packet_id == seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_FACING_ASSIGNMENT_PROPOSAL_V5_3_1", core)
    core = dict(audit); audit_id = core.pop("audit_identity")
    assert audit_id == seal("B2_DEVELOPMENT_PILOT12_ASSIGNMENT_DESIGN_AUDIT_V5_3_1", core)
    assert audit["verdict"] == "PASS_SAFE_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE_NO_SEMANTIC_PLANNING"
    visible = canonical(packet).upper()
    for token in (b"HMCV1", b"M13", b"ABSURD_LOGICAL_EXTENSION", b"MECHANISM_ID", b"MECHANISM_NAME",
                  b"TARGET_MAPPING", b"POOL_OUTCOME", b'"PROPOSITION_ID":"P6"'):
        assert token not in visible

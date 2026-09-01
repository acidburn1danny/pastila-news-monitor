import hashlib
import json
from pathlib import Path


ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: dict) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot13_assignment_is_bound_blind_and_non_authorizing() -> None:
    mapping = json.loads((ART / "humor-mechanics-batch2-development-pilot13-sealed-assignment-v5-3-3.json").read_text(encoding="utf-8"))
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot13-constructor-facing-assignment-proposal-v5-3-3.json").read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot13-assignment-design-audit-v5-3-3.json").read_text(encoding="utf-8"))
    assert mapping["selected_proposition_id"] == packet["selected_proposition_id"] == "P5"
    assert mapping["sufficiency_receipt_identity"] == packet["sufficiency_receipt_identity"] == "32f44383ebaea7ccdc779f1b3c4c94af57e717e735185ebdfa0d601ad33076f6"
    assert mapping["eligible_but_unselected_propositions"] == ["P6"] and mapping["fallback_authority"] == "NONE"
    assert len(packet["closed_factual_authority_envelope"]["propositions"]) == 1
    assert packet["selected_supporting_span_sha256"] == "e1b854d2b88d4489a45f6e53ce937dff06e2e9fad3abe7258a940fb5bf4a4566"
    assert packet["unselected_proposition_or_fallback_authority"] == "ABSENT"
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert packet["creative_premise_family_id"] == "UNASSIGNED"
    assert packet["semantic_role_signature"] is packet["affordance_topology"] is None
    assert packet["realization_plan"] is packet["witness_topology"] is packet["morphological_alignment_opportunity"] is None
    assert packet["constructor_compatibility_evaluated"] is False
    assert all(value is False for value in packet["authority_matrix"].values())
    core = dict(mapping); identity = core.pop("sealed_assignment_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_SEALED_ASSIGNMENT_V5_3_3", core)
    core = dict(packet); packet_id = core.pop("constructor_facing_packet_identity")
    assert packet_id == seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_FACING_ASSIGNMENT_PROPOSAL_V5_3_3", core)
    core = dict(audit); audit_id = core.pop("audit_identity")
    assert audit_id == seal("B2_DEVELOPMENT_PILOT13_ASSIGNMENT_DESIGN_AUDIT_V5_3_3", core)
    assert audit["verdict"] == "PASS_SAFE_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE_NO_SEMANTIC_PLANNING"
    assert audit["taxonomy_target_pool_answer_key_and_p6_scan"] == "PASS_ZERO_HITS"
    assert audit["factual_authority_widening"] == "ABSENT"
    visible = canonical(packet).upper()
    for token in (b"HMCV1", b"M13", b"ABSURD_LOGICAL_EXTENSION", b"MECHANISM_ID", b"MECHANISM_NAME",
                  b"TARGET_MAPPING", b"POOL_OUTCOME", b"ANSWER_KEY", b'"PROPOSITION_ID":"P6"'):
        assert token not in visible

import hashlib
import json
from pathlib import Path

from pastila_scout.humor_batch2_constructor_access_v1 import prepare_development_constructor_access_v1

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot13_g02b_v5_3_3_is_exact_blind_pathless_and_uninvoked():
    denyset = json.loads((ART / "humor-mechanics-batch2-nonblind-development-fragment-denyset-v5-3-3.json").read_text(encoding="utf-8"))
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot13-constructor-facing-assignment-g02b-v5-3-3.json").read_text(encoding="utf-8"))
    release_path = ART / "humor-mechanics-batch2-development-pilot13-constructor-access-release-v5-3-3.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot13-g02b-preconstruction-audit-v5-3-3.json").read_text(encoding="utf-8"))

    packet_core = dict(packet)
    packet_id = packet_core.pop("constructor_facing_packet_identity")
    assert packet_id == seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_PACKET_G02B_V5_3_3", packet_core)
    assert release["release_identity"] == seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_ACCESS_RELEASE_V5_3_3", release["release_core"])
    audit_core = dict(audit)
    audit_id = audit_core.pop("audit_identity")
    assert audit_id == seal("B2_DEVELOPMENT_PILOT13_G02B_AUDIT_V5_3_3", audit_core)
    denyset_core = dict(denyset)
    denyset_id = denyset_core.pop("fragment_denyset_identity")
    assert denyset_id == seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V5_3_3", denyset_core)

    assert len(denyset["candidate_sources"]) == 10
    assert len(denyset["normalized_ngram_sha256"]) == 2698
    assert denyset["blind_reserve_accessed"] is False
    assert packet["selected_proposition_id"] == "P5"
    assert packet["unselected_proposition_or_fallback_authority"] == "ABSENT"
    assert len(packet["proposition_derived_typed_plan"]) == 3
    assert len(packet["predicate_semantic_signatures"]) == 3
    assert len(packet["edge_necessity_witnesses"]) == 2
    assert all(edge["counterfactual_dependency"] and edge["non_arbitrary"] for edge in packet["edge_necessity_witnesses"])
    assert packet["constructor_source_compatibility_identity"] == "b8f0b874ce629de2c1e1d2f5b8744b4425178219de57e7f22631baecb54a01c0"
    assert packet["constructor_source_compatibility_audit_identity"] == "1b1a0ce66e183558343bebce6d37dee253106be2a06e3f447f1def343d4422e2"
    assert packet["class_a_closure"] == "PASS_ALL_DETERMINISTIC_CLOSURE_BEFORE_PROVIDER"
    assert packet["class_b_state"] == "NOT_CREATED_PRE_REALIZATION"
    assert packet["provider_payload_schema"] == ["clause"]
    assert packet["mandatory_release_facing_path"] == [
        "FROZEN_SEMANTICS", "PRE_INVOCATION_CLOSURE", "CLAUSE_ONLY_GENERATION",
        "ACTUAL_UTF8_BYTES", "TRUSTED_COORDINATE_BOUND_CLASS_B_OBSERVATION",
        "SEMANTIC_CONFORMANCE", "CONDITIONAL_EMITTER",
    ]
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert all(value is False for value in packet["authority_matrix"].values())
    assert release["release_core"]["single_use_state"] == "UNCONSUMED_0_OF_1_NOT_AUTHORIZED"
    assert release["release_core"]["constructor_invocation_authorized"] is False
    assert all(value is False for value in release["transport_policy"].values() if isinstance(value, bool))
    assert audit["verdict"] == "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION"
    assert audit["post_qualification_deterministic_infrastructure_defect"] == "REPAIRED_PILOT13_RELEASE_SCHEMA_AND_BINDING_ALLOWLIST"

    visible = canonical(packet).lower()
    for forbidden in (b"hmcv1", b"m13", b"mechanism_id", b"mapping_commitment", b"g04b", b'"proposition_id":"p6"'):
        assert forbidden not in visible

    prepared = prepare_development_constructor_access_v1(release_bytes=release_path.read_bytes())
    assert prepared.release_identity == release["release_identity"]
    assert prepared.packet_identity == packet_id

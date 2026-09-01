import hashlib
import json
from pathlib import Path

from pastila_scout.humor_batch2_constructor_access_v1 import prepare_development_constructor_access_v1

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot12_g02b_v5_3_1_is_exact_semantic_pathless_and_uninvoked():
    denyset = json.loads((ART / "humor-mechanics-batch2-nonblind-development-fragment-denyset-v5-3-1.json").read_text(encoding="utf-8"))
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot12-constructor-facing-assignment-g02b-v5-3-1.json").read_text(encoding="utf-8"))
    release_path = ART / "humor-mechanics-batch2-development-pilot12-constructor-access-release-v5-3-1.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot12-g02b-preconstruction-audit-v5-3-1.json").read_text(encoding="utf-8"))
    packet_core = dict(packet); packet_id = packet_core.pop("constructor_facing_packet_identity")
    assert packet_id == seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_PACKET_G02B_V5_3_1", packet_core)
    assert release["release_identity"] == seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_ACCESS_RELEASE_V5_3_1", release["release_core"])
    audit_core = dict(audit); audit_id = audit_core.pop("audit_identity")
    assert audit_id == seal("B2_DEVELOPMENT_PILOT12_G02B_AUDIT_V5_3_1", audit_core)
    denyset_core = dict(denyset); denyset_id = denyset_core.pop("fragment_denyset_identity")
    assert denyset_id == seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V5_3_1", denyset_core)
    assert len(denyset["candidate_sources"]) == 10 and denyset["blind_reserve_accessed"] is False
    assert packet["selected_proposition_id"] == "P5" and len(packet["proposition_derived_typed_plan"]) == 3
    assert packet["unselected_proposition_or_fallback_authority"] == "ABSENT"
    assert len(packet["predicate_semantic_signatures"]) == 3 and len(packet["edge_necessity_witnesses"]) == 2
    assert all(edge["counterfactual_dependency"] and edge["non_arbitrary"] for edge in packet["edge_necessity_witnesses"])
    assert packet["constructor_source_compatibility_identity"] == "1a3ca6684d124cb036dc2c738fd4d1fa5d13985207b4f4d3189b4baf977f7721"
    assert packet["constructor_source_compatibility_audit_identity"] == "4a64a029dbcb2cd8e6346f66ffdc1aeca02061a5ab320aa1a3bd24e5f94cae4f"
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert all(value is False for value in packet["authority_matrix"].values())
    assert release["release_core"]["single_use_state"] == "UNCONSUMED_0_OF_1_NOT_AUTHORIZED"
    assert audit["verdict"] == "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION"
    prepared = prepare_development_constructor_access_v1(release_bytes=release_path.read_bytes())
    assert prepared.release_identity == release["release_identity"] and prepared.packet_identity == packet_id

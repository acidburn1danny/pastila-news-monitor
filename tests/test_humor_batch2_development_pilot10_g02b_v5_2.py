import hashlib
import json
from pathlib import Path

from pastila_scout.humor_batch2_constructor_access_v1 import prepare_development_constructor_access_v1

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot10_g02b_v5_2_release_is_exact_pathless_and_uninvoked():
    denyset = json.loads((ART / "humor-mechanics-batch2-nonblind-development-fragment-denyset-v5-2.json").read_text(encoding="utf-8"))
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot10-constructor-facing-assignment-g02b-v5-2.json").read_text(encoding="utf-8"))
    release_path = ART / "humor-mechanics-batch2-development-pilot10-constructor-access-release-v5-2.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot10-g02b-preconstruction-audit-v5-2.json").read_text(encoding="utf-8"))

    packet_core = dict(packet)
    packet_identity = packet_core.pop("constructor_facing_packet_identity")
    assert packet_identity == seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_PACKET_G02B_V5_2", packet_core)
    assert release["release_identity"] == seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_ACCESS_RELEASE_V5_2", release["release_core"])
    audit_core = dict(audit)
    audit_identity = audit_core.pop("audit_identity")
    assert audit_identity == seal("B2_DEVELOPMENT_PILOT10_G02B_AUDIT_V5_2", audit_core)
    denyset_core = dict(denyset)
    denyset_identity = denyset_core.pop("fragment_denyset_identity")
    assert denyset_identity == seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V5_2", denyset_core)

    assert len(denyset["candidate_sources"]) == 9
    assert denyset["blind_reserve_accessed"] is False
    assert packet["selected_proposition_id"] == "P3"
    assert len(packet["closed_factual_authority_envelope"]["propositions"]) == 1
    assert len(packet["proposition_derived_typed_plan"]) == 3
    assert sum(len(node["predecessor_node_ids"]) for node in packet["proposition_derived_typed_plan"]) == 2
    assert packet["constructor_implementation_identity"] == "bdf48e9942f097f0259831c0f2f611e50644cdbe7179a2dc7d990bf9ab2b5493"
    assert packet["realization_provider_identity"] == "36b3669acb5e7d2b772ad6d8a912f4cdbfea8f58e3c45e72cafcd206336afce8"
    assert packet["candidate_emitter_identity"] == "e325bd20ba1f58bbc48a6e749dc7a505e5522e4ff11c798855e8d530dae113d4"
    assert packet["constructor_source_compatibility_identity"] == "fda3e7f2bea30b8429fb4f93415c85b81a3322595be6eae7542a367d5f0ad9ee"
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert all(value is False for value in packet["authority_matrix"].values())
    assert release["release_core"]["single_use_state"] == "UNCONSUMED_0_OF_1_NOT_AUTHORIZED"
    assert release["release_core"]["constructor_invocation_authorized"] is False
    assert audit["pre_emission_conformance_enforcement_binding"] == "PASS_EXACT_MANDATORY_BEFORE_EMISSION"
    assert audit["verdict"] == "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION"
    prepared = prepare_development_constructor_access_v1(release_bytes=release_path.read_bytes())
    assert prepared.release_identity == release["release_identity"]
    assert prepared.packet_identity == packet_identity

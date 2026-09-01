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


def test_pilot09_g02b_release_is_blind_pathless_bound_and_uninvoked():
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot09-constructor-facing-assignment-g02b-v5-1.json").read_text(encoding="utf-8"))
    release_path = ART / "humor-mechanics-batch2-development-pilot09-constructor-access-release-v5-1.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot09-g02b-preconstruction-audit-v5-1.json").read_text(encoding="utf-8"))
    denyset = json.loads((ART / "humor-mechanics-batch2-nonblind-development-fragment-denyset-v5-1.json").read_text(encoding="utf-8"))
    core = dict(packet); identity = core.pop("constructor_facing_packet_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_PACKET_G02B_V5_1", core)
    assert release["release_identity"] == seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_ACCESS_RELEASE_V5_1", release["release_core"])
    core = dict(audit); identity = core.pop("audit_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_G02B_AUDIT_V5_1", core)
    core = dict(denyset); identity = core.pop("fragment_denyset_identity")
    assert identity == seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V5_1", core)
    assert len(denyset["candidate_sources"]) == 8 and denyset["blind_reserve_accessed"] is False
    assert packet["selected_proposition_id"] == "P5" and len(packet["closed_factual_authority_envelope"]["propositions"]) == 1
    assert packet["constructor_implementation_generation"] == "5.1"
    assert packet["constructor_implementation_identity"] == "c7134743e6b0e7c3ed7637bff3203f774159f192fef7a7b712e15d4d44a6f419"
    assert packet["constructor_source_compatibility_identity"] == "6554798852137176e9d0b860523b1110da5ac279c9ceae456a99acc09f70a50d"
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert all(value is False for value in packet["authority_matrix"].values())
    prepared = prepare_development_constructor_access_v1(release_bytes=release_path.read_bytes())
    assert prepared.packet_identity == packet["constructor_facing_packet_identity"]
    assert prepared.release_identity == release["release_identity"]
    assert release["release_core"]["single_use_state"] == "UNCONSUMED_0_OF_1_NOT_AUTHORIZED"
    assert audit["verdict"] == "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION"

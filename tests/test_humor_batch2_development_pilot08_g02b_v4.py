import hashlib
import json
from pathlib import Path

from pastila_scout.humor_batch2_constructor_access_v1 import prepare_development_constructor_access_v1

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot08_g02b_release_is_pathless_blind_and_not_authorized():
    base = ROOT / "docs/artifacts"
    packet = json.loads((base / "humor-mechanics-batch2-development-pilot08-constructor-facing-assignment-g02b-v4.json").read_text(encoding="utf-8"))
    release = json.loads((base / "humor-mechanics-batch2-development-pilot08-constructor-access-release-v4.json").read_text(encoding="utf-8"))
    audit = json.loads((base / "humor-mechanics-batch2-development-pilot08-g02b-preconstruction-audit-v4.json").read_text(encoding="utf-8"))
    packet_core = dict(packet); packet_id = packet_core.pop("constructor_facing_packet_identity")
    assert packet_id == seal("B2_DEVELOPMENT_PILOT08_CONSTRUCTOR_PACKET_G02B_V4", packet_core)
    assert release["release_identity"] == seal("B2_DEVELOPMENT_PILOT08_CONSTRUCTOR_ACCESS_RELEASE_V4", release["release_core"])
    audit_core = dict(audit); audit_id = audit_core.pop("audit_identity")
    assert audit_id == seal("B2_DEVELOPMENT_PILOT08_G02B_AUDIT_V4", audit_core)
    assert packet["selected_proposition_id"] == "P5"
    assert len(packet["closed_factual_authority_envelope"]["propositions"]) == 1
    assert "mapping_commitment" not in packet
    assert "g04b_pool_certification" not in packet["authority_matrix"]
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert packet["constructor_implementation_identity"] == "68101cd87711761c2c739dc989490c5dd05eaccc0fac03472b9aac180ce647e4"
    assert packet["constructor_implementation_generation"] == 4
    assert packet["fragment_denyset_identity"] == "d35beab3b093d118e52369239477f6dc835e764976e44336793f90704b38c844"
    assert all(value is False for value in packet["authority_matrix"].values())
    assert release["release_core"]["single_use_state"] == "UNCONSUMED_0_OF_1_NOT_AUTHORIZED"
    assert release["release_core"]["constructor_invocation_authorized"] is False
    assert audit["verdict"] == "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION"


def test_pilot08_release_prepares_pathless_bytes_without_constructor_invocation():
    release_path = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot08-constructor-access-release-v4.json"
    prepared = prepare_development_constructor_access_v1(release_bytes=release_path.read_bytes())
    assert prepared.release_identity == "51c58df40ad779ed8b1e14207b69609980a08bc40f2db6de0b4d8398a9fe1b52"
    assert prepared.packet_identity == "4e812e402c2d56f5b95f5aa60bd09630117de72377d2a6bb8da0e446ac2634ae"

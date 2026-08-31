import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot06_g02b_release_is_pathless_blind_and_not_authorized():
    base = ROOT / "docs/artifacts"
    packet = json.loads((base / "humor-mechanics-batch2-development-pilot06-constructor-facing-assignment-g02b-v2.json").read_text(encoding="utf-8"))
    release = json.loads((base / "humor-mechanics-batch2-development-pilot06-constructor-access-release-v2.json").read_text(encoding="utf-8"))
    audit = json.loads((base / "humor-mechanics-batch2-development-pilot06-g02b-preconstruction-audit-v2.json").read_text(encoding="utf-8"))
    packet_core = dict(packet); packet_id = packet_core.pop("constructor_facing_packet_identity")
    assert packet_id == seal("B2_DEVELOPMENT_PILOT06_CONSTRUCTOR_PACKET_G02B_V2", packet_core)
    assert release["release_identity"] == seal("B2_DEVELOPMENT_PILOT06_CONSTRUCTOR_ACCESS_RELEASE_V2", release["release_core"])
    audit_core = dict(audit); audit_id = audit_core.pop("audit_identity")
    assert audit_id == seal("B2_DEVELOPMENT_PILOT06_G02B_AUDIT_V2", audit_core)
    assert packet["selected_proposition_id"] == "P3"
    assert len(packet["closed_factual_authority_envelope"]["propositions"]) == 1
    assert "mapping_commitment" not in packet
    assert "g04b_pool_certification" not in packet["authority_matrix"]
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert all(value is False for value in packet["authority_matrix"].values())
    assert release["release_core"]["single_use_state"] == "UNCONSUMED_0_OF_1_NOT_AUTHORIZED"
    assert release["release_core"]["constructor_invocation_authorized"] is False
    assert audit["verdict"] == "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION"

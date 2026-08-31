import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot07_prospective_packet_is_unsigned_and_non_authorizing():
    base = ROOT / "docs/artifacts"
    prospective = json.loads((base / "humor-mechanics-batch2-development-pilot07-preingestion-v1.json").read_text(encoding="utf-8"))
    independence = json.loads((base / "humor-mechanics-batch2-development-pilot07-family-independence-v1.json").read_text(encoding="utf-8"))
    packet = json.loads((base / "humor-mechanics-batch2-development-pilot07-signing-packet-v1.json").read_text(encoding="utf-8"))
    core = dict(prospective); identity = core.pop("preingestion_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT07_PREINGESTION_V1", core)
    icore = dict(independence); iid = icore.pop("family_independence_identity")
    assert iid == seal("B2_DEVELOPMENT_PILOT07_FAMILY_INDEPENDENCE_V1", icore)
    assert len(prospective["factual_authority_envelope"]["propositions"]) == 6
    assert prospective["proposition_sufficiency_evaluated"] is False
    assert prospective["selected_proposition"] == prospective["target_mechanism"] == prospective["operational_obligation"] == "UNASSIGNED"
    assert prospective["family_identities"]["creative_premise_family_id"] == "UNASSIGNED"
    assert packet["status"] == "UNSIGNED" and packet["signatures_present"] == 0 and len(packet["signature_requests"]) == 8
    assert all(value is False for value in prospective["authority_matrix"].values())

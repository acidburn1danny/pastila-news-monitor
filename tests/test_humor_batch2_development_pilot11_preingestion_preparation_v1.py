import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot11_prospective_packet_is_exact_unsigned_and_non_authorizing() -> None:
    prospective = json.loads((ART / "humor-mechanics-batch2-development-pilot11-preingestion-v1.json").read_text(encoding="utf-8"))
    independence = json.loads((ART / "humor-mechanics-batch2-development-pilot11-family-independence-v1.json").read_text(encoding="utf-8"))
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot11-signing-packet-v1.json").read_text(encoding="utf-8"))
    core = dict(prospective); identity = core.pop("preingestion_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT11_PREINGESTION_V1", core)
    core = dict(independence); identity = core.pop("family_independence_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT11_FAMILY_INDEPENDENCE_V1", core)
    source = (ROOT / "owner-source-pilot11-v1.txt").read_text(encoding="utf-8")
    source_bytes = source.encode()
    propositions = prospective["factual_authority_envelope"]["propositions"]
    assert len(propositions) == 7
    for item in propositions:
        span = item["supporting_span"]
        cs, ce = span["character_coordinates"]; bs, be = span["utf8_byte_coordinates"]
        assert source[cs:ce].encode() == source_bytes[bs:be]
        assert hashlib.sha256(source_bytes[bs:be]).hexdigest() == span["span_sha256"]
    assert prospective["proposition_sufficiency_evaluated"] is False
    assert prospective["semantic_role_signature"] == prospective["affordance_topology"] == "UNASSIGNED"
    assert prospective["realization_plan"] == prospective["witness_topology"] == "UNASSIGNED"
    assert all(value is False for value in prospective["authority_matrix"].values())
    assert independence["result"] == "PASS_FRESH_FAMILY_INDEPENDENCE"
    assert packet["status"] == "UNSIGNED" and packet["signatures_present"] == 0
    assert len(packet["signature_requests"]) == 8
    assert packet["constructor_semantic_plan_release_or_invocation_performed"] is False

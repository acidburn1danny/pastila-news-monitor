"""Verify Pilot 10 prospective preparation is exact, unsigned, and non-authorizing."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot10_prospective_packet_is_unsigned_and_non_authorizing():
    prospective = json.loads((ART / "humor-mechanics-batch2-development-pilot10-preingestion-v1.json").read_text(encoding="utf-8"))
    independence = json.loads((ART / "humor-mechanics-batch2-development-pilot10-family-independence-v1.json").read_text(encoding="utf-8"))
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot10-signing-packet-v1.json").read_text(encoding="utf-8"))
    core = dict(prospective); identity = core.pop("preingestion_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_PREINGESTION_V1", core)
    core = dict(independence); identity = core.pop("family_independence_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_FAMILY_INDEPENDENCE_V1", core)
    source = (ROOT / "owner-source-pilot10-v1.txt").read_text(encoding="utf-8")
    source_bytes = source.encode()
    assert len(prospective["factual_authority_envelope"]["propositions"]) == 7
    for item in prospective["factual_authority_envelope"]["propositions"]:
        span = item["supporting_span"]
        cs, ce = span["character_coordinates"]; bs, be = span["utf8_byte_coordinates"]
        assert source[cs:ce].encode() == source_bytes[bs:be]
        assert hashlib.sha256(source_bytes[bs:be]).hexdigest() == span["span_sha256"]
    assert prospective["proposition_sufficiency_evaluated"] is False
    assert prospective["constructor_source_compatibility_evaluated"] is False
    assert prospective["selected_proposition"] == prospective["target_mechanism"] == prospective["operational_obligation"] == "UNASSIGNED"
    assert prospective["family_identities"]["creative_premise_family_id"] == "UNASSIGNED"
    assert packet["status"] == "UNSIGNED" and packet["signatures_present"] == 0
    assert len(packet["signature_requests"]) == 8
    assert packet["realization_candidate_emission_or_preemission_conformance_performed"] is False
    assert all(value is False for value in prospective["authority_matrix"].values())

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_pilot08_prospective_packet_is_unsigned_and_non_authorizing() -> None:
    prospective = json.loads(
        (ARTIFACTS / "humor-mechanics-batch2-development-pilot08-preingestion-v1.json").read_text(encoding="utf-8")
    )
    independence = json.loads(
        (ARTIFACTS / "humor-mechanics-batch2-development-pilot08-family-independence-v1.json").read_text(encoding="utf-8")
    )
    packet = json.loads(
        (ARTIFACTS / "humor-mechanics-batch2-development-pilot08-signing-packet-v1.json").read_text(encoding="utf-8")
    )
    core = dict(prospective)
    identity = core.pop("preingestion_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT08_PREINGESTION_V1", core)
    independence_core = dict(independence)
    independence_identity = independence_core.pop("family_independence_identity")
    assert independence_identity == seal("B2_DEVELOPMENT_PILOT08_FAMILY_INDEPENDENCE_V1", independence_core)
    assert len(prospective["factual_authority_envelope"]["propositions"]) == 7
    source = (ROOT / "owner-source-pilot08-v1.txt").read_text(encoding="utf-8")
    source_bytes = source.encode("utf-8")
    for proposition in prospective["factual_authority_envelope"]["propositions"]:
        span = proposition["supporting_span"]
        char_start, char_end = span["character_coordinates"]
        byte_start, byte_end = span["utf8_byte_coordinates"]
        assert char_start < char_end and byte_start < byte_end
        assert source[char_start:char_end].encode("utf-8") == source_bytes[byte_start:byte_end]
        assert hashlib.sha256(source_bytes[byte_start:byte_end]).hexdigest() == span["span_sha256"]
    assert prospective["proposition_sufficiency_evaluated"] is False
    assert prospective["selected_proposition"] == prospective["target_mechanism"] == prospective["operational_obligation"] == "UNASSIGNED"
    assert prospective["family_identities"]["creative_premise_family_id"] == "UNASSIGNED"
    assert prospective["family_identities"]["construction_revision_family_id"] == "UNASSIGNED"
    assert prospective["family_identities"]["creative_marker_family_id"] == "UNASSIGNED"
    assert prospective["constructor_v1_status"] == "HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_RELEASE"
    assert prospective["future_constructor_implementation_identity"] == "UNASSIGNED"
    assert prospective["fragment_collision_evaluated"] is False
    assert packet["status"] == "UNSIGNED"
    assert packet["signatures_present"] == 0
    assert len(packet["signature_requests"]) == 8
    assert packet["constructor_implementation_or_release_performed"] is False
    assert packet["fragment_collision_evaluation_performed"] is False
    assert all(value is False for value in prospective["authority_matrix"].values())

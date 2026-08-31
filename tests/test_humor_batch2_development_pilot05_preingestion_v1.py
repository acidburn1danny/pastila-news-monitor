from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot05-v1.txt"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def seal(namespace: str, value: dict) -> str:
    return hashlib.sha256(json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def test_pilot05_prospective_record_is_sealed_unassigned_and_nonoperational() -> None:
    value = load("humor-mechanics-batch2-development-pilot05-preingestion-v1.json")
    identity = value.pop("preingestion_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT05_PREINGESTION_V1", value)
    assert value["status"] == "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED"
    assert value["validation_identity"] == "42845c8ad8560e47a91383e1f27a8ca92ce532ab74566540e437ea4911600d3e"
    assert value["target_mechanism"] == value["operational_obligation"] == "UNASSIGNED"
    assert value["family_identities"]["creative_premise_family_id"] == "UNASSIGNED"
    assert not value["ingested"] and not value["archive_write"] and not value["git_archival"]
    assert not value["g01a_admitted"] and not value["g01b_admitted"] and not value["g04b_pool_certification_performed"]
    assert not any(value["authority_matrix"].values())


def test_pilot05_seven_propositions_rederive_character_byte_and_hash_bindings() -> None:
    value = load("humor-mechanics-batch2-development-pilot05-preingestion-v1.json")
    source = SOURCE.read_bytes(); text = source.decode("utf-8")
    propositions = value["factual_authority_envelope"]["propositions"]
    assert [item["proposition_id"] for item in propositions] == [f"P{i}" for i in range(1, 8)]
    for item in propositions:
        for name in ("supporting_span", "subject", "predicate", "object"):
            part = item[name]; cs, ce = part["character_coordinates"]; bs, be = part["utf8_byte_coordinates"]
            assert text[cs:ce].encode() == source[bs:be]
            assert hashlib.sha256(source[bs:be]).hexdigest() == part.get("span_sha256", part.get("sha256"))
        if item["qualification"]:
            part = item["qualification"]; cs, ce = part["character_coordinates"]; bs, be = part["utf8_byte_coordinates"]
            assert text[cs:ce].encode() == source[bs:be]
            assert hashlib.sha256(source[bs:be]).hexdigest() == part["sha256"]


def test_pilot05_family_independence_covers_four_prior_pilots() -> None:
    value = load("humor-mechanics-batch2-development-pilot05-family-independence-v1.json")
    identity = value.pop("family_independence_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT05_FAMILY_INDEPENDENCE_V1", value)
    assert value["result"] == "PASS_FRESH_FAMILY_INDEPENDENCE"
    assert len(value["prior_source_sha256"]) == 4 and len(value["prior_family_identities"]) == 4
    assert value["source_hash_distinct"] and value["git_blob_distinct"] and not value["exact_prior_line_reuse"]
    assert value["source_event_topic_revision_sibling_syndication_same_event_relation"] is False
    assert value["selected_or_shaped_using_governance_obligation_target_gap_pool_confound_or_prior_candidate"] is False
    assert value["blind_family_access"] is False


def test_pilot05_unsigned_packet_has_exact_eight_requests_and_current_head() -> None:
    packet = load("humor-mechanics-batch2-development-pilot05-signing-packet-v1.json")
    assert packet["packet_identity"] == seal("B2_DEVELOPMENT_PILOT05_SIGNING_PACKET_V1", packet["packet_core"])
    assert packet["status"] == "UNSIGNED" and packet["signatures_present"] == 0 and len(packet["signature_requests"]) == 8
    assert packet["packet_core"]["prior_ledger_head"] == "3a172491ec99d5f8c0ef2d4be075912b5518f6b42bb19641bd60ab9b20d26fd4"
    assert not packet["source_ingested"] and not packet["archive_written"] and packet["ledger_events_appended"] == 0
    nonces = set()
    for request in packet["signature_requests"]:
        challenge = request["challenge"]; core = {k: v for k, v in challenge.items() if k != "challenge_identity"}
        assert challenge["challenge_identity"] == seal("B2_PILOT05_SIGNING_CHALLENGE_V1", core)
        assert challenge["grants_operational_content_access"] is False and challenge["nonce"] not in nonces
        nonces.add(challenge["nonce"])

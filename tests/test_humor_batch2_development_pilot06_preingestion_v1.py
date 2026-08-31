"""Verify Pilot 06 prospective identities and unsigned signing packet."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot06-v1.txt"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def seal(namespace: str, value: dict) -> str:
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot06_prospective_record_is_sealed_unassigned_and_nonoperational() -> None:
    value = load("humor-mechanics-batch2-development-pilot06-preingestion-v1.json")
    core = dict(value); identity = core.pop("preingestion_identity")
    assert seal("B2_DEVELOPMENT_PILOT06_PREINGESTION_V1", core) == identity
    assert value["status"] == "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED"
    assert value["validation_identity"] == "8c422ad86a4904485e4b854bc6341a917d6e9598521a50955fcc9bfce0a126d5"
    assert value["selected_proposition"] == value["target_mechanism"] == value["operational_obligation"] == "UNASSIGNED"
    assert value["family_identities"]["creative_premise_family_id"] == "UNASSIGNED"
    assert value["proposition_sufficiency_evaluated"] is False
    assert not value["ingested"] and not value["archive_write"] and not value["g01a_admitted"] and not value["g01b_admitted"]
    assert not any(value["authority_matrix"].values())


def test_pilot06_six_propositions_rederive_coordinates_and_hashes() -> None:
    value = load("humor-mechanics-batch2-development-pilot06-preingestion-v1.json")
    source = SOURCE.read_bytes(); text = source.decode()
    propositions = value["factual_authority_envelope"]["propositions"]
    assert [item["proposition_id"] for item in propositions] == [f"P{i}" for i in range(1, 7)]
    for item in propositions:
        for name in ("supporting_span", "subject", "predicate", "object"):
            part = item[name]; cs, ce = part["character_coordinates"]; bs, be = part["utf8_byte_coordinates"]
            assert text[cs:ce].encode() == source[bs:be]
            assert hashlib.sha256(source[bs:be]).hexdigest() == part.get("span_sha256", part.get("sha256"))
        if item["qualification"]:
            part = item["qualification"]; cs, ce = part["character_coordinates"]; bs, be = part["utf8_byte_coordinates"]
            assert text[cs:ce].encode() == source[bs:be]
            assert hashlib.sha256(source[bs:be]).hexdigest() == part["sha256"]


def test_pilot06_independence_and_unsigned_packet_are_fail_closed() -> None:
    value = load("humor-mechanics-batch2-development-pilot06-family-independence-v1.json")
    core = dict(value); identity = core.pop("family_independence_identity")
    assert seal("B2_DEVELOPMENT_PILOT06_FAMILY_INDEPENDENCE_V1", core) == identity
    assert value["result"] == "PASS_FRESH_FAMILY_INDEPENDENCE"
    assert len(value["prior_source_sha256"]) == 5 and len(value["prior_family_identities"]) == 5
    assert value["source_hash_distinct"] and value["git_blob_distinct"] and not value["exact_prior_line_reuse"]
    assert value["blind_family_access"] is False
    packet = load("humor-mechanics-batch2-development-pilot06-signing-packet-v1.json")
    assert packet["packet_identity"] == seal("B2_DEVELOPMENT_PILOT06_SIGNING_PACKET_V1", packet["packet_core"])
    assert packet["status"] == "UNSIGNED" and packet["signatures_present"] == 0 and len(packet["signature_requests"]) == 8
    assert packet["packet_core"]["prior_ledger_head"] == "20d5c36ec01ceaec6cd85131f6253bbd300f710021804ce3debf7d3880bc59b2"
    assert packet["proposition_sufficiency_evaluated"] is False
    assert not packet["source_ingested"] and not packet["archive_written"] and packet["ledger_events_appended"] == 0
    nonces = set()
    for request in packet["signature_requests"]:
        challenge = request["challenge"]; core = {k: v for k, v in challenge.items() if k != "challenge_identity"}
        assert challenge["challenge_identity"] == seal("B2_PILOT06_SIGNING_CHALLENGE_V1", core)
        assert challenge["grants_operational_content_access"] is False and challenge["nonce"] not in nonces
        nonces.add(challenge["nonce"])

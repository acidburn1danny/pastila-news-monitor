from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot02-v1.txt"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: object) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_prospective_identity_and_authority_boundaries() -> None:
    record = load("humor-mechanics-batch2-development-pilot02-preingestion-v1.json")
    core = {k: v for k, v in record.items() if k != "preingestion_identity"}
    assert record["preingestion_identity"] == seal("B2_DEVELOPMENT_PILOT02_PREINGESTION_V1", core)
    assert record["status"] == "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED"
    assert not record["ingested"] and not record["archive_write"] and not record["git_archival"]
    assert not record["g01a_admitted"] and not record["g01b_admitted"]
    assert record["target_mechanism"] == record["operational_obligation"] == "UNASSIGNED"
    assert record["family_identities"]["creative_premise_family_id"] == "UNASSIGNED"
    assert all(value is False for value in record["authority_matrix"].values())


def test_every_proposition_span_and_component_hash_rederives() -> None:
    record = load("humor-mechanics-batch2-development-pilot02-preingestion-v1.json")
    source = SOURCE.read_bytes()
    text = source.decode("utf-8")
    propositions = record["factual_authority_envelope"]["propositions"]
    assert [item["proposition_id"] for item in propositions] == [f"P{i}" for i in range(1, 8)]
    for item in propositions:
        span = item["supporting_span"]
        cs, ce = span["character_coordinates"]
        bs, be = span["utf8_byte_coordinates"]
        assert text[cs:ce].encode("utf-8") == source[bs:be]
        assert hashlib.sha256(source[bs:be]).hexdigest() == span["span_sha256"]
        for field in ("subject", "predicate", "object"):
            component = item[field]
            cs, ce = component["character_coordinates"]
            bs, be = component["utf8_byte_coordinates"]
            assert text[cs:ce].encode("utf-8") == source[bs:be]
            assert hashlib.sha256(source[bs:be]).hexdigest() == component["sha256"]
        if item["qualification"]:
            component = item["qualification"]
            cs, ce = component["character_coordinates"]
            bs, be = component["utf8_byte_coordinates"]
            assert text[cs:ce].encode("utf-8") == source[bs:be]
            assert hashlib.sha256(source[bs:be]).hexdigest() == component["sha256"]


def test_family_independence_is_sealed_and_fresh() -> None:
    record = load("humor-mechanics-batch2-development-pilot02-family-independence-v1.json")
    core = {k: v for k, v in record.items() if k != "family_independence_identity"}
    assert record["family_independence_identity"] == seal("B2_DEVELOPMENT_PILOT02_FAMILY_INDEPENDENCE_V1", core)
    assert record["result"] == "PASS_FRESH_FAMILY_INDEPENDENCE"
    assert record["source_hash_distinct"] and record["git_blob_distinct"]
    assert not record["source_event_topic_revision_sibling_same_event_relation"]
    assert not record["prior_target_or_obligation_assignment"]
    assert not record["prior_construction_or_model_exposure"]
    assert not record["blind_family_access"]
    assert not record["selected_using_successor_obligation_or_target_friendly_shape"]


def test_unsigned_packet_has_exact_roles_challenges_and_no_authority() -> None:
    packet = load("humor-mechanics-batch2-development-pilot02-signing-packet-v1.json")
    assert packet["packet_identity"] == seal("B2_DEVELOPMENT_PILOT02_SIGNING_PACKET_V1", packet["packet_core"])
    assert packet["status"] == "UNSIGNED" and packet["signatures_present"] == 0
    assert not packet["source_ingested"] and not packet["archive_written"] and packet["ledger_events_appended"] == 0
    expected = [
        (0, "RIGHTS_ADMISSION", "RIGHTS_CUSTODIAN"),
        (1, "ACQUISITION_ADMISSION", "RIGHTS_CUSTODIAN"),
        (1, "ACQUISITION_ADMISSION", "ACQUISITION_CUSTODIAN"),
        (2, "IMMUTABLE_ARCHIVE_ADMISSION", "RIGHTS_CUSTODIAN"),
        (2, "IMMUTABLE_ARCHIVE_ADMISSION", "ACQUISITION_CUSTODIAN"),
        (3, "FAMILY_CLOSURE", "FAMILY_CUSTODIAN"),
        (4, "DEVELOPMENT_PARTITION_SEAL", "PARTITION_CUSTODIAN"),
        (5, "CONTAMINATION_LEDGER_ADVANCEMENT", "CONTAMINATION_AUDITOR"),
    ]
    assert [(x["operation_ordinal"], x["purpose"], x["role"]) for x in packet["signature_requests"]] == expected
    nonces = set()
    for request in packet["signature_requests"]:
        assert request["signature_status"] == "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION"
        challenge = request["challenge"]
        identity = challenge.pop("challenge_identity")
        assert identity == seal("B2_PILOT02_SIGNING_CHALLENGE_V1", challenge)
        challenge["challenge_identity"] = identity
        assert challenge["prior_ledger_head"] == "86aa81e1ba197d0ff7b4fe19bc7fa90773e7ded7596839d7d76ee5cdd74ae254"
        assert not challenge["grants_operational_content_access"]
        assert challenge["nonce"] not in nonces
        nonces.add(challenge["nonce"])

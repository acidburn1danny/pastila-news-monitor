from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot03-v1.txt"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: object) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_prospective_record_is_sealed_unassigned_and_nonoperational() -> None:
    value = load("humor-mechanics-batch2-development-pilot03-preingestion-v1.json")
    identity = value.pop("preingestion_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT03_PREINGESTION_V1", value)
    assert value["status"] == "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED"
    assert value["validation_identity"] == "75b72885baa849206d1d1f17ed9fc1d0227c84dd2e84bdaf90ccba13648f4ad7"
    assert value["target_mechanism"] == "UNASSIGNED"
    assert value["operational_obligation"] == "UNASSIGNED"
    assert value["family_identities"]["creative_premise_family_id"] == "UNASSIGNED"
    assert not value["ingested"] and not value["archive_write"] and not value["git_archival"]
    assert not value["g01a_admitted"] and not value["g01b_admitted"]
    assert not any(value["authority_matrix"].values())


def test_seven_propositions_rederive_character_byte_and_hash_bindings() -> None:
    value = load("humor-mechanics-batch2-development-pilot03-preingestion-v1.json")
    source = SOURCE.read_bytes()
    text = source.decode("utf-8")
    propositions = value["factual_authority_envelope"]["propositions"]
    assert [item["proposition_id"] for item in propositions] == [f"P{i}" for i in range(1, 8)]
    for item in propositions:
        for component_name in ("supporting_span", "subject", "predicate", "object"):
            component = item[component_name]
            char_start, char_end = component["character_coordinates"]
            byte_start, byte_end = component["utf8_byte_coordinates"]
            assert text[char_start:char_end].encode("utf-8") == source[byte_start:byte_end]
            expected = component.get("span_sha256", component.get("sha256"))
            assert hashlib.sha256(source[byte_start:byte_end]).hexdigest() == expected
        if item["qualification"]:
            component = item["qualification"]
            char_start, char_end = component["character_coordinates"]
            byte_start, byte_end = component["utf8_byte_coordinates"]
            assert text[char_start:char_end].encode("utf-8") == source[byte_start:byte_end]
            assert hashlib.sha256(source[byte_start:byte_end]).hexdigest() == component["sha256"]


def test_family_independence_is_sealed_against_both_prior_pilots() -> None:
    value = load("humor-mechanics-batch2-development-pilot03-family-independence-v1.json")
    identity = value.pop("family_independence_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT03_FAMILY_INDEPENDENCE_V1", value)
    assert value["result"] == "PASS_FRESH_FAMILY_INDEPENDENCE"
    assert len(value["prior_source_sha256"]) == 2
    assert value["source_hash_distinct"] and value["git_blob_distinct"]
    assert value["exact_prior_line_reuse"] is False
    assert value["source_event_topic_revision_sibling_syndication_same_event_relation"] is False
    assert value["selected_or_shaped_using_governance_obligation_target_gap_or_prior_candidate"] is False
    assert value["blind_family_access"] is False


def test_unsigned_packet_has_exact_eight_requests_current_head_and_unique_nonces() -> None:
    packet = load("humor-mechanics-batch2-development-pilot03-signing-packet-v1.json")
    assert packet["packet_identity"] == seal("B2_DEVELOPMENT_PILOT03_SIGNING_PACKET_V1", packet["packet_core"])
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
    assert [(item["operation_ordinal"], item["purpose"], item["role"]) for item in packet["signature_requests"]] == expected
    nonces: set[str] = set()
    for request in packet["signature_requests"]:
        challenge = request["challenge"]
        core = {key: value for key, value in challenge.items() if key != "challenge_identity"}
        assert challenge["challenge_identity"] == seal("B2_PILOT03_SIGNING_CHALLENGE_V1", core)
        assert challenge["prior_ledger_head"] == "bb530d7a11f32d76b21f3e12695abb5f05219847b96a82c5a911211c8126e460"
        assert challenge["grants_operational_content_access"] is False
        assert challenge["nonce"] not in nonces
        nonces.add(challenge["nonce"])

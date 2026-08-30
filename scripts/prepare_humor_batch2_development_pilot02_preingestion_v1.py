"""Derive Pilot 02 prospective identities and freeze an unsigned signing packet."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot02-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot02-v1.json"
SOURCE_SHA = "be9853603f82bc1fd11b2d0e06a692b3db4b83d1a7e20733c203c5aea1a04ea8"
DECLARATION_SHA = "1791250d9e17c718b48f93c8354afe120fedce0821e0021b4423d88f89416929"
LEDGER_HEAD = "86aa81e1ba197d0ff7b4fe19bc7fa90773e7ded7596839d7d76ee5cdd74ae254"
REGISTRATION_ID = "01912e139471ec23cba5861c8f575f098a6248d39ebbe5ec2ee043493d392ebe"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def blob_oid(value: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest()


def component(source: str, spans: list[tuple[int, int]], start: int, end: int) -> dict[str, Any]:
    char_start, char_end = spans[start][0], spans[end - 1][1]
    raw = source[char_start:char_end].encode("utf-8")
    return {"character_coordinates": [char_start, char_end], "utf8_byte_coordinates": [len(source[:char_start].encode("utf-8")), len(source[:char_end].encode("utf-8"))], "sha256": sha(raw)}


def proposition(identifier: str, source: str, start: int, end: int, subject: tuple[int, int], predicate: tuple[int, int], obj: tuple[int, int], qualification: tuple[int, int] | None = None, time: str = "UNSPECIFIED") -> dict[str, Any]:
    surface = source[start:end]
    spans = [(start + m.start(), start + m.end()) for m in re.finditer(r"\S+", surface)]
    record = {
        "proposition_id": identifier,
        "supporting_span": {"character_coordinates": [start, end], "utf8_byte_coordinates": [len(source[:start].encode("utf-8")), len(source[:end].encode("utf-8"))], "span_sha256": sha(surface.encode("utf-8"))},
        "subject": component(source, spans, *subject), "predicate": component(source, spans, *predicate), "object": component(source, spans, *obj),
        "modality": "ASSERTED", "qualification": component(source, spans, *qualification) if qualification else None,
        "time": time, "scope": "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "attribution": "OWNER_AUTHORED_SOURCE",
        "known_boundary": "ONLY_THE_EXACT_BOUND_PROPOSITION", "unknown_boundary": "ALL_UNSTATED_PROPERTIES_CAUSES_PREFERENCES_RESULTS_AND_REAL_WORLD_APPLICABILITY",
        "prohibited_inferences": ["NO_REAL_WORLD_ASSERTION", "NO_UNSTATED_CAUSAL_INFERENCE", "NO_UNSTATED_PREFERENCE_OR_WINNER_INFERENCE", "NO_UNSTATED_PERSON_INTENT_OR_INTERNAL_STATE_INFERENCE"],
        "quotation_status": "OWNER_AUTHORED_NOT_THIRD_PARTY_QUOTATION", "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC",
    }
    return record


def main() -> None:
    outputs = [
        ART / "humor-mechanics-batch2-development-pilot02-preingestion-v1.json",
        ART / "humor-mechanics-batch2-development-pilot02-family-independence-v1.json",
        ART / "humor-mechanics-batch2-development-pilot02-signing-packet-v1.json",
    ]
    if any(path.exists() for path in outputs):
        raise SystemExit("Pilot 02 prospective preparation already frozen")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    assert sha(source_bytes) == SOURCE_SHA and sha(declaration_bytes) == DECLARATION_SHA
    assert not source_bytes.startswith(b"\xef\xbb\xbf") and b"\r" not in source_bytes and source_bytes.endswith(b"\n") and not source_bytes.endswith(b"\n\n")
    source = source_bytes.decode("utf-8")
    declaration = json.loads(declaration_bytes)
    assert declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-02"
    assert declaration["owner_instruction"]["requested_action"] == "PREINGESTION_VALIDATION_ONLY"
    assert not any(declaration["independent_grants"][key] for key in ("model_exposure", "training", "runtime_integration", "production_routing"))
    lines = source.splitlines(keepends=True)
    assert len(lines) == 6
    starts: list[int] = []
    cursor = 0
    for line in lines:
        starts.append(cursor)
        cursor += len(line)
    ends = [starts[i] + len(lines[i].rstrip("\n")) for i in range(6)]
    line3 = lines[2].rstrip("\n")
    split = line3.index(", iar ")
    p3_end = starts[2] + split
    p4_start = p3_end + len(", iar ")
    propositions = [
        proposition("P1", source, starts[0], ends[0], (0, 2), (2, 3), (3, 12)),
        proposition("P2", source, starts[1], ends[1], (0, 1), (1, 3), (3, 18), (3, 12), "EXPLICIT_2026_09_04_11_30_TO_13_00_BEFORE_PUBLIC_OPENING"),
        proposition("P3", source, starts[2], p3_end, (3, 7), (2, 3), (0, 2)),
        proposition("P4", source, p4_start, ends[2], (0, 2), (2, 4), (4, 10)),
        proposition("P5", source, starts[3], ends[3], (0, 1), (1, 3), (3, 11)),
        proposition("P6", source, starts[4], ends[4], (3, 4), (4, 6), (6, 10), (0, 3), "AT_END_OF_TASTING_WITH_LATER_EVALUATION_UNSCHEDULED"),
        proposition("P7", source, starts[5], ends[5], (7, 9), (4, 7), (9, 10), (0, 4), "AT_TEST_END"),
    ]
    source_meta = declaration["source"]
    source_commitment = seal("B2_OWNED_SOURCE_COMMITMENT_V1", {"sha256": SOURCE_SHA, "byte_length": len(source_bytes), "encoding": "UTF-8", "source_version": source_meta["source_version"], "capture_timestamp": source_meta["capture_timestamp"]})
    rights_identity = seal("B2_INTERNALLY_OWNED_RIGHTS_INSTRUMENT_PROSPECTIVE_V1", {"declaration_sha256": DECLARATION_SHA, "owner_identity": declaration["contributor"]["public_identity"], "grants": declaration["independent_grants"], "rights_terms": declaration["rights_terms"]})
    envelope = {"source_commitment": source_commitment, "source_sha256": SOURCE_SHA, "world_scope": source_meta["world_scope"], "authority_scope": source_meta["authority_scope"], "propositions": propositions, "creative_premise_family_id": "UNASSIGNED"}
    envelope_identity = seal("B2_FACTUAL_AUTHORITY_ENVELOPE_PROSPECTIVE_V1", envelope)
    source_blob = blob_oid(source_bytes)
    archive_commitment = seal("B2_IMMUTABLE_ARCHIVE_COMMITMENT_PROSPECTIVE_V1", {"source_commitment": source_commitment, "source_sha256": SOURCE_SHA, "byte_length": len(source_bytes), "prospective_git_blob_oid_sha1": source_blob, "write_status": "NOT_WRITTEN"})
    independence_core = {
        "schema_name": "batch2-development-pilot02-family-independence-v1", "schema_version": "1.0.0",
        "pilot02_source_sha256": SOURCE_SHA, "pilot01_source_sha256": "84261f1a6b97f951f70a1b86d42114da9703996607d43d2fc3779bffd7a97cb2",
        "pilot02_topology": ["BOUNDED_TASTING_EVENT", "PARTICIPANT_COUNT", "STANDARDIZED_PREPARATION", "MULTIDIMENSIONAL_OBSERVATIONS", "DEFERRED_EVALUATION", "NO_WINNER_AT_END"],
        "pilot01_topology": ["LABELED_STORAGE_ENTITIES", "INVENTORY_QUANTITIES", "REPEATED_CHECKS", "BETWEEN_CHECKS_INVARIANT"],
        "source_hash_distinct": True, "git_blob_distinct": source_blob != "c3a3316a2fc6be4befa40c1f777c09ecc2b48b6f",
        "source_event_topic_revision_sibling_same_event_relation": False, "prior_target_or_obligation_assignment": False,
        "prior_construction_or_model_exposure": False, "blind_family_access": False,
        "selected_using_successor_obligation_or_target_friendly_shape": False, "result": "PASS_FRESH_FAMILY_INDEPENDENCE",
    }
    independence = {**independence_core, "family_independence_identity": seal("B2_DEVELOPMENT_PILOT02_FAMILY_INDEPENDENCE_V1", independence_core)}
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {"pilot_id": declaration["pilot_id"], "event_class": "OWNER_AUTHORED_SYNTHETIC_INTERNAL_TASTING"})
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {"rights_identity": rights_identity, "authority_envelope_identity": envelope_identity})
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {"subject_class": source_meta["subject_class"], "topic_entity_class": "SYNTHETIC_CAFE_TASTING_AND_EVALUATION"})
    revision_family = seal("B2_REVISION_FAMILY_V1", {"source_family": source_family, "source_version": source_meta["source_version"], "supersedes": None})
    family_closure = seal("B2_FAMILY_CLOSURE_PROSPECTIVE_V1", {"source": source_family, "event": event_family, "authority": authority_family, "topic_entity": topic_family, "revision": revision_family, "family_independence_identity": independence["family_independence_identity"], "creative_premise": "UNASSIGNED"})
    partition_identity = seal("B2_DEVELOPMENT_PARTITION_SEAL_PROSPECTIVE_V1", {"family_closure": family_closure, "partition": "DEVELOPMENT", "curriculum_candidate": False, "blind_evaluation": False})
    source_package_identity = seal("B2_SOURCE_PACKAGE_PROSPECTIVE_V1", {"source_commitment": source_commitment, "archive_commitment": archive_commitment, "rights_identity": rights_identity, "authority_envelope_identity": envelope_identity, "family_closure": family_closure, "partition_identity": partition_identity, "status": "NOT_INGESTED_NOT_ARCHIVED"})
    prospective_core = {
        "schema_name": "batch2-development-pilot02-preingestion-v1", "schema_version": "1.0.0",
        "status": "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED", "source_sha256": SOURCE_SHA, "source_byte_length": len(source_bytes), "declaration_sha256": DECLARATION_SHA,
        "source_commitment": source_commitment, "rights_instrument_identity": rights_identity, "immutable_archive_commitment": archive_commitment,
        "prospective_git_blob_oid_sha1": source_blob, "source_package_identity": source_package_identity,
        "factual_authority_envelope": envelope, "factual_authority_envelope_identity": envelope_identity,
        "family_independence_identity": independence["family_independence_identity"],
        "family_identities": {"source_family": source_family, "event_family": event_family, "authority_family": authority_family, "topic_entity_family": topic_family, "revision_family": revision_family, "family_closure": family_closure, "creative_premise_family_id": "UNASSIGNED"},
        "partition": "DEVELOPMENT", "prospective_partition_identity": partition_identity,
        "target_mechanism": "UNASSIGNED", "operational_obligation": "UNASSIGNED",
        "archive_write": False, "git_archival": False, "ingested": False, "g01a_admitted": False, "g01b_admitted": False,
        "authority_matrix": {key: False for key in ("custodial_signing", "immutable_ingestion", "archive_write", "g01a_admission", "g01b_admission", "mechanism_assignment", "obligation_assignment", "creative_premise_assignment", "construction", "generation", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    prospective = {**prospective_core, "preingestion_identity": seal("B2_DEVELOPMENT_PILOT02_PREINGESTION_V1", prospective_core)}
    operations = [
        ("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"], rights_identity),
        ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], source_package_identity),
        ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], archive_commitment),
        ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"], family_closure),
        ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"], partition_identity),
        ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"], prospective["preingestion_identity"]),
    ]
    op_records = [{"ordinal": i, "purpose": purpose, "object_identity": obj, "required_signer_roles": roles, "distinct_signers_required": len(roles) > 1} for i, (purpose, roles, obj) in enumerate(operations)]
    packet_core = {"preingestion_identity": prospective["preingestion_identity"], "source_sha256": SOURCE_SHA, "declaration_sha256": DECLARATION_SHA, "registration_identity": REGISTRATION_ID, "prior_ledger_head": LEDGER_HEAD, "operations": op_records, "atomic": True}
    packet_identity = seal("B2_DEVELOPMENT_PILOT02_SIGNING_PACKET_V1", packet_core)
    registration = json.loads((ART / "humor-mechanics-batch2-custodial-public-key-registration-v1.json").read_text(encoding="utf-8"))
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    requests = []
    for operation in op_records:
        for role in operation["required_signer_roles"]:
            challenge_core = {"domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT02_PREINGESTION_V1", "purpose": operation["purpose"], "role": role, "principal_identity": principals[role], "object_identity": operation["object_identity"], "packet_identity": packet_identity, "source_sha256": SOURCE_SHA, "declaration_sha256": DECLARATION_SHA, "preingestion_identity": prospective["preingestion_identity"], "nonce": seal("B2_PILOT02_SIGNING_NONCE_V1", {"packet": packet_identity, "ordinal": operation["ordinal"], "role": role}), "prior_ledger_head": LEDGER_HEAD, "grants_operational_content_access": False}
            challenge = {**challenge_core, "challenge_identity": seal("B2_PILOT02_SIGNING_CHALLENGE_V1", challenge_core)}
            requests.append({"operation_ordinal": operation["ordinal"], "purpose": operation["purpose"], "role": role, "challenge": challenge, "signature_status": "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION"})
    packet = {"schema_name": "batch2-development-pilot02-custodial-signing-packet-v1", "schema_version": "1.0.0", "packet_core": packet_core, "packet_identity": packet_identity, "signature_requests": requests, "status": "UNSIGNED", "signatures_present": 0, "source_ingested": False, "archive_written": False, "ledger_events_appended": 0}
    for path, value in zip(outputs, (prospective, independence, packet), strict=True):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"preparation_verdict": "PASS_UNSIGNED_PREPARATION", "preingestion_identity": prospective["preingestion_identity"], "source_commitment": source_commitment, "rights_identity": rights_identity, "archive_commitment": archive_commitment, "source_package_identity": source_package_identity, "authority_envelope_identity": envelope_identity, "family_independence_identity": independence["family_independence_identity"], "family_closure": family_closure, "partition_identity": partition_identity, "signing_packet_identity": packet_identity, "signature_requests": len(requests)}, sort_keys=True))


if __name__ == "__main__":
    main()

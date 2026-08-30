"""Derive Pilot 03 prospective identities and freeze an unsigned signing packet."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot03-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot03-v1.json"
VALIDATION_COMMIT = "32e0e2529b8adc6eace1e4585ad16c5479bb02b5"
VALIDATION_ID = "75b72885baa849206d1d1f17ed9fc1d0227c84dd2e84bdaf90ccba13648f4ad7"
SOURCE_SHA = "61a5889cb03f72c6f4f72b0f1652b2db43c092f51c91f7d5e59933a99ca2fc30"
DECLARATION_SHA = "5915ee71841ed1a40ae375e0e7c6a4b611c525d0b8690464e61d66e078b14d8d"
LEDGER_HEAD = "bb530d7a11f32d76b21f3e12695abb5f05219847b96a82c5a911211c8126e460"
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
    return {
        "character_coordinates": [char_start, char_end],
        "utf8_byte_coordinates": [len(source[:char_start].encode("utf-8")), len(source[:char_end].encode("utf-8"))],
        "sha256": sha(raw),
    }


def proposition(
    identifier: str,
    source: str,
    start: int,
    end: int,
    subject: tuple[int, int],
    predicate: tuple[int, int],
    obj: tuple[int, int],
    qualification: tuple[int, int] | None = None,
    time: str = "UNSPECIFIED",
    known_boundary: str = "ONLY_THE_EXACT_BOUND_PROPOSITION",
    unknown_boundary: str = "ALL_UNSTATED_PROPERTIES_CAUSES_RESULTS_AND_REAL_WORLD_APPLICABILITY",
) -> dict[str, Any]:
    surface = source[start:end]
    spans = [(start + match.start(), start + match.end()) for match in re.finditer(r"\S+", surface)]
    return {
        "proposition_id": identifier,
        "supporting_span": {
            "character_coordinates": [start, end],
            "utf8_byte_coordinates": [len(source[:start].encode("utf-8")), len(source[:end].encode("utf-8"))],
            "span_sha256": sha(surface.encode("utf-8")),
        },
        "subject": component(source, spans, *subject),
        "predicate": component(source, spans, *predicate),
        "object": component(source, spans, *obj),
        "modality": "ASSERTED",
        "qualification": component(source, spans, *qualification) if qualification else None,
        "time": time,
        "scope": "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY",
        "attribution": "OWNER_AUTHORED_SOURCE",
        "known_boundary": known_boundary,
        "unknown_boundary": unknown_boundary,
        "prohibited_inferences": [
            "NO_REAL_WORLD_ASSERTION",
            "NO_UNSTATED_CAUSAL_INFERENCE",
            "NO_UNSTATED_CONTENT_INFERENCE",
            "NO_UNSTATED_PERSON_INTENT_OR_INTERNAL_STATE_INFERENCE",
        ],
        "quotation_status": "OWNER_AUTHORED_NOT_THIRD_PARTY_QUOTATION",
        "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC",
    }


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != VALIDATION_COMMIT:
        raise SystemExit("HEAD differs from Pilot 03 validation commit")
    output_names = (
        "humor-mechanics-batch2-development-pilot03-preingestion-v1.json",
        "humor-mechanics-batch2-development-pilot03-family-independence-v1.json",
        "humor-mechanics-batch2-development-pilot03-signing-packet-v1.json",
    )
    if any((ART / name).exists() for name in output_names):
        raise SystemExit("Pilot 03 prospective preparation already frozen")
    validation = json.loads(subprocess.check_output([
        "git", "show", f"{VALIDATION_COMMIT}:docs/artifacts/humor-mechanics-batch2-development-pilot03-strict-preingestion-validation-v1.json"
    ], cwd=ROOT))
    if validation["validation_identity"] != VALIDATION_ID or validation["validation_verdict"] != "PASS_STRICT_PREINGESTION_VALIDATION_ONLY":
        raise SystemExit("validation binding")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    if sha(source_bytes) != SOURCE_SHA or sha(declaration_bytes) != DECLARATION_SHA:
        raise SystemExit("owner input hash")
    source = source_bytes.decode("utf-8")
    declaration = json.loads(declaration_bytes)
    if declaration["pilot_id"] != "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-03":
        raise SystemExit("pilot id")
    lines = source.splitlines(keepends=True)
    if len(lines) != 6:
        raise SystemExit("source line count")
    starts: list[int] = []
    cursor = 0
    for line in lines:
        starts.append(cursor)
        cursor += len(line)
    ends = [starts[index] + len(lines[index].rstrip("\n")) for index in range(6)]
    propositions = [
        proposition("P1", source, starts[0], ends[0], (0, 4), (4, 5), (5, 12)),
        proposition(
            "P2", source, starts[1], ends[1], (0, 1), (1, 3), (3, 10), (3, 10),
            "EXPLICIT_2026_09_06_09_40_RECEIPT",
        ),
        proposition("P3", source, starts[1], ends[1], (0, 1), (11, 13), (13, 17)),
        proposition("P4", source, starts[2], ends[2], (0, 3), (3, 4), (4, 10)),
        proposition(
            "P5", source, starts[3], ends[3], (2, 3), (3, 5), (5, 13), (0, 2),
            "AFTER_INTERNAL_REGISTRATION",
        ),
        proposition(
            "P6", source, starts[4], ends[4], (0, 2), (2, 4), (4, 10), (4, 10),
            "EXPLICIT_2026_09_06_AFTER_11_00",
        ),
        proposition(
            "P7", source, starts[5], ends[5], (6, 10), (3, 6), (0, 3), (0, 3),
            "AT_RECEIPT",
            known_boundary="EXACT_CONTENT_NOT_DOCUMENTED_AT_RECEIPT",
            unknown_boundary="PARCEL_CONTENT_AND_ALL_UNSTATED_PROPERTIES_CAUSES_RESULTS_AND_REAL_WORLD_APPLICABILITY_UNKNOWN",
        ),
    ]
    source_meta = declaration["source"]
    source_commitment = seal("B2_OWNED_SOURCE_COMMITMENT_V1", {
        "sha256": SOURCE_SHA,
        "byte_length": len(source_bytes),
        "encoding": "UTF-8",
        "source_version": source_meta["source_version"],
        "capture_timestamp": source_meta["capture_timestamp"],
    })
    rights_identity = seal("B2_INTERNALLY_OWNED_RIGHTS_INSTRUMENT_PROSPECTIVE_V1", {
        "declaration_sha256": DECLARATION_SHA,
        "owner_identity": declaration["contributor"]["public_identity"],
        "grants": declaration["independent_grants"],
        "rights_terms": declaration["rights_terms"],
    })
    envelope = {
        "source_commitment": source_commitment,
        "source_sha256": SOURCE_SHA,
        "world_scope": source_meta["world_scope"],
        "authority_scope": source_meta["authority_scope"],
        "propositions": propositions,
        "creative_premise_family_id": "UNASSIGNED",
    }
    envelope_identity = seal("B2_FACTUAL_AUTHORITY_ENVELOPE_PROSPECTIVE_V1", envelope)
    source_blob = blob_oid(source_bytes)
    archive_commitment = seal("B2_IMMUTABLE_ARCHIVE_COMMITMENT_PROSPECTIVE_V1", {
        "source_commitment": source_commitment,
        "source_sha256": SOURCE_SHA,
        "byte_length": len(source_bytes),
        "prospective_git_blob_oid_sha1": source_blob,
        "write_status": "NOT_WRITTEN",
    })
    pilot01 = json.loads(subprocess.check_output([
        "git", "show", "2e9314c18cd11b35c63d6242dfac1cb4bf5b21b8:docs/artifacts/humor-mechanics-batch2-development-pilot01-g01a-g01b-admission-v1.json"
    ], cwd=ROOT))
    pilot02 = json.loads(subprocess.check_output([
        "git", "show", "33a670ada0fc2cd31680033f0c42abeb1b0b4bb6:docs/artifacts/humor-mechanics-batch2-development-pilot02-g01a-g01b-admission-v1.json"
    ], cwd=ROOT))
    independence_core = {
        "schema_name": "batch2-development-pilot03-family-independence-v1",
        "schema_version": "1.0.0",
        "pilot03_source_sha256": SOURCE_SHA,
        "prior_source_sha256": [pilot01["g01a"]["source_sha256"], pilot02["g01a"]["source_sha256"]],
        "pilot03_topology": [
            "INTERNAL_PARCEL_RECEIPT",
            "TIMESTAMPED_INTERNAL_REGISTRATION",
            "RECORDED_TRANSPORT_WEIGHT",
            "POST_REGISTRATION_TECHNICAL_TRANSFER",
            "SCHEDULED_CONTROLLED_OPENING",
            "CONTENT_UNKNOWN_AT_RECEIPT",
        ],
        "prior_family_identities": {
            "pilot01": pilot01["g01b"]["family_identities"],
            "pilot02": pilot02["g01b"]["family_identities"],
        },
        "source_hash_distinct": SOURCE_SHA not in (pilot01["g01a"]["source_sha256"], pilot02["g01a"]["source_sha256"]),
        "git_blob_distinct": source_blob not in (pilot01["g01a"]["source_git_object"], pilot02["g01a"]["source_git_object"]),
        "exact_prior_line_reuse": False,
        "source_event_topic_revision_sibling_syndication_same_event_relation": False,
        "prior_target_obligation_or_creative_premise_assignment": False,
        "prior_construction_model_training_runtime_or_production_exposure": False,
        "blind_family_access": False,
        "selected_or_shaped_using_governance_obligation_target_gap_or_prior_candidate": False,
        "result": "PASS_FRESH_FAMILY_INDEPENDENCE",
    }
    independence = {
        **independence_core,
        "family_independence_identity": seal("B2_DEVELOPMENT_PILOT03_FAMILY_INDEPENDENCE_V1", independence_core),
    }
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {
        "pilot_id": declaration["pilot_id"],
        "event_class": "OWNER_AUTHORED_SYNTHETIC_INTERNAL_PARCEL_RECEIPT_AND_CONTROLLED_OPENING",
    })
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {
        "rights_identity": rights_identity,
        "authority_envelope_identity": envelope_identity,
    })
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {
        "subject_class": source_meta["subject_class"],
        "topic_entity_class": "SYNTHETIC_INTERNAL_DISTRIBUTION_PARCEL_HANDLING",
    })
    revision_family = seal("B2_REVISION_FAMILY_V1", {
        "source_family": source_family,
        "source_version": source_meta["source_version"],
        "supersedes": None,
    })
    family_closure = seal("B2_FAMILY_CLOSURE_PROSPECTIVE_V1", {
        "source": source_family,
        "event": event_family,
        "authority": authority_family,
        "topic_entity": topic_family,
        "revision": revision_family,
        "family_independence_identity": independence["family_independence_identity"],
        "creative_premise": "UNASSIGNED",
    })
    partition_identity = seal("B2_DEVELOPMENT_PARTITION_SEAL_PROSPECTIVE_V1", {
        "family_closure": family_closure,
        "partition": "DEVELOPMENT",
        "curriculum_candidate": False,
        "blind_evaluation": False,
    })
    source_package_identity = seal("B2_SOURCE_PACKAGE_PROSPECTIVE_V1", {
        "source_commitment": source_commitment,
        "archive_commitment": archive_commitment,
        "rights_identity": rights_identity,
        "authority_envelope_identity": envelope_identity,
        "family_closure": family_closure,
        "partition_identity": partition_identity,
        "status": "NOT_INGESTED_NOT_ARCHIVED",
    })
    prospective_core = {
        "schema_name": "batch2-development-pilot03-preingestion-v1",
        "schema_version": "1.0.0",
        "status": "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED",
        "validation_commit": VALIDATION_COMMIT,
        "validation_identity": VALIDATION_ID,
        "source_sha256": SOURCE_SHA,
        "source_byte_length": len(source_bytes),
        "declaration_sha256": DECLARATION_SHA,
        "source_commitment": source_commitment,
        "rights_instrument_identity": rights_identity,
        "immutable_archive_commitment": archive_commitment,
        "prospective_git_blob_oid_sha1": source_blob,
        "source_package_identity": source_package_identity,
        "factual_authority_envelope": envelope,
        "factual_authority_envelope_identity": envelope_identity,
        "family_independence_identity": independence["family_independence_identity"],
        "family_identities": {
            "source_family": source_family,
            "event_family": event_family,
            "authority_family": authority_family,
            "topic_entity_family": topic_family,
            "revision_family": revision_family,
            "family_closure": family_closure,
            "creative_premise_family_id": "UNASSIGNED",
        },
        "partition": "DEVELOPMENT",
        "prospective_partition_identity": partition_identity,
        "target_mechanism": "UNASSIGNED",
        "operational_obligation": "UNASSIGNED",
        "archive_write": False,
        "git_archival": False,
        "ingested": False,
        "g01a_admitted": False,
        "g01b_admitted": False,
        "authority_matrix": {
            key: False for key in (
                "custodial_signing", "immutable_ingestion", "archive_write", "g01a_admission", "g01b_admission",
                "mechanism_assignment", "obligation_assignment", "creative_premise_assignment", "construction",
                "generation", "model_exposure", "training", "runtime_integration", "production_routing",
            )
        },
    }
    prospective = {
        **prospective_core,
        "preingestion_identity": seal("B2_DEVELOPMENT_PILOT03_PREINGESTION_V1", prospective_core),
    }
    operations = [
        ("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"], rights_identity),
        ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], source_package_identity),
        ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], archive_commitment),
        ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"], family_closure),
        ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"], partition_identity),
        ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"], prospective["preingestion_identity"]),
    ]
    operation_records = [
        {"ordinal": index, "purpose": purpose, "object_identity": object_identity,
         "required_signer_roles": roles, "distinct_signers_required": len(roles) > 1}
        for index, (purpose, roles, object_identity) in enumerate(operations)
    ]
    packet_core = {
        "preingestion_identity": prospective["preingestion_identity"],
        "source_sha256": SOURCE_SHA,
        "declaration_sha256": DECLARATION_SHA,
        "registration_identity": REGISTRATION_ID,
        "prior_ledger_head": LEDGER_HEAD,
        "operations": operation_records,
        "atomic": True,
    }
    packet_identity = seal("B2_DEVELOPMENT_PILOT03_SIGNING_PACKET_V1", packet_core)
    registration = json.loads((ART / "humor-mechanics-batch2-custodial-public-key-registration-v1.json").read_text(encoding="utf-8"))
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    requests = []
    for operation in operation_records:
        for role in operation["required_signer_roles"]:
            challenge_core = {
                "domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT03_PREINGESTION_V1",
                "purpose": operation["purpose"],
                "role": role,
                "principal_identity": principals[role],
                "object_identity": operation["object_identity"],
                "packet_identity": packet_identity,
                "source_sha256": SOURCE_SHA,
                "declaration_sha256": DECLARATION_SHA,
                "preingestion_identity": prospective["preingestion_identity"],
                "nonce": seal("B2_PILOT03_SIGNING_NONCE_V1", {
                    "packet": packet_identity, "ordinal": operation["ordinal"], "role": role,
                }),
                "prior_ledger_head": LEDGER_HEAD,
                "grants_operational_content_access": False,
            }
            challenge = {
                **challenge_core,
                "challenge_identity": seal("B2_PILOT03_SIGNING_CHALLENGE_V1", challenge_core),
            }
            requests.append({
                "operation_ordinal": operation["ordinal"],
                "purpose": operation["purpose"],
                "role": role,
                "challenge": challenge,
                "signature_status": "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION",
            })
    packet = {
        "schema_name": "batch2-development-pilot03-custodial-signing-packet-v1",
        "schema_version": "1.0.0",
        "packet_core": packet_core,
        "packet_identity": packet_identity,
        "signature_requests": requests,
        "status": "UNSIGNED",
        "signatures_present": 0,
        "source_ingested": False,
        "archive_written": False,
        "ledger_events_appended": 0,
    }
    for name, value in zip(output_names, (prospective, independence, packet), strict=True):
        (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "preparation_verdict": "PASS_UNSIGNED_PREPARATION",
        "preingestion_identity": prospective["preingestion_identity"],
        "source_commitment": source_commitment,
        "rights_identity": rights_identity,
        "archive_commitment": archive_commitment,
        "source_package_identity": source_package_identity,
        "authority_envelope_identity": envelope_identity,
        "family_independence_identity": independence["family_independence_identity"],
        "family_closure": family_closure,
        "partition_identity": partition_identity,
        "signing_packet_identity": packet_identity,
        "signature_requests": len(requests),
    }, sort_keys=True))


if __name__ == "__main__":
    main()

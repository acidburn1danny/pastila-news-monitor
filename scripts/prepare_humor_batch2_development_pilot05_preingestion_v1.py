"""Derive Pilot 05 prospective identities and freeze an unsigned signing packet."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot05-v1.txt"
DECLARATION = ART / "humor-mechanics-batch2-development-pilot05-owner-declaration-canonical-v1.json"
VALIDATION_COMMIT = "c48c97858a480a13a4064b85d67b7bb716e30b2d"
VALIDATION_ID = "42845c8ad8560e47a91383e1f27a8ca92ce532ab74566540e437ea4911600d3e"
SOURCE_SHA = "e3404a694bf1203f8a11ceeed0e682511882237e4777bd0e092876994c4326cc"
DECLARATION_SHA = "69e207463fcb8d31e0ccaf99db46192bd577997dfb4b1d3658a5f955fb148e25"
LEDGER_HEAD = "3a172491ec99d5f8c0ef2d4be075912b5518f6b42bb19641bd60ab9b20d26fd4"
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
    return {"character_coordinates": [char_start, char_end], "utf8_byte_coordinates": [len(source[:char_start].encode()), len(source[:char_end].encode())], "sha256": sha(raw)}


def proposition(identifier: str, source: str, start: int, end: int, subject: tuple[int, int], predicate: tuple[int, int], obj: tuple[int, int], qualification: tuple[int, int] | None = None, time: str = "UNSPECIFIED", known: str = "ONLY_THE_EXACT_BOUND_PROPOSITION", unknown: str = "ALL_UNSTATED_PROPERTIES_CAUSES_RESULTS_AND_REAL_WORLD_APPLICABILITY") -> dict[str, Any]:
    surface = source[start:end]
    spans = [(start + match.start(), start + match.end()) for match in re.finditer(r"\S+", surface)]
    return {
        "proposition_id": identifier,
        "supporting_span": {"character_coordinates": [start, end], "utf8_byte_coordinates": [len(source[:start].encode()), len(source[:end].encode())], "span_sha256": sha(surface.encode())},
        "subject": component(source, spans, *subject), "predicate": component(source, spans, *predicate), "object": component(source, spans, *obj),
        "modality": "ASSERTED", "qualification": component(source, spans, *qualification) if qualification else None,
        "time": time, "scope": "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "attribution": "OWNER_AUTHORED_SOURCE",
        "known_boundary": known, "unknown_boundary": unknown,
        "prohibited_inferences": ["NO_REAL_WORLD_ASSERTION", "NO_UNSTATED_CAUSAL_INFERENCE", "NO_UNSTATED_PERSON_INTENT_OR_INTERNAL_STATE_INFERENCE", "NO_UNSTATED_ATTENDANCE_OR_DEMAND_INFERENCE"],
        "quotation_status": "OWNER_AUTHORED_NOT_THIRD_PARTY_QUOTATION", "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC",
    }


def git_json(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != VALIDATION_COMMIT:
        raise SystemExit("HEAD differs from Pilot 05 validation commit")
    names = ("humor-mechanics-batch2-development-pilot05-preingestion-v1.json", "humor-mechanics-batch2-development-pilot05-family-independence-v1.json", "humor-mechanics-batch2-development-pilot05-signing-packet-v1.json")
    if any((ART / name).exists() for name in names):
        raise SystemExit("Pilot 05 prospective preparation already frozen")
    validation = git_json(VALIDATION_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot05-strict-preingestion-validation-v1.json")
    if validation["validation_identity"] != VALIDATION_ID or validation["validation_verdict"] != "PASS_STRICT_PREINGESTION_VALIDATION_ONLY":
        raise SystemExit("validation binding")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    if sha(source_bytes) != SOURCE_SHA or sha(declaration_bytes) != DECLARATION_SHA:
        raise SystemExit("owner input hash")
    source, declaration = source_bytes.decode("utf-8"), json.loads(declaration_bytes)
    lines = source.splitlines(keepends=True)
    if len(lines) != 6 or declaration["pilot_id"] != "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-05":
        raise SystemExit("source/declaration shape")
    starts, cursor = [], 0
    for line in lines:
        starts.append(cursor); cursor += len(line)
    ends = [starts[i] + len(lines[i].rstrip("\n")) for i in range(6)]
    propositions = [
        proposition("P1", source, starts[0], ends[0], (0, 5), (5, 6), (6, 13), (9, 13)),
        proposition("P2", source, starts[1], ends[1], (4, 5), (5, 8), (8, 15), (0, 4), "EXPLICIT_2026_09_10"),
        proposition("P3", source, starts[2], ends[2], (2, 3), (3, 5), (5, 8), (8, 11), "AFTER_THE_STATED_CALIBRATION"),
        proposition("P4", source, starts[3], ends[3], (0, 1), (1, 4), (4, 9)),
        proposition("P5", source, starts[3], ends[3], (10, 11), (11, 14), (14, 17)),
        proposition("P6", source, starts[4], ends[4], (0, 2), (2, 4), (4, 10), None, "THE_STATED_DAY", "EXTERIOR_AIR_TEMPERATURE_NOT_ESTABLISHED", "EXTERIOR_TEMPERATURE_AND_ALL_UNSTATED_PROPERTIES_CAUSES_RESULTS_AND_REAL_WORLD_APPLICABILITY_UNKNOWN"),
        proposition("P7", source, starts[5], ends[5], (3, 6), (0, 3), (3, 6), None, "FUTURE_RECALIBRATION", "NEXT_RECALIBRATION_DATE_NOT_SPECIFIED", "NEXT_RECALIBRATION_DATE_AND_ALL_UNSTATED_PROPERTIES_CAUSES_RESULTS_AND_REAL_WORLD_APPLICABILITY_UNKNOWN"),
    ]
    meta = declaration["source"]
    source_commitment = seal("B2_OWNED_SOURCE_COMMITMENT_V1", {"sha256": SOURCE_SHA, "byte_length": len(source_bytes), "encoding": "UTF-8", "source_version": meta["source_version"], "capture_timestamp": meta["capture_timestamp"]})
    rights_identity = seal("B2_INTERNALLY_OWNED_RIGHTS_INSTRUMENT_PROSPECTIVE_V1", {"declaration_sha256": DECLARATION_SHA, "owner_identity": declaration["contributor"]["public_identity"], "grants": declaration["independent_grants"], "rights_terms": declaration["rights_terms"]})
    envelope = {"source_commitment": source_commitment, "source_sha256": SOURCE_SHA, "world_scope": meta["world_scope"], "authority_scope": meta["authority_scope"], "propositions": propositions, "creative_premise_family_id": "UNASSIGNED"}
    envelope_identity = seal("B2_FACTUAL_AUTHORITY_ENVELOPE_PROSPECTIVE_V1", envelope)
    source_blob = blob_oid(source_bytes)
    archive_commitment = seal("B2_IMMUTABLE_ARCHIVE_COMMITMENT_PROSPECTIVE_V1", {"source_commitment": source_commitment, "source_sha256": SOURCE_SHA, "byte_length": len(source_bytes), "prospective_git_blob_oid_sha1": source_blob, "write_status": "NOT_WRITTEN"})
    admissions = [
        git_json("2e9314c18cd11b35c63d6242dfac1cb4bf5b21b8", "docs/artifacts/humor-mechanics-batch2-development-pilot01-g01a-g01b-admission-v1.json"),
        git_json("33a670ada0fc2cd31680033f0c42abeb1b0b4bb6", "docs/artifacts/humor-mechanics-batch2-development-pilot02-g01a-g01b-admission-v1.json"),
        git_json("ea1397958e96ea5e2c5bd65acb98495bd0dd409b", "docs/artifacts/humor-mechanics-batch2-development-pilot03-g01a-g01b-admission-v1.json"),
        git_json("902d1d06f30924dc66e2190a81590c4359a4b1c7", "docs/artifacts/humor-mechanics-batch2-development-pilot04-g01a-g01b-admission-v1.json"),
    ]
    independence_core = {
        "schema_name": "batch2-development-pilot05-family-independence-v1", "schema_version": "1.0.0", "pilot05_source_sha256": SOURCE_SHA,
        "prior_source_sha256": [item["g01a"]["source_sha256"] for item in admissions], "prior_family_identities": {f"pilot0{i+1}": item["g01b"]["family_identities"] for i, item in enumerate(admissions)},
        "pilot05_topology": ["SYNTHETIC_INTERNAL_WEATHER_STATION", "DIGITAL_SENSOR_CALIBRATION", "REFERENCE_VALUE", "OBSERVED_POST_CALIBRATION_VALUE", "TECHNICAL_LOG_AND_AVAILABILITY", "EXTERIOR_TEMPERATURE_NOT_ESTABLISHED", "NEXT_RECALIBRATION_DATE_UNKNOWN"],
        "source_hash_distinct": SOURCE_SHA not in [item["g01a"]["source_sha256"] for item in admissions], "git_blob_distinct": source_blob not in [item["g01a"]["source_git_object"] for item in admissions],
        "exact_prior_line_reuse": False, "source_event_topic_revision_sibling_syndication_same_event_relation": False,
        "prior_target_obligation_or_creative_premise_assignment": False, "prior_construction_model_training_runtime_or_production_exposure": False,
        "blind_family_access": False, "selected_or_shaped_using_governance_obligation_target_gap_pool_confound_or_prior_candidate": False,
        "result": "PASS_FRESH_FAMILY_INDEPENDENCE",
    }
    independence = {**independence_core, "family_independence_identity": seal("B2_DEVELOPMENT_PILOT05_FAMILY_INDEPENDENCE_V1", independence_core)}
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {"pilot_id": declaration["pilot_id"], "event_class": "OWNER_AUTHORED_SYNTHETIC_SENSOR_CALIBRATION"})
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {"rights_identity": rights_identity, "authority_envelope_identity": envelope_identity})
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {"subject_class": meta["subject_class"], "topic_entity_class": "SYNTHETIC_WEATHER_STATION_SENSOR_CALIBRATION"})
    revision_family = seal("B2_REVISION_FAMILY_V1", {"source_family": source_family, "source_version": meta["source_version"], "supersedes": None})
    family_closure = seal("B2_FAMILY_CLOSURE_PROSPECTIVE_V1", {"source": source_family, "event": event_family, "authority": authority_family, "topic_entity": topic_family, "revision": revision_family, "family_independence_identity": independence["family_independence_identity"], "creative_premise": "UNASSIGNED"})
    partition_identity = seal("B2_DEVELOPMENT_PARTITION_SEAL_PROSPECTIVE_V1", {"family_closure": family_closure, "partition": "DEVELOPMENT", "curriculum_candidate": False, "blind_evaluation": False})
    source_package_identity = seal("B2_SOURCE_PACKAGE_PROSPECTIVE_V1", {"source_commitment": source_commitment, "archive_commitment": archive_commitment, "rights_identity": rights_identity, "authority_envelope_identity": envelope_identity, "family_closure": family_closure, "partition_identity": partition_identity, "status": "NOT_INGESTED_NOT_ARCHIVED"})
    prospective_core = {
        "schema_name": "batch2-development-pilot05-preingestion-v1", "schema_version": "1.0.0", "status": "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED",
        "validation_commit": VALIDATION_COMMIT, "validation_identity": VALIDATION_ID, "source_sha256": SOURCE_SHA, "source_byte_length": len(source_bytes), "declaration_sha256": DECLARATION_SHA,
        "source_commitment": source_commitment, "rights_instrument_identity": rights_identity, "immutable_archive_commitment": archive_commitment, "prospective_git_blob_oid_sha1": source_blob,
        "source_package_identity": source_package_identity, "factual_authority_envelope": envelope, "factual_authority_envelope_identity": envelope_identity, "family_independence_identity": independence["family_independence_identity"],
        "family_identities": {"source_family": source_family, "event_family": event_family, "authority_family": authority_family, "topic_entity_family": topic_family, "revision_family": revision_family, "family_closure": family_closure, "creative_premise_family_id": "UNASSIGNED"},
        "partition": "DEVELOPMENT", "prospective_partition_identity": partition_identity, "target_mechanism": "UNASSIGNED", "operational_obligation": "UNASSIGNED",
        "archive_write": False, "git_archival": False, "ingested": False, "g01a_admitted": False, "g01b_admitted": False, "g04b_pool_certification_performed": False,
        "post_g01_rebalancing_assignment_gate": "REQUIRED_NOT_PERFORMED_DIFFERENT_OBLIGATION_FAMILY_AND_CLOSE_ALTERNATIVE_PROFILE",
        "authority_matrix": {key: False for key in ("custodial_signing", "immutable_ingestion", "archive_write", "g01a_admission", "g01b_admission", "mechanism_assignment", "obligation_assignment", "creative_premise_assignment", "construction", "generation", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    prospective = {**prospective_core, "preingestion_identity": seal("B2_DEVELOPMENT_PILOT05_PREINGESTION_V1", prospective_core)}
    operations = [("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"], rights_identity), ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], source_package_identity), ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], archive_commitment), ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"], family_closure), ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"], partition_identity), ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"], prospective["preingestion_identity"])]
    operation_records = [{"ordinal": i, "purpose": purpose, "object_identity": obj, "required_signer_roles": roles, "distinct_signers_required": len(roles) > 1} for i, (purpose, roles, obj) in enumerate(operations)]
    packet_core = {"preingestion_identity": prospective["preingestion_identity"], "source_sha256": SOURCE_SHA, "declaration_sha256": DECLARATION_SHA, "registration_identity": REGISTRATION_ID, "prior_ledger_head": LEDGER_HEAD, "operations": operation_records, "atomic": True}
    packet_identity = seal("B2_DEVELOPMENT_PILOT05_SIGNING_PACKET_V1", packet_core)
    registration = git_json(VALIDATION_COMMIT, "docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json")
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    requests = []
    for operation in operation_records:
        for role in operation["required_signer_roles"]:
            challenge_core = {"domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT05_PREINGESTION_V1", "purpose": operation["purpose"], "role": role, "principal_identity": principals[role], "object_identity": operation["object_identity"], "packet_identity": packet_identity, "source_sha256": SOURCE_SHA, "declaration_sha256": DECLARATION_SHA, "preingestion_identity": prospective["preingestion_identity"], "nonce": seal("B2_PILOT05_SIGNING_NONCE_V1", {"packet": packet_identity, "ordinal": operation["ordinal"], "role": role}), "prior_ledger_head": LEDGER_HEAD, "grants_operational_content_access": False}
            challenge = {**challenge_core, "challenge_identity": seal("B2_PILOT05_SIGNING_CHALLENGE_V1", challenge_core)}
            requests.append({"operation_ordinal": operation["ordinal"], "purpose": operation["purpose"], "role": role, "challenge": challenge, "signature_status": "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION"})
    packet = {"schema_name": "batch2-development-pilot05-custodial-signing-packet-v1", "schema_version": "1.0.0", "packet_core": packet_core, "packet_identity": packet_identity, "signature_requests": requests, "status": "UNSIGNED", "signatures_present": 0, "source_ingested": False, "archive_written": False, "ledger_events_appended": 0}
    for name, value in zip(names, (prospective, independence, packet), strict=True):
        (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"preparation_verdict": "PASS_UNSIGNED_PREPARATION", "preingestion_identity": prospective["preingestion_identity"], "source_commitment": source_commitment, "rights_identity": rights_identity, "archive_commitment": archive_commitment, "source_package_identity": source_package_identity, "authority_envelope_identity": envelope_identity, "family_independence_identity": independence["family_independence_identity"], "family_closure": family_closure, "partition_identity": partition_identity, "signing_packet_identity": packet_identity, "signature_requests": len(requests)}, sort_keys=True))


if __name__ == "__main__":
    main()

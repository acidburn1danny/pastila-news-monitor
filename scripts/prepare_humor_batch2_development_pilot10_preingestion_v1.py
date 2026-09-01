"""Prepare Pilot 10 prospective objects and an unsigned custodial packet only."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot10-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot10-v1.json"
VALIDATION_COMMIT = "9ff02583e8c55c889f5e805dbf272647096a0f4d"
VALIDATION_IDENTITY = "a617795fc21f257e73ff3ed5947151cb9dc762bca51f90a2c11a0f346d313851"
SOURCE_SHA256 = "454a0c568c12a46224407f6c3b378f8197e3f4653cca6d897d1c03b8d94821d7"
DECLARATION_SHA256 = "4bc43e0b03964d50685fe2e5193fafcbfee2c14cd35ebe777fdba64c15540435"
LEDGER_HEAD = "0dc087dde79a0b008d333c4e84a0572b32cb9bd25704b9a55a00cb4d5849069a"
REGISTRATION_IDENTITY = "01912e139471ec23cba5861c8f575f098a6248d39ebbe5ec2ee043493d392ebe"
GOVERNANCE = "80bbf059956424ce6f20885de51ce900f6116b40a223a107a46a29d3b012efc6"
CONFORMANCE = "084ddf4d8e9f215db3665370221260c351d3befe747c4dbb45ab35baac4c993b"
CONTRACT = "69138467540b37cbfb8444596d9a37119f8b74d002e0c491c8ff599ce77cec77"
IMPLEMENTATION = "bdf48e9942f097f0259831c0f2f611e50644cdbe7179a2dc7d990bf9ab2b5493"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_blob_oid(value: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def git_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{VALIDATION_COMMIT}:{path}"], cwd=ROOT))


def coordinates(source: str, start: int, end: int) -> dict[str, Any]:
    raw = source[start:end].encode()
    return {
        "character_coordinates": [start, end],
        "utf8_byte_coordinates": [len(source[:start].encode()), len(source[:end].encode())],
        "sha256": sha256(raw),
    }


def proposition(identifier: str, source: str, span: tuple[int, int], subject: tuple[int, int],
                predicate: tuple[int, int], obj: tuple[int, int], qualification: tuple[int, int] | None,
                time: str, known: str, unknown: str) -> dict[str, Any]:
    start, end = span
    words = [(start + item.start(), start + item.end()) for item in re.finditer(r"\S+", source[start:end])]

    def part(bounds: tuple[int, int]) -> dict[str, Any]:
        return coordinates(source, words[bounds[0]][0], words[bounds[1] - 1][1])

    return {
        "proposition_id": identifier,
        "supporting_span": {**coordinates(source, start, end), "span_sha256": sha256(source[start:end].encode())},
        "subject": part(subject), "predicate": part(predicate), "object": part(obj),
        "modality": "ASSERTED", "qualification": part(qualification) if qualification else None,
        "time": time, "scope": "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY",
        "attribution": "OWNER_AUTHORED_SOURCE", "known_boundary": known, "unknown_boundary": unknown,
        "prohibited_inferences": [
            "NO_REAL_WORLD_ASSERTION", "NO_UNSTATED_CAUSAL_INFERENCE",
            "NO_UNSTATED_PERSON_INTENT_OR_INTERNAL_STATE_INFERENCE",
            "NO_UNSTATED_DELIVERY_CRATE_MATERIAL_PROCEDURE_DISPOSITION_OR_OUTCOME_INFERENCE",
        ],
        "quotation_status": "NO_QUOTATION",
        "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC",
    }


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == VALIDATION_COMMIT, "HEAD differs from validation commit")
    validation = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot10-strict-preingestion-validation-v1.json")
    require(validation["validation_identity"] == VALIDATION_IDENTITY, "validation identity")
    require(validation["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY", "validation verdict")
    require(validation["deterministic_blockers"] == [] and validation["repair_performed"] is False, "validation boundary")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(sha256(source_bytes) == SOURCE_SHA256 and sha256(declaration_bytes) == DECLARATION_SHA256, "input hashes")
    source, declaration = source_bytes.decode("utf-8"), json.loads(declaration_bytes)
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-10", "pilot")
    sentence_spans = []
    for match in re.finditer(r"[^.!?]+[.!?]", source, re.S):
        raw = match.group()
        sentence_spans.append((match.start() + len(raw) - len(raw.lstrip()), match.end()))
    require(len(sentence_spans) == 7, "seven proposition candidates")
    propositions = [
        proposition("P1", source, sentence_spans[0], (6, 10), (10, 13), (13, 22), (0, 6),
                    "EXPLICIT_2026_09_21_AFTERNOON", "EXACT_DELIVERY_EVENT_QUANTITY_AND_MATERIAL_CATEGORY",
                    "NO_OTHER_DELIVERY_SOURCE_OR_MATERIAL_FACT"),
        proposition("P2", source, sentence_spans[1], (2, 4), (4, 6), (7, 19), (0, 2),
                    "AT_RECEPTION", "EACH_CRATE_IS_WEIGHED_AND_LABEL_NUMBER_COMPARED_WITH_DELIVERY_DOCUMENT",
                    "NO_ASSERTION_ABOUT_COMPARISON_RESULT"),
        proposition("P3", source, sentence_spans[2], (16, 17), (17, 25), (25, 32), (0, 16),
                    "IF_BOTH_DOCUMENT_MATCH_CONDITIONS_HOLD", "CRATE_IS_APPROVED_AND_MOVED_TO_HORTICULTURAL_STORAGE",
                    "NO_ASSERTION_THAT_ANY_CRATE_WILL_MEET_BOTH_CONDITIONS"),
        proposition("P4", source, sentence_spans[3], (15, 16), (16, 24), (24, 27), (0, 15),
                    "IF_WEIGHT_DIFFERS_OR_LABEL_NUMBER_DOES_NOT_MATCH", "CRATE_REMAINS_AT_RECEPTION_AND_IS_REJECTED",
                    "NO_ASSERTION_THAT_ANY_CRATE_WILL_MEET_A_REJECTION_CONDITION"),
        proposition("P5", source, sentence_spans[4], (0, 1), (1, 2), (2, 11), None,
                    "DURING_STATED_RECEPTION", "STAFF_RECORD_CRATE_NUMBER_AND_OBSERVED_DIFFERENCE_TYPE_FOR_EACH_DISCREPANCY",
                    "NO_ASSERTION_THAT_A_DISCREPANCY_EXISTS"),
        proposition("P6", source, sentence_spans[5], (0, 1), (1, 10), (10, 17), (3, 7),
                    "THIS_DELIVERY_ONLY", "VERIFICATION_DOES_NOT_ESTABLISH_STATE_OF_OTHER_STORED_MATERIALS",
                    "ALL_FACTS_ABOUT_OTHER_MATERIALS_REMAIN_UNKNOWN"),
        proposition("P7", source, sentence_spans[6], (12, 14), (16, 18), (18, 20), (0, 16),
                    "BEFORE_RECEPTION", "DISCREPANCY_EXISTENCE_COUNT_AND_ADDITIONAL_VERIFICATION NEED_ARE_UNKNOWN",
                    "NO_ASSERTION_THAT_DISCREPANCIES_OR_ADDITIONAL_VERIFICATIONS_WILL OCCUR"),
    ]
    metadata = declaration["source"]
    source_commitment = seal("B2_OWNED_SOURCE_COMMITMENT_V1", {
        "sha256": SOURCE_SHA256, "byte_length": len(source_bytes), "encoding": "UTF-8",
        "source_version": metadata["source_version"], "capture_timestamp": metadata["capture_timestamp"],
    })
    rights_identity = seal("B2_INTERNALLY_OWNED_RIGHTS_INSTRUMENT_PROSPECTIVE_V1", {
        "declaration_sha256": DECLARATION_SHA256, "owner_identity": declaration["contributor"]["public_identity"],
        "grants": declaration["independent_grants"], "rights_terms": declaration["rights_terms"],
    })
    envelope = {"source_commitment": source_commitment, "source_sha256": SOURCE_SHA256,
                "world_scope": metadata["world_scope"], "authority_scope": metadata["authority_scope"],
                "propositions": propositions, "creative_premise_family_id": "UNASSIGNED"}
    envelope_identity = seal("B2_FACTUAL_AUTHORITY_ENVELOPE_PROSPECTIVE_V1", envelope)
    source_blob = git_blob_oid(source_bytes)
    archive_commitment = seal("B2_IMMUTABLE_ARCHIVE_COMMITMENT_PROSPECTIVE_V1", {
        "source_commitment": source_commitment, "source_sha256": SOURCE_SHA256, "byte_length": len(source_bytes),
        "prospective_git_blob_oid_sha1": source_blob, "write_status": "NOT_WRITTEN",
    })
    admissions = [git_json(f"docs/artifacts/humor-mechanics-batch2-development-pilot{i:02d}-g01a-g01b-admission-v1.json") for i in range(1, 10)]
    prior_hashes = [item["g01a"]["source_sha256"] for item in admissions]
    prior_blobs = [item["g01a"]["source_git_object"] for item in admissions]
    independence_core = {
        "schema_name": "batch2-development-pilot10-family-independence-v1", "schema_version": "1.0.0",
        "pilot10_source_sha256": SOURCE_SHA256, "prior_source_sha256": prior_hashes,
        "prior_family_identities": {f"pilot{i:02d}": item["g01b"]["family_identities"] for i, item in enumerate(admissions, 1)},
        "pilot10_topology": ["SYNTHETIC_BOTANICAL_GARDEN_DELIVERY_RECEPTION", "CRATE_WEIGHT_AND_IDENTIFIER_COMPARISON",
            "CONJUNCTIVE_APPROVAL_AND_STORAGE", "DISJUNCTIVE_REJECTION_AND_RECEPTION_HOLD",
            "DISCREPANCY_RECORDING", "DELIVERY_ONLY_SCOPE", "DISCREPANCY_AND_ADDITIONAL_VERIFICATION_UNKNOWN"],
        "source_hash_distinct": SOURCE_SHA256 not in prior_hashes, "git_blob_distinct": source_blob not in prior_blobs,
        "exact_prior_line_reuse": False, "source_event_topic_revision_sibling_syndication_same_event_relation": False,
        "prior_target_obligation_selected_proposition_constructor_test_creative_premise_or_marker_assignment": False,
        "prior_construction_model_training_runtime_or_production_exposure": False, "blind_family_access": False,
        "selected_or_shaped_using_governance_obligation_sufficiency_constructor_target_gap_pool_confound_prior_candidate_or_marker": False,
        "result": "PASS_FRESH_FAMILY_INDEPENDENCE",
    }
    independence = {**independence_core, "family_independence_identity": seal("B2_DEVELOPMENT_PILOT10_FAMILY_INDEPENDENCE_V1", independence_core)}
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {"pilot_id": declaration["pilot_id"], "event_class": "OWNER_AUTHORED_SYNTHETIC_BOTANICAL_DELIVERY_RECEPTION"})
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {"rights_identity": rights_identity, "authority_envelope_identity": envelope_identity})
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {"subject_class": metadata["subject_class"], "topic_entity_class": "SYNTHETIC_BOTANICAL_GARDEN_DELIVERY_CONTROL"})
    revision_family = seal("B2_REVISION_FAMILY_V1", {"source_family": source_family, "source_version": metadata["source_version"], "supersedes": None})
    family_closure = seal("B2_FAMILY_CLOSURE_PROSPECTIVE_V1", {"source": source_family, "event": event_family,
        "authority": authority_family, "topic_entity": topic_family, "revision": revision_family,
        "family_independence_identity": independence["family_independence_identity"], "creative_premise": "UNASSIGNED",
        "construction_revision_family": "UNASSIGNED", "creative_marker_family": "UNASSIGNED"})
    partition_identity = seal("B2_DEVELOPMENT_PARTITION_SEAL_PROSPECTIVE_V1", {
        "family_closure": family_closure, "partition": "DEVELOPMENT", "curriculum_candidate": False, "blind_evaluation": False})
    source_package_identity = seal("B2_SOURCE_PACKAGE_PROSPECTIVE_V1", {
        "source_commitment": source_commitment, "archive_commitment": archive_commitment, "rights_identity": rights_identity,
        "authority_envelope_identity": envelope_identity, "family_closure": family_closure,
        "partition_identity": partition_identity, "status": "NOT_INGESTED_NOT_ARCHIVED"})
    core = {
        "schema_name": "batch2-development-pilot10-preingestion-v1", "schema_version": "1.0.0",
        "status": "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED", "validation_commit": VALIDATION_COMMIT,
        "validation_identity": VALIDATION_IDENTITY, "governance_identity": GOVERNANCE,
        "conformance_schema_identity": CONFORMANCE, "constructor_contract_identity": CONTRACT,
        "constructor_implementation_identity": IMPLEMENTATION, "source_sha256": SOURCE_SHA256,
        "source_byte_length": len(source_bytes), "declaration_sha256": DECLARATION_SHA256,
        "source_commitment": source_commitment, "rights_instrument_identity": rights_identity,
        "immutable_archive_commitment": archive_commitment, "prospective_git_blob_oid_sha1": source_blob,
        "source_package_identity": source_package_identity, "factual_authority_envelope": envelope,
        "factual_authority_envelope_identity": envelope_identity,
        "family_independence_identity": independence["family_independence_identity"],
        "family_identities": {"source_family": source_family, "event_family": event_family,
            "authority_family": authority_family, "topic_entity_family": topic_family, "revision_family": revision_family,
            "family_closure": family_closure, "creative_premise_family_id": "UNASSIGNED",
            "construction_revision_family_id": "UNASSIGNED", "creative_marker_family_id": "UNASSIGNED"},
        "partition": "DEVELOPMENT", "prospective_partition_identity": partition_identity,
        "selected_proposition": "UNASSIGNED", "target_mechanism": "UNASSIGNED", "operational_obligation": "UNASSIGNED",
        "proposition_sufficiency_evaluated": False, "constructor_source_compatibility_evaluated": False,
        "post_realization_pre_emission_conformance_performed": False, "fragment_collision_evaluated": False,
        "archive_write": False, "git_archival": False, "ingested": False, "g01a_admitted": False, "g01b_admitted": False,
        "authority_matrix": {key: False for key in ("custodial_signing", "signature_verification", "immutable_ingestion",
            "archive_write", "g01a_admission", "g01b_admission", "proposition_sufficiency_evaluation", "assignment",
            "constructor_source_compatibility_evaluation", "constructor_release", "constructor_invocation", "realization",
            "candidate_emission", "post_realization_pre_emission_conformance", "fragment_collision_evaluation", "g02", "g02c",
            "g03", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    prospective = {**core, "preingestion_identity": seal("B2_DEVELOPMENT_PILOT10_PREINGESTION_V1", core)}
    operations = [("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"], rights_identity),
        ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], source_package_identity),
        ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], archive_commitment),
        ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"], family_closure),
        ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"], partition_identity),
        ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"], prospective["preingestion_identity"])]
    records = [{"ordinal": i, "purpose": p, "object_identity": o, "required_signer_roles": r,
                "distinct_signers_required": len(r) > 1} for i, (p, r, o) in enumerate(operations)]
    packet_core = {"preingestion_identity": prospective["preingestion_identity"], "source_sha256": SOURCE_SHA256,
        "declaration_sha256": DECLARATION_SHA256, "registration_identity": REGISTRATION_IDENTITY,
        "prior_ledger_head": LEDGER_HEAD, "operations": records, "atomic": True}
    packet_identity = seal("B2_DEVELOPMENT_PILOT10_SIGNING_PACKET_V1", packet_core)
    registration = git_json("docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json")
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    requests = []
    for operation in records:
        for role in operation["required_signer_roles"]:
            challenge_core = {"domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT10_PREINGESTION_V1",
                "purpose": operation["purpose"], "role": role, "principal_identity": principals[role],
                "object_identity": operation["object_identity"], "packet_identity": packet_identity,
                "source_sha256": SOURCE_SHA256, "declaration_sha256": DECLARATION_SHA256,
                "preingestion_identity": prospective["preingestion_identity"],
                "nonce": seal("B2_PILOT10_SIGNING_NONCE_V1", {"packet": packet_identity, "ordinal": operation["ordinal"], "role": role}),
                "prior_ledger_head": LEDGER_HEAD, "grants_operational_content_access": False}
            challenge = {**challenge_core, "challenge_identity": seal("B2_PILOT10_SIGNING_CHALLENGE_V1", challenge_core)}
            requests.append({"operation_ordinal": operation["ordinal"], "purpose": operation["purpose"], "role": role,
                "challenge": challenge, "signature_status": "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION"})
    require(len(requests) == 8, "exactly eight requests")
    packet = {"schema_name": "batch2-development-pilot10-custodial-signing-packet-v1", "schema_version": "1.0.0",
        "packet_core": packet_core, "packet_identity": packet_identity, "signature_requests": requests,
        "status": "UNSIGNED", "signatures_present": 0, "source_ingested": False, "archive_written": False,
        "ledger_events_appended": 0, "proposition_sufficiency_evaluated": False,
        "constructor_source_compatibility_or_release_performed": False,
        "realization_candidate_emission_or_preemission_conformance_performed": False,
        "fragment_collision_evaluation_performed": False}
    write("humor-mechanics-batch2-development-pilot10-preingestion-v1.json", prospective)
    write("humor-mechanics-batch2-development-pilot10-family-independence-v1.json", independence)
    write("humor-mechanics-batch2-development-pilot10-signing-packet-v1.json", packet)
    print(json.dumps({"preparation_verdict": "PASS_UNSIGNED_PREPARATION", "preingestion_identity": prospective["preingestion_identity"],
        "source_commitment": source_commitment, "rights_identity": rights_identity, "archive_commitment": archive_commitment,
        "source_package_identity": source_package_identity, "authority_envelope_identity": envelope_identity,
        "family_independence_identity": independence["family_independence_identity"], "family_closure": family_closure,
        "partition_identity": partition_identity, "signing_packet_identity": packet_identity, "signature_requests": len(requests)}, sort_keys=True))


if __name__ == "__main__":
    main()

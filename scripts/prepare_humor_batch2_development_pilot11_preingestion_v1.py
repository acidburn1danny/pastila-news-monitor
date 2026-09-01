"""Prepare prospective Pilot 11 identities and unsigned custodial packet only."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot11-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot11-v1.json"
VALIDATION_COMMIT = "b3ca5e2d80593614d4e2304583e66f782c0fe716"
VALIDATION_IDENTITY = "513f665bfba9b476fe088c04e6c12aed3315a9342583004448362760e2c956bb"
SOURCE_SHA256 = "cdf1901941057914cb7b22ac1233771773e2f15bd1671bcc47e2d17d123e2bd9"
DECLARATION_SHA256 = "6fdb4ca1cac39f6b4cf4ae9614163d0641695608568bebc4e582322190a3ed21"
LEDGER_HEAD = "e8279d111b95f6a1e4abf96ace2594c2cdbda6be504708d7df3d9e10feec8335"
REGISTRATION_IDENTITY = "01912e139471ec23cba5861c8f575f098a6248d39ebbe5ec2ee043493d392ebe"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_blob_oid(value: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def git_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{VALIDATION_COMMIT}:{path}"], cwd=ROOT))


def coordinates(source: str, start: int, end: int) -> dict[str, Any]:
    raw = source[start:end].encode()
    return {"character_coordinates": [start, end],
            "utf8_byte_coordinates": [len(source[:start].encode()), len(source[:end].encode())], "sha256": sha256(raw)}


def proposition(identifier: str, source: str, span: tuple[int, int], subject: tuple[int, int],
                predicate: tuple[int, int], obj: tuple[int, int], qualification: tuple[int, int] | None,
                time: str, known: str, unknown: str) -> dict[str, Any]:
    start, end = span
    words = [(start + item.start(), start + item.end()) for item in re.finditer(r"\S+", source[start:end])]

    def part(bounds: tuple[int, int]) -> dict[str, Any]:
        return coordinates(source, words[bounds[0]][0], words[bounds[1] - 1][1])

    return {"proposition_id": identifier,
            "supporting_span": {**coordinates(source, start, end), "span_sha256": sha256(source[start:end].encode())},
            "subject": part(subject), "predicate": part(predicate), "object": part(obj),
            "modality": "ASSERTED", "qualification": part(qualification) if qualification else None,
            "time": time, "scope": "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY",
            "attribution": "OWNER_AUTHORED_SOURCE", "known_boundary": known, "unknown_boundary": unknown,
            "prohibited_inferences": ["NO_REAL_WORLD_ASSERTION", "NO_UNSTATED_CAUSAL_INFERENCE",
                "NO_UNSTATED_PERSON_INTENT_OR_INTERNAL_STATE_INFERENCE",
                "NO_UNSTATED_CONTAINER_MATERIAL_PROCEDURE_DISPOSITION_OR_OUTCOME_INFERENCE"],
            "quotation_status": "NO_QUOTATION",
            "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC"}


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == VALIDATION_COMMIT, "HEAD")
    validation = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot11-strict-preingestion-validation-v1.json")
    require(validation["validation_identity"] == VALIDATION_IDENTITY, "validation identity")
    require(validation["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY", "validation verdict")
    require(validation["deterministic_blockers"] == [] and validation["repair_performed"] is False, "validation boundary")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(sha256(source_bytes) == SOURCE_SHA256 and sha256(declaration_bytes) == DECLARATION_SHA256, "input hashes")
    source, declaration = source_bytes.decode("utf-8"), json.loads(declaration_bytes)
    spans = [(m.start() + len(m.group()) - len(m.group().lstrip()), m.end()) for m in re.finditer(r"[^.!?]+[.!?]", source, re.S)]
    require(len(spans) == 7, "seven propositions")
    propositions = [
        proposition("P1", source, spans[0], (6, 11), (11, 12), (12, 20), (0, 6),
                    "EXPLICIT_2026_09_23_MORNING_BEFORE_FILLING", "EXACT_INSPECTION_EVENT_QUANTITY_AND_MATERIAL", "NO_OTHER_LOT_OR_CONTAINER_FACT"),
        proposition("P2", source, spans[1], (3, 4), (4, 5), (5, 20), (0, 3),
                    "FOR_EACH_CONTAINER_BEFORE_FILLING", "SURFACE_INTEGRITY_AND_SERIAL_MATCH_ARE_CHECKED", "NO_ASSERTION_ABOUT_CHECK_RESULT"),
        proposition("P3", source, spans[2], (5, 6), (6, 16), (16, 20), (0, 5),
                    "IF_BOTH_CHECKS_CONFORM", "CONTAINER_RECORDED_ACCEPTED_AND_SENT_TO_FILLING_LINE", "NO_ASSERTION_ANY_CONTAINER_WILL QUALIFY"),
        proposition("P4", source, spans[3], (9, 10), (10, 15), (15, 19), (0, 9),
                    "IF_CRACK_OBSERVED_OR_SERIAL_MISMATCHES", "CONTAINER_REJECTED_AND_REMAINS_IN_CONTROL_AREA", "NO_ASSERTION_ANY_CONTAINER_WILL FAIL"),
        proposition("P5", source, spans[4], (4, 5), (5, 7), (7, 11), (0, 4),
                    "FOR_EACH_REJECTED_CONTAINER", "OPERATOR_RECORDS_SERIAL_AND_REJECTION_REASON", "NO_ASSERTION_REJECTION EXISTS"),
        proposition("P6", source, spans[5], (0, 1), (1, 10), (10, 15), (3, 7),
                    "THIS_LOT_ONLY", "VERIFICATION_DOES_NOT ESTABLISH OTHER LOT CONTAINER STATE", "ALL OTHER LOT STATES UNKNOWN"),
        proposition("P7", source, spans[6], (3, 6), (6, 20), (20, 25), (0, 3),
                    "BEFORE_CONTROL", "REJECTION_COUNT_AND_REPLACEMENT_NECESSITY_UNKNOWN", "NO ASSERTION REJECTION OR REPLACEMENT WILL OCCUR"),
    ]
    metadata = declaration["source"]
    source_commitment = seal("B2_OWNED_SOURCE_COMMITMENT_V1", {"sha256": SOURCE_SHA256, "byte_length": len(source_bytes),
        "encoding": "UTF-8", "source_version": metadata["source_version"], "capture_timestamp": metadata["capture_timestamp"]})
    rights_identity = seal("B2_INTERNALLY_OWNED_RIGHTS_INSTRUMENT_PROSPECTIVE_V1", {
        "declaration_sha256": DECLARATION_SHA256, "owner_identity": declaration["contributor"]["public_identity"],
        "grants": declaration["independent_grants"], "rights_terms": declaration["rights_terms"]})
    envelope = {"source_commitment": source_commitment, "source_sha256": SOURCE_SHA256,
        "world_scope": metadata["world_scope"], "authority_scope": metadata["authority_scope"],
        "propositions": propositions, "creative_premise_family_id": "UNASSIGNED"}
    envelope_identity = seal("B2_FACTUAL_AUTHORITY_ENVELOPE_PROSPECTIVE_V1", envelope)
    source_blob = git_blob_oid(source_bytes)
    archive_commitment = seal("B2_IMMUTABLE_ARCHIVE_COMMITMENT_PROSPECTIVE_V1", {"source_commitment": source_commitment,
        "source_sha256": SOURCE_SHA256, "byte_length": len(source_bytes), "prospective_git_blob_oid_sha1": source_blob,
        "write_status": "NOT_WRITTEN"})
    admissions = [git_json(f"docs/artifacts/humor-mechanics-batch2-development-pilot{i:02d}-g01a-g01b-admission-v1.json") for i in range(1, 11)]
    prior_hashes = [item["g01a"]["source_sha256"] for item in admissions]
    prior_blobs = [item["g01a"]["source_git_object"] for item in admissions]
    independence_core = {"schema_name": "batch2-development-pilot11-family-independence-v1", "schema_version": "1.0.0",
        "pilot11_source_sha256": SOURCE_SHA256, "prior_source_sha256": prior_hashes,
        "prior_family_identities": {f"pilot{i:02d}": item["g01b"]["family_identities"] for i, item in enumerate(admissions, 1)},
        "pilot11_topology": ["SYNTHETIC_GLASS_CONTAINER_LOT_INSPECTION", "SURFACE_AND_SERIAL_CONJUNCTIVE_CHECK",
            "CONJUNCTIVE_ACCEPTANCE_AND_FILLING_DISPOSITION", "DISJUNCTIVE_REJECTION_AND_CONTROL_HOLD",
            "REJECTION_REASON_RECORDING", "LOT_ONLY_SCOPE", "REJECTION_COUNT_AND_REPLACEMENT_UNKNOWN"],
        "source_hash_distinct": SOURCE_SHA256 not in prior_hashes, "git_blob_distinct": source_blob not in prior_blobs,
        "exact_prior_line_reuse": False, "source_event_topic_revision_sibling_syndication_same_event_relation": False,
        "prior_target_obligation_proposition_constructor_semantic_role_affordance_realization_witness_premise_or_marker_assignment": False,
        "prior_construction_model_training_runtime_or_production_exposure": False, "blind_family_access": False,
        "selected_or_shaped_using_downstream_gate_or_expected_result": False, "result": "PASS_FRESH_FAMILY_INDEPENDENCE"}
    independence = {**independence_core, "family_independence_identity": seal("B2_DEVELOPMENT_PILOT11_FAMILY_INDEPENDENCE_V1", independence_core)}
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {"pilot_id": declaration["pilot_id"], "event_class": "OWNER_AUTHORED_SYNTHETIC_GLASS_CONTAINER_LOT_INSPECTION"})
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {"rights_identity": rights_identity, "authority_envelope_identity": envelope_identity})
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {"subject_class": metadata["subject_class"], "topic_entity_class": "SYNTHETIC_GLASS_CONTAINER_QUALITY_CONTROL"})
    revision_family = seal("B2_REVISION_FAMILY_V1", {"source_family": source_family, "source_version": metadata["source_version"], "supersedes": None})
    family_closure = seal("B2_FAMILY_CLOSURE_PROSPECTIVE_V1", {"source": source_family, "event": event_family,
        "authority": authority_family, "topic_entity": topic_family, "revision": revision_family,
        "family_independence_identity": independence["family_independence_identity"], "creative_premise": "UNASSIGNED",
        "construction_revision_family": "UNASSIGNED", "creative_marker_family": "UNASSIGNED"})
    partition_identity = seal("B2_DEVELOPMENT_PARTITION_SEAL_PROSPECTIVE_V1", {"family_closure": family_closure,
        "partition": "DEVELOPMENT", "curriculum_candidate": False, "blind_evaluation": False})
    source_package_identity = seal("B2_SOURCE_PACKAGE_PROSPECTIVE_V1", {"source_commitment": source_commitment,
        "archive_commitment": archive_commitment, "rights_identity": rights_identity,
        "authority_envelope_identity": envelope_identity, "family_closure": family_closure,
        "partition_identity": partition_identity, "status": "NOT_INGESTED_NOT_ARCHIVED"})
    request = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot11-owner-input-request-v1.json")
    core = {"schema_name": "batch2-development-pilot11-preingestion-v1", "schema_version": "1.0.0",
        "status": "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED", "validation_commit": VALIDATION_COMMIT,
        "validation_identity": VALIDATION_IDENTITY, "governance_identity": request["governance_identity"],
        "conformance_schema_identity": request["conformance_schema_identity"],
        "constructor_contract_identity": request["constructor_contract_identity"],
        "constructor_implementation_identity": request["constructor_implementation_identity"],
        "source_sha256": SOURCE_SHA256, "source_byte_length": len(source_bytes), "declaration_sha256": DECLARATION_SHA256,
        "source_commitment": source_commitment, "rights_instrument_identity": rights_identity,
        "immutable_archive_commitment": archive_commitment, "prospective_git_blob_oid_sha1": source_blob,
        "source_package_identity": source_package_identity, "factual_authority_envelope": envelope,
        "factual_authority_envelope_identity": envelope_identity, "family_independence_identity": independence["family_independence_identity"],
        "family_identities": {"source_family": source_family, "event_family": event_family, "authority_family": authority_family,
            "topic_entity_family": topic_family, "revision_family": revision_family, "family_closure": family_closure,
            "creative_premise_family_id": "UNASSIGNED", "construction_revision_family_id": "UNASSIGNED",
            "creative_marker_family_id": "UNASSIGNED"},
        "partition": "DEVELOPMENT", "prospective_partition_identity": partition_identity,
        "selected_proposition": "UNASSIGNED", "target_mechanism": "UNASSIGNED", "operational_obligation": "UNASSIGNED",
        "semantic_role_signature": "UNASSIGNED", "affordance_topology": "UNASSIGNED", "realization_plan": "UNASSIGNED",
        "witness_topology": "UNASSIGNED", "proposition_sufficiency_evaluated": False,
        "constructor_source_compatibility_or_semantic_plan_evaluated": False, "semantic_edge_validation_performed": False,
        "archive_write": False, "git_archival": False, "ingested": False, "g01a_admitted": False, "g01b_admitted": False,
        "authority_matrix": {key: False for key in ("custodial_signing", "signature_verification", "immutable_ingestion",
            "archive_write", "g01a_admission", "g01b_admission", "proposition_sufficiency_evaluation", "assignment",
            "constructor_source_compatibility_evaluation", "semantic_plan_evaluation", "constructor_release", "constructor_invocation",
            "realization", "candidate_emission", "semantic_edge_validation", "fragment_collision_evaluation", "g02", "g02c", "g03",
            "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")}}
    prospective = {**core, "preingestion_identity": seal("B2_DEVELOPMENT_PILOT11_PREINGESTION_V1", core)}
    operations = [("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"], rights_identity),
        ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], source_package_identity),
        ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], archive_commitment),
        ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"], family_closure),
        ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"], partition_identity),
        ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"], prospective["preingestion_identity"])]
    records = [{"ordinal": i, "purpose": p, "object_identity": o, "required_signer_roles": roles,
                "distinct_signers_required": len(roles) > 1} for i, (p, roles, o) in enumerate(operations)]
    packet_core = {"preingestion_identity": prospective["preingestion_identity"], "source_sha256": SOURCE_SHA256,
        "declaration_sha256": DECLARATION_SHA256, "registration_identity": REGISTRATION_IDENTITY,
        "prior_ledger_head": LEDGER_HEAD, "operations": records, "atomic": True}
    packet_identity = seal("B2_DEVELOPMENT_PILOT11_SIGNING_PACKET_V1", packet_core)
    registration = git_json("docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json")
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    requests = []
    for operation in records:
        for role in operation["required_signer_roles"]:
            challenge_core = {"domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT11_PREINGESTION_V1",
                "purpose": operation["purpose"], "role": role, "principal_identity": principals[role],
                "object_identity": operation["object_identity"], "packet_identity": packet_identity,
                "source_sha256": SOURCE_SHA256, "declaration_sha256": DECLARATION_SHA256,
                "preingestion_identity": prospective["preingestion_identity"],
                "nonce": seal("B2_PILOT11_SIGNING_NONCE_V1", {"packet": packet_identity, "ordinal": operation["ordinal"], "role": role}),
                "prior_ledger_head": LEDGER_HEAD, "grants_operational_content_access": False}
            challenge = {**challenge_core, "challenge_identity": seal("B2_PILOT11_SIGNING_CHALLENGE_V1", challenge_core)}
            requests.append({"operation_ordinal": operation["ordinal"], "purpose": operation["purpose"], "role": role,
                "challenge": challenge, "signature_status": "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION"})
    require(len(requests) == 8, "eight requests")
    packet = {"schema_name": "batch2-development-pilot11-custodial-signing-packet-v1", "schema_version": "1.0.0",
        "packet_core": packet_core, "packet_identity": packet_identity, "signature_requests": requests,
        "status": "UNSIGNED", "signatures_present": 0, "source_ingested": False, "archive_written": False,
        "ledger_events_appended": 0, "proposition_sufficiency_evaluated": False,
        "constructor_semantic_plan_release_or_invocation_performed": False,
        "realization_candidate_emission_or_semantic_edge_validation_performed": False,
        "fragment_collision_evaluation_performed": False}
    write("humor-mechanics-batch2-development-pilot11-preingestion-v1.json", prospective)
    write("humor-mechanics-batch2-development-pilot11-family-independence-v1.json", independence)
    write("humor-mechanics-batch2-development-pilot11-signing-packet-v1.json", packet)
    print(json.dumps({"preparation_verdict": "PASS_UNSIGNED_PREPARATION", "preingestion_identity": prospective["preingestion_identity"],
        "source_commitment": source_commitment, "rights_identity": rights_identity, "archive_commitment": archive_commitment,
        "source_package_identity": source_package_identity, "authority_envelope_identity": envelope_identity,
        "family_independence_identity": independence["family_independence_identity"], "family_closure": family_closure,
        "partition_identity": partition_identity, "signing_packet_identity": packet_identity, "signature_requests": len(requests)}, sort_keys=True))


if __name__ == "__main__":
    main()

"""Prepare prospective Pilot 12 identities and unsigned custodial packet only."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot12-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot12-v1.json"
VALIDATION_COMMIT = "429afab261f4037d5f9c2a8136b97da238ef8d64"
VALIDATION_IDENTITY = "cac50378a8d97eea9cebb67d333deca20811ea9080a3e9f875be8998826e19e8"
SOURCE_SHA256 = "8b87cef6b320d45d7594bc48919bae63442f51f1f7937b599575d435df69ea27"
DECLARATION_SHA256 = "94f573e8aa1bb1789117ebef856da896447ddcfd944f195e17267e7bdf456ab3"
LEDGER_HEAD = "1cc90a7a8a7ae0471411a75ad7a5d87c90c983c059fd27ae661d95bc894991b3"


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
            "subject": part(subject), "predicate": part(predicate), "object": part(obj), "modality": "ASSERTED",
            "qualification": part(qualification) if qualification else None, "time": time,
            "scope": "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "attribution": "OWNER_AUTHORED_SOURCE",
            "known_boundary": known, "unknown_boundary": unknown,
            "prohibited_inferences": ["NO_REAL_WORLD_ASSERTION", "NO_UNSTATED_CAUSAL_INFERENCE",
                "NO_UNSTATED_PERSON_INTENT_OR_INTERNAL_STATE_INFERENCE",
                "NO_UNSTATED_LIBRARY_VOLUME_BOX_TRANSFER_DESTINATION_OR_OUTCOME_INFERENCE"],
            "quotation_status": "NO_QUOTATION", "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC"}


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == VALIDATION_COMMIT, "HEAD")
    validation = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot12-strict-preingestion-validation-v1.json")
    require(validation["validation_identity"] == VALIDATION_IDENTITY and validation["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY", "validation")
    require(validation["deterministic_blockers"] == [] and validation["repair_performed"] is False, "validation boundary")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(sha256(source_bytes) == SOURCE_SHA256 and sha256(declaration_bytes) == DECLARATION_SHA256, "inputs")
    source, declaration = source_bytes.decode("utf-8"), json.loads(declaration_bytes)
    spans = [(m.start() + len(m.group()) - len(m.group().lstrip()), m.end()) for m in re.finditer(r"[^.!?]+[.!?]", source, re.S)]
    require(len(spans) == 8, "eight propositions")
    propositions = [
        proposition("P1", source, spans[0], (6, 10), (10, 13), (13, 25), (0, 6),
                    "EXPLICIT_2026_09_25_MORNING", "COLLECTION_QUANTITY_LOCATION_AND_PREPARATION", "NO_OTHER_COLLECTION_OR_LIBRARY_EVENT_FACT"),
        proposition("P2", source, spans[1], (0, 2), (2, 12), (12, 18), None,
                    "TRANSFER_LIST_STATE", "VOLUME_CODE_AND_DESTINATION_SHELF_ASSOCIATION", "NO_ASSERTION_ASSOCIATION_IS_EXPECTED"),
        proposition("P3", source, spans[2], (0, 1), (1, 10), (10, 18), None,
                    "DURING_PREPARATION", "LIBRARIAN_READS_CODE_AND_IDENTIFIES_ASSOCIATED_SHELF", "NO_ASSERTION_DESTINATION_MATCHES_EXPECTATION"),
        proposition("P4", source, spans[3], (0, 1), (1, 4), (4, 13), None,
                    "AFTER_SHELF_IDENTIFICATION", "VOLUME_PLACED_IN_BOX_MARKED_WITH_LISTED_SHELF", "NO_ASSERTION_BOX_WILL_BE_TRANSPORTED"),
        proposition("P5", source, spans[4], (0, 2), (2, 4), (4, 7), (7, 19),
                    "ONLY_IF_ALL_BOXED_VOLUMES_SHARE_DESTINATION", "BOX_TRANSPORTED_TO_LIBRARY_STORAGE", "NO_ASSERTION_ANY_BOX_SATISFIES_CONDITION"),
        proposition("P6", source, spans[5], (13, 14), (14, 16), (16, 21), (0, 13),
                    "IF_BOX_HAS_MIXED_DESTINATION_SHELVES", "BOX_REMAINS_IN_READING_ROOM_FOR_RECHECK", "NO_ASSERTION_ANY_BOX_HAS_MIXED_DESTINATIONS"),
        proposition("P7", source, spans[6], (0, 1), (1, 15), (15, 20), None,
                    "THIS_60_VOLUME_COLLECTION_ONLY", "OPERATION_SCOPE_AND_OTHER_BOOK_POSITION_NONMODIFICATION", "NO_ASSERTION_ABOUT_OTHER_COLLECTIONS"),
        proposition("P8", source, spans[7], (0, 3), (3, 6), (6, 29), (0, 3),
                    "BEFORE_VERIFICATION", "EXPECTED_DESTINATION_MATCH_AND_BOX_RECHECK_NEED_UNKNOWN", "NO_ASSERTION_MISMATCH_OR_RECHECK_WILL_OCCUR"),
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
    admissions = [git_json(f"docs/artifacts/humor-mechanics-batch2-development-pilot{i:02d}-g01a-g01b-admission-v1.json") for i in range(1, 12)]
    prior_hashes = [item["g01a"]["source_sha256"] for item in admissions]
    prior_blobs = [item["g01a"]["source_git_object"] for item in admissions]
    independence_core = {"schema_name": "batch2-development-pilot12-family-independence-v1", "schema_version": "1.0.0",
        "pilot12_source_sha256": SOURCE_SHA256, "prior_source_sha256": prior_hashes,
        "prior_family_identities": {f"pilot{i:02d}": item["g01b"]["family_identities"] for i, item in enumerate(admissions, 1)},
        "pilot12_topology": ["SYNTHETIC_UNIVERSITY_LIBRARY_COLLECTION_TRANSFER", "INVENTORY_CODE_TO_DESTINATION_SHELF_ASSOCIATION",
            "CODE_READ_AND_SHELF_IDENTIFICATION", "SHELF_MARKED_BOX_PLACEMENT", "SAME_DESTINATION_CONDITIONAL_STORAGE_TRANSPORT",
            "MIXED_DESTINATION_RECHECK_HOLD", "COLLECTION_ONLY_SCOPE", "DESTINATION_MATCH_AND_RECHECK_UNKNOWN"],
        "source_hash_distinct": SOURCE_SHA256 not in prior_hashes, "git_blob_distinct": source_blob not in prior_blobs,
        "exact_prior_line_reuse": False, "source_event_topic_revision_sibling_syndication_same_event_relation": False,
        "prior_target_obligation_proposition_constructor_semantic_role_affordance_realization_witness_alignment_premise_or_marker_assignment": False,
        "prior_construction_model_training_runtime_or_production_exposure": False, "blind_family_access": False,
        "selected_or_shaped_using_downstream_gate_alignment_opportunity_or_expected_result": False,
        "result": "PASS_FRESH_FAMILY_INDEPENDENCE"}
    independence = {**independence_core, "family_independence_identity": seal("B2_DEVELOPMENT_PILOT12_FAMILY_INDEPENDENCE_V1", independence_core)}
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {"pilot_id": declaration["pilot_id"], "event_class": "OWNER_AUTHORED_SYNTHETIC_UNIVERSITY_LIBRARY_COLLECTION_TRANSFER"})
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {"rights_identity": rights_identity, "authority_envelope_identity": envelope_identity})
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {"subject_class": metadata["subject_class"], "topic_entity_class": "SYNTHETIC_LIBRARY_VOLUME_TRANSFER_CONTROL"})
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
    request = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot12-owner-input-request-v1.json")
    core = {"schema_name": "batch2-development-pilot12-preingestion-v1", "schema_version": "1.0.0",
        "status": "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED", "validation_commit": VALIDATION_COMMIT,
        "validation_identity": VALIDATION_IDENTITY, "base_governance_identity": request["base_governance_identity"],
        "v5_3_1_alignment_contract_identity": request["v5_3_1_alignment_contract_identity"],
        "constructor_implementation_identity": request["constructor_implementation_identity"],
        "source_sha256": SOURCE_SHA256, "source_byte_length": len(source_bytes), "declaration_sha256": DECLARATION_SHA256,
        "source_commitment": source_commitment, "rights_instrument_identity": rights_identity,
        "immutable_archive_commitment": archive_commitment, "prospective_git_blob_oid_sha1": source_blob,
        "source_package_identity": source_package_identity, "factual_authority_envelope": envelope,
        "factual_authority_envelope_identity": envelope_identity, "family_independence_identity": independence["family_independence_identity"],
        "family_identities": {"source_family": source_family, "event_family": event_family, "authority_family": authority_family,
            "topic_entity_family": topic_family, "revision_family": revision_family, "family_closure": family_closure,
            "creative_premise_family_id": "UNASSIGNED", "construction_revision_family_id": "UNASSIGNED", "creative_marker_family_id": "UNASSIGNED"},
        "partition": "DEVELOPMENT", "prospective_partition_identity": partition_identity,
        "selected_proposition": "UNASSIGNED", "target_mechanism": "UNASSIGNED", "operational_obligation": "UNASSIGNED",
        "semantic_role_signature": "UNASSIGNED", "affordance_topology": "UNASSIGNED", "realization_plan": "UNASSIGNED",
        "witness_topology": "UNASSIGNED", "morphological_alignment_opportunity": "UNASSIGNED",
        "proposition_sufficiency_evaluated": False, "constructor_source_compatibility_or_semantic_plan_evaluated": False,
        "coordinate_bound_semantic_conformance_performed": False, "archive_write": False, "git_archival": False,
        "ingested": False, "g01a_admitted": False, "g01b_admitted": False,
        "authority_matrix": {key: False for key in ("custodial_signing", "signature_verification", "immutable_ingestion", "archive_write",
            "g01a_admission", "g01b_admission", "proposition_sufficiency_evaluation", "assignment", "constructor_source_compatibility_evaluation",
            "semantic_plan_evaluation", "constructor_release", "constructor_invocation", "realization", "candidate_emission",
            "coordinate_bound_semantic_conformance", "semantic_edge_validation", "fragment_collision_evaluation", "g02", "g02c", "g03",
            "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")}}
    prospective = {**core, "preingestion_identity": seal("B2_DEVELOPMENT_PILOT12_PREINGESTION_V1", core)}
    operations = [("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"], rights_identity),
        ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], source_package_identity),
        ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], archive_commitment),
        ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"], family_closure),
        ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"], partition_identity),
        ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"], prospective["preingestion_identity"])]
    records = [{"ordinal": i, "purpose": purpose, "object_identity": obj, "required_signer_roles": roles,
                "distinct_signers_required": len(roles) > 1} for i, (purpose, roles, obj) in enumerate(operations)]
    registration = git_json("docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json")
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    packet_core = {"preingestion_identity": prospective["preingestion_identity"], "source_sha256": SOURCE_SHA256,
        "declaration_sha256": DECLARATION_SHA256, "registration_identity": registration["registration_identity"],
        "prior_ledger_head": LEDGER_HEAD, "operations": records, "atomic": True}
    packet_identity = seal("B2_DEVELOPMENT_PILOT12_SIGNING_PACKET_V1", packet_core)
    requests = []
    for operation in records:
        for role in operation["required_signer_roles"]:
            challenge_core = {"domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT12_PREINGESTION_V1", "purpose": operation["purpose"],
                "role": role, "principal_identity": principals[role], "object_identity": operation["object_identity"],
                "packet_identity": packet_identity, "source_sha256": SOURCE_SHA256, "declaration_sha256": DECLARATION_SHA256,
                "preingestion_identity": prospective["preingestion_identity"],
                "nonce": seal("B2_PILOT12_SIGNING_NONCE_V1", {"packet": packet_identity, "ordinal": operation["ordinal"], "role": role}),
                "prior_ledger_head": LEDGER_HEAD, "grants_operational_content_access": False}
            challenge = {**challenge_core, "challenge_identity": seal("B2_PILOT12_SIGNING_CHALLENGE_V1", challenge_core)}
            requests.append({"operation_ordinal": operation["ordinal"], "purpose": operation["purpose"], "role": role,
                "challenge": challenge, "signature_status": "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION"})
    require(len(requests) == 8, "eight requests")
    packet = {"schema_name": "batch2-development-pilot12-custodial-signing-packet-v1", "schema_version": "1.0.0",
        "packet_core": packet_core, "packet_identity": packet_identity, "signature_requests": requests, "status": "UNSIGNED",
        "signatures_present": 0, "source_ingested": False, "archive_written": False, "ledger_events_appended": 0,
        "proposition_sufficiency_evaluated": False, "constructor_semantic_plan_release_or_invocation_performed": False,
        "realization_candidate_emission_coordinate_conformance_or_semantic_edge_validation_performed": False,
        "fragment_collision_evaluation_performed": False}
    write("humor-mechanics-batch2-development-pilot12-preingestion-v1.json", prospective)
    write("humor-mechanics-batch2-development-pilot12-family-independence-v1.json", independence)
    write("humor-mechanics-batch2-development-pilot12-signing-packet-v1.json", packet)
    print(json.dumps({"preparation_verdict": "PASS_UNSIGNED_PREPARATION", "preingestion_identity": prospective["preingestion_identity"],
        "source_commitment": source_commitment, "rights_identity": rights_identity, "archive_commitment": archive_commitment,
        "source_package_identity": source_package_identity, "authority_envelope_identity": envelope_identity,
        "family_independence_identity": independence["family_independence_identity"], "family_closure": family_closure,
        "partition_identity": partition_identity, "signing_packet_identity": packet_identity,
        "proposition_bindings": len(propositions), "signature_requests": len(requests)}, sort_keys=True))


if __name__ == "__main__":
    main()

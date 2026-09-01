"""Derive Pilot 09 prospective identities and freeze an unsigned signing packet."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot09-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot09-v1.json"
VALIDATION_COMMIT = "8fe9196229a5b86954b77c30e9ff6ed28a6f5d82"
VALIDATION_IDENTITY = "4c1c183f017f2a09fae6ce415a5ed5816fae2be6d956c1a2e927170d57e44625"
SOURCE_SHA256 = "608f26b4588c347707ae5eccb08194d498fb3b3e9e7a6402be63ad2bc7c77c77"
DECLARATION_SHA256 = "8c68d5bf2a711fc518879fcddfba9ea44d7c232fb962fdecc816bf97d249b41b"
LEDGER_HEAD = "c7e343b25d667cea07499d2c78f6f1d7b54861e234baa17603873f6fd7b6e143"
REGISTRATION_IDENTITY = "01912e139471ec23cba5861c8f575f098a6248d39ebbe5ec2ee043493d392ebe"


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
    return {
        "character_coordinates": [start, end],
        "utf8_byte_coordinates": [len(source[:start].encode()), len(source[:end].encode())],
        "sha256": sha256(source[start:end].encode()),
    }


def proposition(
    identifier: str, source: str, sentence_span: tuple[int, int], subject: tuple[int, int],
    predicate: tuple[int, int], obj: tuple[int, int], qualification: tuple[int, int] | None,
    time: str, known: str = "ONLY_THE_EXACT_BOUND_PROPOSITION",
    unknown: str = "ALL_UNSTATED_PROPERTIES_CAUSES_RESULTS_AND_REAL_WORLD_APPLICABILITY",
) -> dict[str, Any]:
    start, end = sentence_span
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
            "NO_UNSTATED_OPERATION_INTERVENTION_OTHER_EQUIPMENT_OR_OUTCOME_INFERENCE",
        ],
        "quotation_status": "NO_QUOTATION",
        "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC",
    }


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), "artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == VALIDATION_COMMIT, "HEAD")
    validation = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot09-strict-preingestion-validation-v1.json")
    require(validation["validation_identity"] == VALIDATION_IDENTITY, "validation")
    require(validation["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY", "verdict")
    require(validation["deterministic_blockers"] == [] and validation["proposition_sufficiency_evaluated"] is False, "boundary")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(sha256(source_bytes) == SOURCE_SHA256 and sha256(declaration_bytes) == DECLARATION_SHA256, "input hashes")
    source, declaration = source_bytes.decode("utf-8"), json.loads(declaration_bytes)
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-09", "pilot")
    sentence_spans: list[tuple[int, int]] = []
    for match in re.finditer(r"[^.!?]+[.!?]", source, re.S):
        raw = match.group()
        sentence_spans.append((match.start() + len(raw) - len(raw.lstrip()), match.end()))
    require(len(sentence_spans) == 8, "sentences")
    propositions = [
        proposition("P1", source, sentence_spans[0], (6, 9), (9, 10), (10, 24), (0, 6), "EXPLICIT_2026_09_18_MORNING"),
        proposition("P2", source, sentence_spans[1], (0, 1), (1, 3), (3, 12), (3, 12), "BEFORE_ORDINARY_PARCEL_PROCESSING"),
        proposition("P3", source, sentence_spans[2], (4, 6), (6, 11), (11, 17), (0, 4), "AT_CONVEYOR_ENTRY_DURING_STATED_VERIFICATION"),
        proposition("P4", source, sentence_spans[3], (3, 6), (6, 7), (7, 17), (0, 3), "AFTER_CONTROL_UNIT_RECEIVES_SIGNAL"),
        proposition(
            "P5", source, sentence_spans[4], (13, 14), (14, 16), (16, 17), (0, 13),
            "CONDITIONAL_DURING_STATED_VERIFICATION",
            "AUTOMATIC_NONSTART_OCCURS_IF_SENSOR_NONDETECTION_OR_SIGNAL_NONARRIVAL_CONDITION_HOLDS",
            "NO_ASSERTION_THAT_EITHER_CONDITION_WILL_OCCUR_OR_THAT_ANY_COMPONENT_IS_DEFECTIVE",
        ),
        proposition("P6", source, sentence_spans[5], (3, 4), (4, 6), (6, 19), (0, 3), "DURING_STATED_VERIFICATION"),
        proposition(
            "P7", source, sentence_spans[6], (0, 1), (1, 3), (3, 18), (3, 9), "STATED_TEST_SCOPE",
            "TEST_IS_LIMITED_TO_THIS_TRANSPORT_LINE_AND_DOES_NOT_ESTABLISH_OTHER_EQUIPMENT_STATE",
            "NO_ASSERTION_ABOUT_OTHER_EQUIPMENT_IN_THE_LOGISTICS_CENTER",
        ),
        proposition(
            "P8", source, sentence_spans[7], (7, 8), (3, 6), (6, 21), (0, 3), "BEFORE_STATED_VERIFICATION",
            "SYSTEM_PERFORMANCE_AND_TECHNICAL_INTERVENTION_NEED_ARE_EXPLICITLY_UNKNOWN_BEFORE_VERIFICATION",
            "NO_ASSERTION_THAT_THE_SYSTEM_WILL_DEVIATE_OR_THAT_INTERVENTION_WILL_BE_NEEDED",
        ),
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
    envelope = {
        "source_commitment": source_commitment, "source_sha256": SOURCE_SHA256,
        "world_scope": metadata["world_scope"], "authority_scope": metadata["authority_scope"],
        "propositions": propositions, "creative_premise_family_id": "UNASSIGNED",
    }
    envelope_identity = seal("B2_FACTUAL_AUTHORITY_ENVELOPE_PROSPECTIVE_V1", envelope)
    source_blob = git_blob_oid(source_bytes)
    archive_commitment = seal("B2_IMMUTABLE_ARCHIVE_COMMITMENT_PROSPECTIVE_V1", {
        "source_commitment": source_commitment, "source_sha256": SOURCE_SHA256,
        "byte_length": len(source_bytes), "prospective_git_blob_oid_sha1": source_blob, "write_status": "NOT_WRITTEN",
    })
    admissions = [
        git_json(f"docs/artifacts/humor-mechanics-batch2-development-pilot{index:02d}-g01a-g01b-admission-v1.json")
        for index in range(1, 9)
    ]
    prior_hashes = [item["g01a"]["source_sha256"] for item in admissions]
    prior_blobs = [item["g01a"]["source_git_object"] for item in admissions]
    independence_core = {
        "schema_name": "batch2-development-pilot09-family-independence-v1", "schema_version": "1.0.0",
        "pilot09_source_sha256": SOURCE_SHA256, "prior_source_sha256": prior_hashes,
        "prior_family_identities": {f"pilot{index:02d}": item["g01b"]["family_identities"] for index, item in enumerate(admissions, 1)},
        "pilot09_topology": [
            "SYNTHETIC_LOGISTICS_CONVEYOR_VERIFICATION", "PRE_OPERATION_VERIFICATION_INTERVAL",
            "PARCEL_SENSOR_TO_CONTROL_SIGNAL_RELATION", "CONTROL_TO_CONVEYOR_START_RELATION",
            "CONDITIONAL_AUTOMATIC_NONSTART", "SEPARATE_VERIFICATION_RECORDING",
            "SINGLE_TRANSPORT_LINE_SCOPE", "SYSTEM_AND_INTERVENTION_OUTCOMES_UNKNOWN",
        ],
        "source_hash_distinct": SOURCE_SHA256 not in prior_hashes, "git_blob_distinct": source_blob not in prior_blobs,
        "exact_prior_line_reuse": False, "source_event_topic_revision_sibling_syndication_same_event_relation": False,
        "prior_target_obligation_selected_proposition_constructor_test_creative_premise_or_marker_assignment": False,
        "prior_construction_model_training_runtime_or_production_exposure": False, "blind_family_access": False,
        "selected_or_shaped_using_governance_obligation_sufficiency_constructor_target_gap_pool_confound_prior_candidate_or_marker": False,
        "result": "PASS_FRESH_FAMILY_INDEPENDENCE",
    }
    independence = {**independence_core, "family_independence_identity": seal("B2_DEVELOPMENT_PILOT09_FAMILY_INDEPENDENCE_V1", independence_core)}
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {"pilot_id": declaration["pilot_id"], "event_class": "OWNER_AUTHORED_SYNTHETIC_LOGISTICS_CONVEYOR_VERIFICATION"})
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {"rights_identity": rights_identity, "authority_envelope_identity": envelope_identity})
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {"subject_class": metadata["subject_class"], "topic_entity_class": "SYNTHETIC_LOGISTICS_CONVEYOR_CONTROL_SYSTEM"})
    revision_family = seal("B2_REVISION_FAMILY_V1", {"source_family": source_family, "source_version": metadata["source_version"], "supersedes": None})
    family_closure = seal("B2_FAMILY_CLOSURE_PROSPECTIVE_V1", {
        "source": source_family, "event": event_family, "authority": authority_family, "topic_entity": topic_family,
        "revision": revision_family, "family_independence_identity": independence["family_independence_identity"],
        "creative_premise": "UNASSIGNED", "construction_revision_family": "UNASSIGNED", "creative_marker_family": "UNASSIGNED",
    })
    partition_identity = seal("B2_DEVELOPMENT_PARTITION_SEAL_PROSPECTIVE_V1", {
        "family_closure": family_closure, "partition": "DEVELOPMENT", "curriculum_candidate": False, "blind_evaluation": False,
    })
    source_package_identity = seal("B2_SOURCE_PACKAGE_PROSPECTIVE_V1", {
        "source_commitment": source_commitment, "archive_commitment": archive_commitment, "rights_identity": rights_identity,
        "authority_envelope_identity": envelope_identity, "family_closure": family_closure,
        "partition_identity": partition_identity, "status": "NOT_INGESTED_NOT_ARCHIVED",
    })
    prospective_core = {
        "schema_name": "batch2-development-pilot09-preingestion-v1", "schema_version": "1.0.0",
        "status": "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED", "validation_commit": VALIDATION_COMMIT,
        "validation_identity": VALIDATION_IDENTITY, "governance_identity": "e81ee4eff9044ee16180ef36a7508fe9f1e7c784fa6830299588cea16c2d3a3e",
        "conformance_schema_identity": "29d7b0f97008ad38e64b8e966f398d829a66299ec805290ebbec3f92848efab6",
        "constructor_contract_identity": "e42f4741ddab7a6acbdd16f34804cd55408ca5a5428433be3c55eb9b74163c5a",
        "constructor_implementation_identity": "caf85ada6fcd296d3798b5d47838d7b8a39d029dac5f6ecae68ace58712b9d61",
        "source_sha256": SOURCE_SHA256, "source_byte_length": len(source_bytes), "declaration_sha256": DECLARATION_SHA256,
        "source_commitment": source_commitment, "rights_instrument_identity": rights_identity,
        "immutable_archive_commitment": archive_commitment, "prospective_git_blob_oid_sha1": source_blob,
        "source_package_identity": source_package_identity, "factual_authority_envelope": envelope,
        "factual_authority_envelope_identity": envelope_identity,
        "family_independence_identity": independence["family_independence_identity"],
        "family_identities": {
            "source_family": source_family, "event_family": event_family, "authority_family": authority_family,
            "topic_entity_family": topic_family, "revision_family": revision_family, "family_closure": family_closure,
            "creative_premise_family_id": "UNASSIGNED", "construction_revision_family_id": "UNASSIGNED",
            "creative_marker_family_id": "UNASSIGNED",
        },
        "partition": "DEVELOPMENT", "prospective_partition_identity": partition_identity,
        "selected_proposition": "UNASSIGNED", "target_mechanism": "UNASSIGNED", "operational_obligation": "UNASSIGNED",
        "proposition_sufficiency_evaluated": False, "constructor_source_compatibility_evaluated": False,
        "fragment_denyset_identity": "UNASSIGNED_NOT_DERIVED", "fragment_collision_evaluated": False,
        "archive_write": False, "git_archival": False, "ingested": False, "g01a_admitted": False, "g01b_admitted": False,
        "authority_matrix": {key: False for key in (
            "custodial_signing", "immutable_ingestion", "archive_write", "g01a_admission", "g01b_admission",
            "proposition_sufficiency_evaluation", "assignment", "constructor_source_compatibility_evaluation",
            "constructor_release", "construction", "fragment_collision_evaluation", "g04b_pool_certification",
            "model_exposure", "training", "runtime_integration", "production_routing",
        )},
    }
    prospective = {**prospective_core, "preingestion_identity": seal("B2_DEVELOPMENT_PILOT09_PREINGESTION_V1", prospective_core)}
    operations = [
        ("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"], rights_identity),
        ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], source_package_identity),
        ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], archive_commitment),
        ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"], family_closure),
        ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"], partition_identity),
        ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"], prospective["preingestion_identity"]),
    ]
    records = [{"ordinal": i, "purpose": purpose, "object_identity": obj, "required_signer_roles": roles, "distinct_signers_required": len(roles) > 1} for i, (purpose, roles, obj) in enumerate(operations)]
    packet_core = {
        "preingestion_identity": prospective["preingestion_identity"], "source_sha256": SOURCE_SHA256,
        "declaration_sha256": DECLARATION_SHA256, "registration_identity": REGISTRATION_IDENTITY,
        "prior_ledger_head": LEDGER_HEAD, "operations": records, "atomic": True,
    }
    packet_identity = seal("B2_DEVELOPMENT_PILOT09_SIGNING_PACKET_V1", packet_core)
    registration = git_json("docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json")
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    requests = []
    for operation in records:
        for role in operation["required_signer_roles"]:
            challenge_core = {
                "domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT09_PREINGESTION_V1", "purpose": operation["purpose"],
                "role": role, "principal_identity": principals[role], "object_identity": operation["object_identity"],
                "packet_identity": packet_identity, "source_sha256": SOURCE_SHA256,
                "declaration_sha256": DECLARATION_SHA256, "preingestion_identity": prospective["preingestion_identity"],
                "nonce": seal("B2_PILOT09_SIGNING_NONCE_V1", {"packet": packet_identity, "ordinal": operation["ordinal"], "role": role}),
                "prior_ledger_head": LEDGER_HEAD, "grants_operational_content_access": False,
            }
            challenge = {**challenge_core, "challenge_identity": seal("B2_PILOT09_SIGNING_CHALLENGE_V1", challenge_core)}
            requests.append({"operation_ordinal": operation["ordinal"], "purpose": operation["purpose"], "role": role, "challenge": challenge, "signature_status": "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION"})
    require(len(requests) == 8, "requests")
    packet = {
        "schema_name": "batch2-development-pilot09-custodial-signing-packet-v1", "schema_version": "1.0.0",
        "packet_core": packet_core, "packet_identity": packet_identity, "signature_requests": requests,
        "status": "UNSIGNED", "signatures_present": 0, "source_ingested": False, "archive_written": False,
        "ledger_events_appended": 0, "proposition_sufficiency_evaluated": False,
        "constructor_source_compatibility_or_release_performed": False, "fragment_collision_evaluation_performed": False,
    }
    write("humor-mechanics-batch2-development-pilot09-preingestion-v1.json", prospective)
    write("humor-mechanics-batch2-development-pilot09-family-independence-v1.json", independence)
    write("humor-mechanics-batch2-development-pilot09-signing-packet-v1.json", packet)
    print(json.dumps({
        "preparation_verdict": "PASS_UNSIGNED_PREPARATION", "preingestion_identity": prospective["preingestion_identity"],
        "source_commitment": source_commitment, "rights_identity": rights_identity,
        "archive_commitment": archive_commitment, "source_package_identity": source_package_identity,
        "authority_envelope_identity": envelope_identity, "family_independence_identity": independence["family_independence_identity"],
        "family_closure": family_closure, "partition_identity": partition_identity,
        "signing_packet_identity": packet_identity, "signature_requests": len(requests),
    }, sort_keys=True))


if __name__ == "__main__":
    main()

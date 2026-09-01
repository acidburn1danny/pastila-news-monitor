"""Derive Pilot 08 prospective identities and freeze an unsigned signing packet."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot08-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot08-v1.json"
VALIDATION_COMMIT = "084c74ece46851f9d8ba2beb72aecd487cafbf23"
VALIDATION_IDENTITY = "cb3e5037ff983b64122313cbb49ed0005f366cda24657de25aef99f5116bee89"
SOURCE_SHA256 = "d2a71300c1d1832f68132e4b824714ec0bc51beecf26f750146befb00a26712a"
DECLARATION_SHA256 = "7a7da131c60d7a2e1aece6804edd5c7256dca15e534cf3cac3205ebdf39b74b4"
LEDGER_HEAD = "c065bb2c17c3d84e1c76ae25beb2f40934e911acc6653188ebc603ac642d5b98"
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
    return {
        "character_coordinates": [start, end],
        "utf8_byte_coordinates": [len(source[:start].encode()), len(source[:end].encode())],
        "sha256": sha256(source[start:end].encode()),
    }


def component(source: str, words: list[tuple[int, int]], start: int, end: int) -> dict[str, Any]:
    return coordinates(source, words[start][0], words[end - 1][1])


def proposition(
    identifier: str,
    source: str,
    start: int,
    end: int,
    subject: tuple[int, int],
    predicate: tuple[int, int],
    obj: tuple[int, int],
    qualification: tuple[int, int] | None,
    time: str,
    known_boundary: str = "ONLY_THE_EXACT_BOUND_PROPOSITION",
    unknown_boundary: str = "ALL_UNSTATED_PROPERTIES_CAUSES_RESULTS_AND_REAL_WORLD_APPLICABILITY",
) -> dict[str, Any]:
    words = [(start + match.start(), start + match.end()) for match in re.finditer(r"\S+", source[start:end])]
    return {
        "proposition_id": identifier,
        "supporting_span": {
            **coordinates(source, start, end),
            "span_sha256": sha256(source[start:end].encode()),
        },
        "subject": component(source, words, *subject),
        "predicate": component(source, words, *predicate),
        "object": component(source, words, *obj),
        "modality": "ASSERTED",
        "qualification": component(source, words, *qualification) if qualification else None,
        "time": time,
        "scope": "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY",
        "attribution": "OWNER_AUTHORED_SOURCE",
        "known_boundary": known_boundary,
        "unknown_boundary": unknown_boundary,
        "prohibited_inferences": [
            "NO_REAL_WORLD_ASSERTION",
            "NO_UNSTATED_CAUSAL_INFERENCE",
            "NO_UNSTATED_PERSON_INTENT_OR_INTERNAL_STATE_INFERENCE",
            "NO_UNSTATED_DEFECT_INTERVENTION_REPLACEMENT_OR_OTHER_SECTOR_INFERENCE",
        ],
        "quotation_status": "NO_QUOTATION",
        "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC",
    }


def write_json(name: str, value: dict[str, Any]) -> None:
    path = ARTIFACTS / name
    require(not path.exists(), f"artifact already exists: {name}")
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == VALIDATION_COMMIT, "HEAD differs from validation commit")
    validation = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot08-strict-preingestion-validation-v1.json")
    require(validation["validation_identity"] == VALIDATION_IDENTITY, "validation identity")
    require(validation["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY", "validation verdict")
    require(validation["deterministic_blockers"] == [], "validation blockers")
    require(validation["proposition_sufficiency_evaluated"] is False, "proposition sufficiency")

    source_bytes = SOURCE.read_bytes()
    declaration_bytes = DECLARATION.read_bytes()
    require(sha256(source_bytes) == SOURCE_SHA256, "source hash")
    require(sha256(declaration_bytes) == DECLARATION_SHA256, "declaration hash")
    source = source_bytes.decode("utf-8")
    declaration = json.loads(declaration_bytes)
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-08", "pilot")

    sentence_spans = []
    for match in re.finditer(r"[^.!?]+[.!?]", source, re.S):
        raw = match.group()
        leading = len(raw) - len(raw.lstrip())
        sentence_spans.append((match.start() + leading, match.end()))
    require(len(sentence_spans) == 7, "seven sentences")
    propositions = [
        proposition("P1", source, *sentence_spans[0], (6, 12), (12, 16), (16, 23), (0, 6), "EXPLICIT_2026_09_16_MORNING"),
        proposition("P2", source, *sentence_spans[1], (0, 1), (1, 3), (3, 8), (8, 23), "EXPLICIT_2026_09_16_07_00_TO_11_30"),
        proposition("P3", source, *sentence_spans[2], (0, 1), (1, 2), (2, 6), (6, 8), "GENERAL_SYSTEM_STRUCTURE_FOR_STATED_EVENT"),
        proposition("P4", source, *sentence_spans[3], (3, 4), (4, 13), (13, 23), (0, 3), "DURING_THE_STATED_VERIFICATION"),
        proposition(
            "P5", source, *sentence_spans[4], (0, 6), (6, 8), (8, 22), (0, 6), "CONDITIONAL_DURING_THE_STATED_VERIFICATION",
            "RECORDING_AND_LATER_CHECK_OCCUR_ONLY_IF_A_ZONE_DOES_NOT_RESPOND_CORRECTLY",
            "NO_ASSERTION_THAT_ANY_ZONE_WILL_FAIL_OR_WHICH_COMPONENT_IF_ANY_IS_DEFECTIVE",
        ),
        proposition(
            "P6", source, *sentence_spans[5], (0, 4), (4, 6), (6, 9), (9, 18), "EXPLICIT_2026_09_16_SCOPE",
            "WORK_IS_LIMITED_TO_THE_EASTERN_SECTOR_AND_EXCLUDES_OTHER_PARK_ZONES",
            "NO_ASSERTION_ABOUT_WORK_OR_SYSTEM_STATE_OUTSIDE_THE_EASTERN_SECTOR",
        ),
        proposition(
            "P7", source, *sentence_spans[6], (0, 4), (4, 7), (7, 21), (0, 4), "BEFORE_THE_STATED_VERIFICATION",
            "DEFECT_DISCOVERY_AND_COMPONENT_REPLACEMENT_ARE_EXPLICITLY_UNKNOWN_BEFORE_VERIFICATION",
            "NO_ASSERTION_THAT_DEFECTS_WILL_BE_FOUND_OR_ANY_COMPONENT_WILL_REQUIRE_REPLACEMENT",
        ),
    ]

    metadata = declaration["source"]
    source_commitment = seal("B2_OWNED_SOURCE_COMMITMENT_V1", {
        "sha256": SOURCE_SHA256,
        "byte_length": len(source_bytes),
        "encoding": "UTF-8",
        "source_version": metadata["source_version"],
        "capture_timestamp": metadata["capture_timestamp"],
    })
    rights_identity = seal("B2_INTERNALLY_OWNED_RIGHTS_INSTRUMENT_PROSPECTIVE_V1", {
        "declaration_sha256": DECLARATION_SHA256,
        "owner_identity": declaration["contributor"]["public_identity"],
        "grants": declaration["independent_grants"],
        "rights_terms": declaration["rights_terms"],
    })
    envelope = {
        "source_commitment": source_commitment,
        "source_sha256": SOURCE_SHA256,
        "world_scope": metadata["world_scope"],
        "authority_scope": metadata["authority_scope"],
        "propositions": propositions,
        "creative_premise_family_id": "UNASSIGNED",
    }
    envelope_identity = seal("B2_FACTUAL_AUTHORITY_ENVELOPE_PROSPECTIVE_V1", envelope)
    source_blob = git_blob_oid(source_bytes)
    archive_commitment = seal("B2_IMMUTABLE_ARCHIVE_COMMITMENT_PROSPECTIVE_V1", {
        "source_commitment": source_commitment,
        "source_sha256": SOURCE_SHA256,
        "byte_length": len(source_bytes),
        "prospective_git_blob_oid_sha1": source_blob,
        "write_status": "NOT_WRITTEN",
    })

    admissions = [
        git_json(f"docs/artifacts/humor-mechanics-batch2-development-pilot0{index}-g01a-g01b-admission-v1.json")
        for index in range(1, 8)
    ]
    prior_hashes = [item["g01a"]["source_sha256"] for item in admissions]
    prior_blobs = [item["g01a"]["source_git_object"] for item in admissions]
    independence_core = {
        "schema_name": "batch2-development-pilot08-family-independence-v1",
        "schema_version": "1.0.0",
        "pilot08_source_sha256": SOURCE_SHA256,
        "prior_source_sha256": prior_hashes,
        "prior_family_identities": {
            f"pilot0{index}": item["g01b"]["family_identities"]
            for index, item in enumerate(admissions, 1)
        },
        "pilot08_topology": [
            "SYNTHETIC_MUNICIPAL_PARK_IRRIGATION_MAINTENANCE",
            "EXPLICIT_MAINTENANCE_INTERVAL",
            "SIX_INDEPENDENT_VEGETATION_ZONES",
            "COMMAND_RESPONSE_VERIFICATION",
            "CONDITIONAL_DEFECT_RECORDING_AND_COMPONENT_CHECK",
            "EASTERN_SECTOR_ONLY",
            "DEFECT_AND_REPLACEMENT_OUTCOMES_UNKNOWN",
        ],
        "source_hash_distinct": SOURCE_SHA256 not in prior_hashes,
        "git_blob_distinct": source_blob not in prior_blobs,
        "exact_prior_line_reuse": False,
        "source_event_topic_revision_sibling_syndication_same_event_relation": False,
        "prior_target_obligation_selected_proposition_creative_premise_or_marker_assignment": False,
        "prior_construction_model_training_runtime_or_production_exposure": False,
        "blind_family_access": False,
        "selected_or_shaped_using_governance_obligation_sufficiency_target_gap_pool_confound_prior_candidate_or_marker": False,
        "result": "PASS_FRESH_FAMILY_INDEPENDENCE",
    }
    independence = {
        **independence_core,
        "family_independence_identity": seal("B2_DEVELOPMENT_PILOT08_FAMILY_INDEPENDENCE_V1", independence_core),
    }
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {
        "pilot_id": declaration["pilot_id"],
        "event_class": "OWNER_AUTHORED_SYNTHETIC_MUNICIPAL_PARK_IRRIGATION_MAINTENANCE",
    })
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {
        "rights_identity": rights_identity,
        "authority_envelope_identity": envelope_identity,
    })
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {
        "subject_class": metadata["subject_class"],
        "topic_entity_class": "SYNTHETIC_MUNICIPAL_PARK_IRRIGATION_SYSTEM_MAINTENANCE",
    })
    revision_family = seal("B2_REVISION_FAMILY_V1", {
        "source_family": source_family,
        "source_version": metadata["source_version"],
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
        "construction_revision_family": "UNASSIGNED",
        "creative_marker_family": "UNASSIGNED",
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

    authority_matrix = {
        key: False
        for key in (
            "custodial_signing",
            "immutable_ingestion",
            "archive_write",
            "g01a_admission",
            "g01b_admission",
            "proposition_sufficiency_evaluation",
            "assignment",
            "constructor_implementation",
            "constructor_release",
            "construction",
            "fragment_collision_evaluation",
            "g04b_pool_certification",
            "model_exposure",
            "training",
            "runtime_integration",
            "production_routing",
        )
    }
    prospective_core = {
        "schema_name": "batch2-development-pilot08-preingestion-v1",
        "schema_version": "1.0.0",
        "status": "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED",
        "validation_commit": VALIDATION_COMMIT,
        "validation_identity": VALIDATION_IDENTITY,
        "governance_identity": "cc86204c6f199c80ef7c7bf87a58cf3c62d17acb1fe14bd2666bbf5ba86692f6",
        "conformance_schema_identity": "12c96a72555a26181abd5d0e7fa033a425fdacafb3a7fb197a21b39358da1dbe",
        "source_sha256": SOURCE_SHA256,
        "source_byte_length": len(source_bytes),
        "declaration_sha256": DECLARATION_SHA256,
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
            "construction_revision_family_id": "UNASSIGNED",
            "creative_marker_family_id": "UNASSIGNED",
        },
        "partition": "DEVELOPMENT",
        "prospective_partition_identity": partition_identity,
        "selected_proposition": "UNASSIGNED",
        "target_mechanism": "UNASSIGNED",
        "operational_obligation": "UNASSIGNED",
        "proposition_sufficiency_evaluated": False,
        "constructor_v1_status": "HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_RELEASE",
        "future_constructor_implementation_identity": "UNASSIGNED",
        "fragment_denyset_identity": "UNASSIGNED_NOT_DERIVED",
        "fragment_collision_evaluated": False,
        "archive_write": False,
        "git_archival": False,
        "ingested": False,
        "g01a_admitted": False,
        "g01b_admitted": False,
        "g04b_pool_certification_performed": False,
        "authority_matrix": authority_matrix,
    }
    prospective = {
        **prospective_core,
        "preingestion_identity": seal("B2_DEVELOPMENT_PILOT08_PREINGESTION_V1", prospective_core),
    }

    operations = [
        ("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"], rights_identity),
        ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], source_package_identity),
        ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], archive_commitment),
        ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"], family_closure),
        ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"], partition_identity),
        ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"], prospective["preingestion_identity"]),
    ]
    records = [
        {
            "ordinal": ordinal,
            "purpose": purpose,
            "object_identity": object_identity,
            "required_signer_roles": roles,
            "distinct_signers_required": len(roles) > 1,
        }
        for ordinal, (purpose, roles, object_identity) in enumerate(operations)
    ]
    packet_core = {
        "preingestion_identity": prospective["preingestion_identity"],
        "source_sha256": SOURCE_SHA256,
        "declaration_sha256": DECLARATION_SHA256,
        "registration_identity": REGISTRATION_IDENTITY,
        "prior_ledger_head": LEDGER_HEAD,
        "operations": records,
        "atomic": True,
    }
    packet_identity = seal("B2_DEVELOPMENT_PILOT08_SIGNING_PACKET_V1", packet_core)
    registration = git_json("docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json")
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    requests = []
    for operation in records:
        for role in operation["required_signer_roles"]:
            challenge_core = {
                "domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT08_PREINGESTION_V1",
                "purpose": operation["purpose"],
                "role": role,
                "principal_identity": principals[role],
                "object_identity": operation["object_identity"],
                "packet_identity": packet_identity,
                "source_sha256": SOURCE_SHA256,
                "declaration_sha256": DECLARATION_SHA256,
                "preingestion_identity": prospective["preingestion_identity"],
                "nonce": seal("B2_PILOT08_SIGNING_NONCE_V1", {
                    "packet": packet_identity,
                    "ordinal": operation["ordinal"],
                    "role": role,
                }),
                "prior_ledger_head": LEDGER_HEAD,
                "grants_operational_content_access": False,
            }
            challenge = {
                **challenge_core,
                "challenge_identity": seal("B2_PILOT08_SIGNING_CHALLENGE_V1", challenge_core),
            }
            requests.append({
                "operation_ordinal": operation["ordinal"],
                "purpose": operation["purpose"],
                "role": role,
                "challenge": challenge,
                "signature_status": "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION",
            })
    require(len(requests) == 8, "signature request count")
    packet = {
        "schema_name": "batch2-development-pilot08-custodial-signing-packet-v1",
        "schema_version": "1.0.0",
        "packet_core": packet_core,
        "packet_identity": packet_identity,
        "signature_requests": requests,
        "status": "UNSIGNED",
        "signatures_present": 0,
        "source_ingested": False,
        "archive_written": False,
        "ledger_events_appended": 0,
        "proposition_sufficiency_evaluated": False,
        "constructor_implementation_or_release_performed": False,
        "fragment_collision_evaluation_performed": False,
    }

    write_json("humor-mechanics-batch2-development-pilot08-preingestion-v1.json", prospective)
    write_json("humor-mechanics-batch2-development-pilot08-family-independence-v1.json", independence)
    write_json("humor-mechanics-batch2-development-pilot08-signing-packet-v1.json", packet)
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

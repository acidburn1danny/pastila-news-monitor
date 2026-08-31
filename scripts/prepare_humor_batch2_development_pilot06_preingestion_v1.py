"""Derive Pilot 06 prospective identities and freeze an unsigned signing packet."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot06-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot06-v1.json"
VALIDATION_COMMIT = "7a21268129154200251a74155196c0bd479347ac"
VALIDATION_ID = "8c422ad86a4904485e4b854bc6341a917d6e9598521a50955fcc9bfce0a126d5"
SOURCE_SHA = "eb97e6bdffc809d0902f90bb26b95c3c4a6047476b27eec7ac46b613dba030ad"
DECLARATION_SHA = "9612cd4e0b58b752636b83dfcab28f2e0c4eb208981f52b6b34f9295526050c4"
LEDGER_HEAD = "20d5c36ec01ceaec6cd85131f6253bbd300f710021804ce3debf7d3880bc59b2"
REGISTRATION_ID = "01912e139471ec23cba5861c8f575f098a6248d39ebbe5ec2ee043493d392ebe"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def blob_oid(value: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def git_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{VALIDATION_COMMIT}:{path}"], cwd=ROOT))


def component(source: str, words: list[tuple[int, int]], start: int, end: int) -> dict[str, Any]:
    cs, ce = words[start][0], words[end - 1][1]
    return {"character_coordinates": [cs, ce], "utf8_byte_coordinates": [len(source[:cs].encode()), len(source[:ce].encode())],
            "sha256": sha(source[cs:ce].encode())}


def proposition(identifier: str, source: str, start: int, end: int, subject: tuple[int, int], predicate: tuple[int, int],
                obj: tuple[int, int], qualification: tuple[int, int] | None = None, time: str = "UNSPECIFIED",
                known: str = "ONLY_THE_EXACT_BOUND_PROPOSITION",
                unknown: str = "ALL_UNSTATED_PROPERTIES_CAUSES_RESULTS_AND_REAL_WORLD_APPLICABILITY") -> dict[str, Any]:
    surface = source[start:end]
    words = [(start + m.start(), start + m.end()) for m in re.finditer(r"\S+", surface)]
    return {"proposition_id": identifier,
            "supporting_span": {"character_coordinates": [start, end],
                                "utf8_byte_coordinates": [len(source[:start].encode()), len(source[:end].encode())],
                                "span_sha256": sha(surface.encode())},
            "subject": component(source, words, *subject), "predicate": component(source, words, *predicate),
            "object": component(source, words, *obj),
            "modality": "ASSERTED", "qualification": component(source, words, *qualification) if qualification else None,
            "time": time, "scope": "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "attribution": "OWNER_AUTHORED_SOURCE",
            "known_boundary": known, "unknown_boundary": unknown,
            "prohibited_inferences": ["NO_REAL_WORLD_ASSERTION", "NO_UNSTATED_CAUSAL_INFERENCE",
                                      "NO_UNSTATED_PERSON_INTENT_OR_INTERNAL_STATE_INFERENCE", "NO_UNSTATED_ATTENDANCE_OR_DEMAND_INFERENCE"],
            "quotation_status": "OWNER_AUTHORED_REGISTER_LABEL_NOT_THIRD_PARTY_QUOTATION",
            "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC"}


def write(name: str, value: Any) -> None:
    path = ART / name
    require(not path.exists(), f"already exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == VALIDATION_COMMIT, "HEAD")
    validation = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot06-strict-preingestion-validation-v1.json")
    require(validation["validation_identity"] == VALIDATION_ID and validation["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY", "validation")
    require(validation["proposition_sufficiency_evaluated"] is False, "sufficiency boundary")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(sha(source_bytes) == SOURCE_SHA and sha(declaration_bytes) == DECLARATION_SHA, "owner input hash")
    source, declaration = source_bytes.decode(), json.loads(declaration_bytes)
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-06", "pilot")
    lines = source.splitlines(keepends=True)
    require(len(lines) == 6, "source lines")
    starts, cursor = [], 0
    for line in lines:
        starts.append(cursor); cursor += len(line)
    ends = [starts[i] + len(lines[i].rstrip("\n")) for i in range(6)]
    propositions = [
        proposition("P1", source, starts[0], ends[0], (0, 2), (2, 3), (3, 16), (3, 7), "EXPLICIT_2026_09_12"),
        proposition("P2", source, starts[1], ends[1], (0, 1), (1, 2), (2, 11), None, "EXPLICIT_2026_09_12_09_30_TO_14_00"),
        proposition("P3", source, starts[2], ends[2], (3, 6), (6, 7), (7, 16), (0, 3), "DURING_THE_STATED_SESSION"),
        proposition("P4", source, starts[3], ends[3], (0, 4), (4, 7), (7, 10), None, "DURING_OR_AFTER_THE_STATED_SESSION"),
        proposition("P5", source, starts[4], ends[4], (0, 4), (4, 6), (6, 13), None, "THE_STATED_DAY",
                    "PHOTOGRAPH_AND_PRESS_ARCHIVE_COLLECTIONS_EXCLUDED_FROM_THIS_INVENTORY",
                    "ALL_OTHER_COLLECTION_STATUS_AND_UNSTATED_PROPERTIES_UNKNOWN"),
        proposition("P6", source, starts[5], ends[5], (6, 9), (3, 6), (6, 9), (0, 3), "AT_SESSION_END",
                    "NEXT_INVENTORY_DATE_NOT_ESTABLISHED",
                    "NEXT_INVENTORY_DATE_AND_ALL_UNSTATED_PROPERTIES_CAUSES_RESULTS_AND_REAL_WORLD_APPLICABILITY_UNKNOWN"),
    ]
    meta = declaration["source"]
    source_commitment = seal("B2_OWNED_SOURCE_COMMITMENT_V1", {"sha256": SOURCE_SHA, "byte_length": len(source_bytes),
                              "encoding": "UTF-8", "source_version": meta["source_version"], "capture_timestamp": meta["capture_timestamp"]})
    rights_identity = seal("B2_INTERNALLY_OWNED_RIGHTS_INSTRUMENT_PROSPECTIVE_V1", {"declaration_sha256": DECLARATION_SHA,
                           "owner_identity": declaration["contributor"]["public_identity"], "grants": declaration["independent_grants"],
                           "rights_terms": declaration["rights_terms"]})
    envelope = {"source_commitment": source_commitment, "source_sha256": SOURCE_SHA, "world_scope": meta["world_scope"],
                "authority_scope": meta["authority_scope"], "propositions": propositions, "creative_premise_family_id": "UNASSIGNED"}
    envelope_identity = seal("B2_FACTUAL_AUTHORITY_ENVELOPE_PROSPECTIVE_V1", envelope)
    source_blob = blob_oid(source_bytes)
    archive_commitment = seal("B2_IMMUTABLE_ARCHIVE_COMMITMENT_PROSPECTIVE_V1", {"source_commitment": source_commitment,
                              "source_sha256": SOURCE_SHA, "byte_length": len(source_bytes),
                              "prospective_git_blob_oid_sha1": source_blob, "write_status": "NOT_WRITTEN"})
    admissions = [git_json(f"docs/artifacts/humor-mechanics-batch2-development-pilot0{i}-g01a-g01b-admission-v1.json") for i in range(1, 6)]
    prior_hashes = [item["g01a"]["source_sha256"] for item in admissions]
    prior_blobs = [item["g01a"]["source_git_object"] for item in admissions]
    independence_core = {"schema_name": "batch2-development-pilot06-family-independence-v1", "schema_version": "1.0.0",
                         "pilot06_source_sha256": SOURCE_SHA, "prior_source_sha256": prior_hashes,
                         "prior_family_identities": {f"pilot0{i}": item["g01b"]["family_identities"] for i, item in enumerate(admissions, 1)},
                         "pilot06_topology": ["SYNTHETIC_LIBRARY_MAP_INVENTORY", "FIXED_SESSION_WINDOW", "VERIFICATION_REGISTER_ENTRY",
                                              "RESTORATION_EVALUATION_NOTATION", "EXCLUDED_COLLECTIONS", "NEXT_INVENTORY_DATE_UNKNOWN"],
                         "source_hash_distinct": SOURCE_SHA not in prior_hashes, "git_blob_distinct": source_blob not in prior_blobs,
                         "exact_prior_line_reuse": False, "source_event_topic_revision_sibling_syndication_same_event_relation": False,
                         "prior_target_obligation_selected_proposition_or_creative_premise_assignment": False,
                         "prior_construction_model_training_runtime_or_production_exposure": False, "blind_family_access": False,
                         "selected_or_shaped_using_governance_obligation_sufficiency_target_gap_pool_confound_or_prior_candidate": False,
                         "result": "PASS_FRESH_FAMILY_INDEPENDENCE"}
    independence = {**independence_core, "family_independence_identity": seal("B2_DEVELOPMENT_PILOT06_FAMILY_INDEPENDENCE_V1", independence_core)}
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {"pilot_id": declaration["pilot_id"], "event_class": "OWNER_AUTHORED_SYNTHETIC_LIBRARY_INVENTORY"})
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {"rights_identity": rights_identity, "authority_envelope_identity": envelope_identity})
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {"subject_class": meta["subject_class"], "topic_entity_class": "SYNTHETIC_LIBRARY_MAP_COLLECTION_INVENTORY"})
    revision_family = seal("B2_REVISION_FAMILY_V1", {"source_family": source_family, "source_version": meta["source_version"], "supersedes": None})
    family_closure = seal("B2_FAMILY_CLOSURE_PROSPECTIVE_V1", {"source": source_family, "event": event_family, "authority": authority_family,
                          "topic_entity": topic_family, "revision": revision_family,
                          "family_independence_identity": independence["family_independence_identity"], "creative_premise": "UNASSIGNED"})
    partition_identity = seal("B2_DEVELOPMENT_PARTITION_SEAL_PROSPECTIVE_V1", {"family_closure": family_closure,
                              "partition": "DEVELOPMENT", "curriculum_candidate": False, "blind_evaluation": False})
    source_package_identity = seal("B2_SOURCE_PACKAGE_PROSPECTIVE_V1", {"source_commitment": source_commitment,
                                   "archive_commitment": archive_commitment, "rights_identity": rights_identity,
                                   "authority_envelope_identity": envelope_identity, "family_closure": family_closure,
                                   "partition_identity": partition_identity, "status": "NOT_INGESTED_NOT_ARCHIVED"})
    prospective_core = {"schema_name": "batch2-development-pilot06-preingestion-v1", "schema_version": "1.0.0",
                        "status": "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED", "validation_commit": VALIDATION_COMMIT,
                        "validation_identity": VALIDATION_ID, "source_sha256": SOURCE_SHA, "source_byte_length": len(source_bytes),
                        "declaration_sha256": DECLARATION_SHA, "source_commitment": source_commitment,
                        "rights_instrument_identity": rights_identity, "immutable_archive_commitment": archive_commitment,
                        "prospective_git_blob_oid_sha1": source_blob, "source_package_identity": source_package_identity,
                        "factual_authority_envelope": envelope, "factual_authority_envelope_identity": envelope_identity,
                        "family_independence_identity": independence["family_independence_identity"],
                        "family_identities": {"source_family": source_family, "event_family": event_family, "authority_family": authority_family,
                                              "topic_entity_family": topic_family, "revision_family": revision_family,
                                              "family_closure": family_closure, "creative_premise_family_id": "UNASSIGNED"},
                        "partition": "DEVELOPMENT", "prospective_partition_identity": partition_identity,
                        "selected_proposition": "UNASSIGNED", "target_mechanism": "UNASSIGNED", "operational_obligation": "UNASSIGNED",
                        "proposition_sufficiency_evaluated": False,
                        "proposition_sufficiency_timing": "ONLY_AFTER_G01A_AND_G01B_PASS_BEFORE_ASSIGNMENT",
                        "archive_write": False, "git_archival": False, "ingested": False, "g01a_admitted": False, "g01b_admitted": False,
                        "g04b_pool_certification_performed": False,
                        "authority_matrix": {key: False for key in ("custodial_signing", "immutable_ingestion", "archive_write", "g01a_admission",
                                                                     "g01b_admission", "proposition_sufficiency_evaluation", "assignment",
                                                                     "constructor_release", "construction", "g04b_pool_certification", "model_exposure",
                                                                     "training", "runtime_integration", "production_routing")}}
    prospective = {**prospective_core, "preingestion_identity": seal("B2_DEVELOPMENT_PILOT06_PREINGESTION_V1", prospective_core)}
    operations = [("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"], rights_identity),
                  ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], source_package_identity),
                  ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], archive_commitment),
                  ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"], family_closure),
                  ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"], partition_identity),
                  ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"], prospective["preingestion_identity"])]
    records = [{"ordinal": i, "purpose": purpose, "object_identity": obj, "required_signer_roles": roles,
                "distinct_signers_required": len(roles) > 1} for i, (purpose, roles, obj) in enumerate(operations)]
    packet_core = {"preingestion_identity": prospective["preingestion_identity"], "source_sha256": SOURCE_SHA,
                   "declaration_sha256": DECLARATION_SHA, "registration_identity": REGISTRATION_ID,
                   "prior_ledger_head": LEDGER_HEAD, "operations": records, "atomic": True}
    packet_identity = seal("B2_DEVELOPMENT_PILOT06_SIGNING_PACKET_V1", packet_core)
    registration = git_json("docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json")
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    requests = []
    for operation in records:
        for role in operation["required_signer_roles"]:
            challenge_core = {"domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT06_PREINGESTION_V1", "purpose": operation["purpose"],
                              "role": role, "principal_identity": principals[role], "object_identity": operation["object_identity"],
                              "packet_identity": packet_identity, "source_sha256": SOURCE_SHA, "declaration_sha256": DECLARATION_SHA,
                              "preingestion_identity": prospective["preingestion_identity"],
                              "nonce": seal("B2_PILOT06_SIGNING_NONCE_V1", {"packet": packet_identity, "ordinal": operation["ordinal"], "role": role}),
                              "prior_ledger_head": LEDGER_HEAD, "grants_operational_content_access": False}
            challenge = {**challenge_core, "challenge_identity": seal("B2_PILOT06_SIGNING_CHALLENGE_V1", challenge_core)}
            requests.append({"operation_ordinal": operation["ordinal"], "purpose": operation["purpose"], "role": role,
                             "challenge": challenge, "signature_status": "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION"})
    packet = {"schema_name": "batch2-development-pilot06-custodial-signing-packet-v1", "schema_version": "1.0.0",
              "packet_core": packet_core, "packet_identity": packet_identity, "signature_requests": requests, "status": "UNSIGNED",
              "signatures_present": 0, "source_ingested": False, "archive_written": False, "ledger_events_appended": 0,
              "proposition_sufficiency_evaluated": False}
    write("humor-mechanics-batch2-development-pilot06-preingestion-v1.json", prospective)
    write("humor-mechanics-batch2-development-pilot06-family-independence-v1.json", independence)
    write("humor-mechanics-batch2-development-pilot06-signing-packet-v1.json", packet)
    print(json.dumps({"preparation_verdict": "PASS_UNSIGNED_PREPARATION", "preingestion_identity": prospective["preingestion_identity"],
                      "source_commitment": source_commitment, "rights_identity": rights_identity,
                      "archive_commitment": archive_commitment, "source_package_identity": source_package_identity,
                      "authority_envelope_identity": envelope_identity, "family_independence_identity": independence["family_independence_identity"],
                      "family_closure": family_closure, "partition_identity": partition_identity,
                      "signing_packet_identity": packet_identity, "signature_requests": len(requests)}, sort_keys=True))


if __name__ == "__main__":
    main()

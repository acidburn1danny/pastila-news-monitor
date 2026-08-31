"""Derive Pilot 07 prospective identities and freeze an unsigned signing packet."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot07-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot07-v1.json"
COMMIT = "c65228bf32537a78dac0db78b38e742956e9e072"
VALIDATION_ID = "c76bcf9831131e74a6ecb407d0305db07d42d3aff735c5c5ce233ad15952ea08"
SOURCE_SHA = "eaeb78b44b28cc399037892bd31cb82e914573e464ef938dd183736cd03247be"
DECLARATION_SHA = "9c687390c6f34d6bd463e9e59b8b6c9055d7460af7003eaa2fbabe1a57ee2caf"
LEDGER_HEAD = "a92ba489bc32a5b62d3adf48c655703c107dde2ebc241b93cfc95ad39a91548f"
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
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT))


def component(source: str, words: list[tuple[int, int]], start: int, end: int) -> dict[str, Any]:
    cs, ce = words[start][0], words[end - 1][1]
    return {"character_coordinates": [cs, ce], "utf8_byte_coordinates": [len(source[:cs].encode()), len(source[:ce].encode())],
            "sha256": sha(source[cs:ce].encode())}


def proposition(identifier: str, source: str, start: int, end: int, subject: tuple[int, int], predicate: tuple[int, int], obj: tuple[int, int],
                qualification: tuple[int, int] | None, time: str, known: str = "ONLY_THE_EXACT_BOUND_PROPOSITION",
                unknown: str = "ALL_UNSTATED_PROPERTIES_CAUSES_RESULTS_AND_REAL_WORLD_APPLICABILITY") -> dict[str, Any]:
    surface = source[start:end]; words = [(start + m.start(), start + m.end()) for m in re.finditer(r"\S+", surface)]
    return {"proposition_id": identifier,
            "supporting_span": {"character_coordinates": [start, end], "utf8_byte_coordinates": [len(source[:start].encode()), len(source[:end].encode())],
                                "span_sha256": sha(surface.encode())},
            "subject": component(source, words, *subject), "predicate": component(source, words, *predicate), "object": component(source, words, *obj),
            "modality": "ASSERTED", "qualification": component(source, words, *qualification) if qualification else None,
            "time": time, "scope": "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY", "attribution": "OWNER_AUTHORED_SOURCE",
            "known_boundary": known, "unknown_boundary": unknown,
            "prohibited_inferences": ["NO_REAL_WORLD_ASSERTION", "NO_UNSTATED_CAUSAL_INFERENCE", "NO_UNSTATED_PERSON_INTENT_OR_INTERNAL_STATE_INFERENCE",
                                      "NO_UNSTATED_ATTENDANCE_DEMAND_OR_INTERVENTION_INFERENCE"],
            "quotation_status": "NO_QUOTATION", "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC"}


def write(name: str, value: Any) -> None:
    path = ART / name
    require(not path.exists(), "artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    validation = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot07-strict-preingestion-validation-v1.json")
    require(validation["validation_identity"] == VALIDATION_ID and validation["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY", "validation")
    require(validation["proposition_sufficiency_evaluated"] is False, "sufficiency")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(sha(source_bytes) == SOURCE_SHA and sha(declaration_bytes) == DECLARATION_SHA, "owner inputs")
    source, declaration = source_bytes.decode(), json.loads(declaration_bytes)
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-07", "pilot")
    lines = source.splitlines(keepends=True); require(len(lines) == 6, "lines")
    starts, cursor = [], 0
    for line in lines:
        starts.append(cursor); cursor += len(line)
    ends = [starts[i] + len(lines[i].rstrip("\n")) for i in range(6)]
    propositions = [
        proposition("P1", source, starts[0], ends[0], (0, 2), (2, 3), (3, 17), (3, 7), "EXPLICIT_2026_09_14"),
        proposition("P2", source, starts[1], ends[1], (0, 1), (1, 2), (2, 11), (5, 11), "EXPLICIT_2026_09_14_08_45_BEFORE_FIRST_PUBLIC_SCREENING"),
        proposition("P3", source, starts[2], ends[2], (5, 9), (3, 5), (9, 14), (0, 3), "DURING_THE_STATED_TEST"),
        proposition("P4", source, starts[3], ends[3], (0, 1), (1, 3), (3, 13), None, "DURING_THE_STATED_TEST"),
        proposition("P5", source, starts[4], ends[4], (6, 7), (7, 9), (9, 16), (0, 6), "CONDITIONAL_DURING_OR_AFTER_THE_STATED_TEST",
                    "ISSUE_RECORDING_OCCURS_ONLY_IF_A_TECHNICAL_PROBLEM_IS_OBSERVED",
                    "NO_ASSERTION_THAT_A_PROBLEM_WAS_OR_WILL_BE_OBSERVED_OR_THAT_INTERVENTION_IS_REQUIRED"),
        proposition("P6", source, starts[5], ends[5], (0, 1), (1, 3), (3, 13), None, "AFTER_THE_STATED_TEST_UNKNOWN_OUTCOME",
                    "SOURCE_DOES_NOT_ESTABLISH_WHETHER_INTERVENTION_WILL_BE_NEEDED",
                    "INTERVENTION_NECESSITY_AND_ALL_UNSTATED_RESULTS_CAUSES_AND_REAL_WORLD_APPLICABILITY_UNKNOWN"),
    ]
    meta = declaration["source"]
    source_commitment = seal("B2_OWNED_SOURCE_COMMITMENT_V1", {"sha256": SOURCE_SHA, "byte_length": len(source_bytes), "encoding": "UTF-8",
                                                                "source_version": meta["source_version"], "capture_timestamp": meta["capture_timestamp"]})
    rights_identity = seal("B2_INTERNALLY_OWNED_RIGHTS_INSTRUMENT_PROSPECTIVE_V1", {"declaration_sha256": DECLARATION_SHA,
                           "owner_identity": declaration["contributor"]["public_identity"], "grants": declaration["independent_grants"],
                           "rights_terms": declaration["rights_terms"]})
    envelope = {"source_commitment": source_commitment, "source_sha256": SOURCE_SHA, "world_scope": meta["world_scope"],
                "authority_scope": meta["authority_scope"], "propositions": propositions, "creative_premise_family_id": "UNASSIGNED"}
    envelope_identity = seal("B2_FACTUAL_AUTHORITY_ENVELOPE_PROSPECTIVE_V1", envelope)
    source_blob = blob_oid(source_bytes)
    archive_commitment = seal("B2_IMMUTABLE_ARCHIVE_COMMITMENT_PROSPECTIVE_V1", {"source_commitment": source_commitment, "source_sha256": SOURCE_SHA,
                              "byte_length": len(source_bytes), "prospective_git_blob_oid_sha1": source_blob, "write_status": "NOT_WRITTEN"})
    admissions = [git_json(f"docs/artifacts/humor-mechanics-batch2-development-pilot0{i}-g01a-g01b-admission-v1.json") for i in range(1, 7)]
    prior_hashes = [item["g01a"]["source_sha256"] for item in admissions]; prior_blobs = [item["g01a"]["source_git_object"] for item in admissions]
    independence_core = {"schema_name": "batch2-development-pilot07-family-independence-v1", "schema_version": "1.0.0",
                         "pilot07_source_sha256": SOURCE_SHA, "prior_source_sha256": prior_hashes,
                         "prior_family_identities": {f"pilot0{i}": item["g01b"]["family_identities"] for i, item in enumerate(admissions, 1)},
                         "pilot07_topology": ["SYNTHETIC_CINEMA_TECHNICAL_INSPECTION", "PRE_PUBLIC_SCREENING_TIME", "INTERNAL_VIDEO_DURATION",
                                              "THREE_SUBSYSTEM_RECORDS", "CONDITIONAL_ISSUE_RECORDING", "INTERVENTION_OUTCOME_UNKNOWN"],
                         "source_hash_distinct": SOURCE_SHA not in prior_hashes, "git_blob_distinct": source_blob not in prior_blobs,
                         "exact_prior_line_reuse": False, "source_event_topic_revision_sibling_syndication_same_event_relation": False,
                         "prior_target_obligation_selected_proposition_or_creative_premise_assignment": False,
                         "prior_construction_model_training_runtime_or_production_exposure": False, "blind_family_access": False,
                         "selected_or_shaped_using_governance_obligation_sufficiency_target_gap_pool_confound_or_prior_candidate": False,
                         "result": "PASS_FRESH_FAMILY_INDEPENDENCE"}
    independence = {**independence_core, "family_independence_identity": seal("B2_DEVELOPMENT_PILOT07_FAMILY_INDEPENDENCE_V1", independence_core)}
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {"pilot_id": declaration["pilot_id"], "event_class": "OWNER_AUTHORED_SYNTHETIC_CINEMA_TECHNICAL_INSPECTION"})
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {"rights_identity": rights_identity, "authority_envelope_identity": envelope_identity})
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {"subject_class": meta["subject_class"], "topic_entity_class": "SYNTHETIC_CINEMA_PROJECTION_SYSTEM_INSPECTION"})
    revision_family = seal("B2_REVISION_FAMILY_V1", {"source_family": source_family, "source_version": meta["source_version"], "supersedes": None})
    family_closure = seal("B2_FAMILY_CLOSURE_PROSPECTIVE_V1", {"source": source_family, "event": event_family, "authority": authority_family,
                          "topic_entity": topic_family, "revision": revision_family, "family_independence_identity": independence["family_independence_identity"],
                          "creative_premise": "UNASSIGNED"})
    partition_identity = seal("B2_DEVELOPMENT_PARTITION_SEAL_PROSPECTIVE_V1", {"family_closure": family_closure, "partition": "DEVELOPMENT",
                              "curriculum_candidate": False, "blind_evaluation": False})
    source_package_identity = seal("B2_SOURCE_PACKAGE_PROSPECTIVE_V1", {"source_commitment": source_commitment, "archive_commitment": archive_commitment,
                                   "rights_identity": rights_identity, "authority_envelope_identity": envelope_identity, "family_closure": family_closure,
                                   "partition_identity": partition_identity, "status": "NOT_INGESTED_NOT_ARCHIVED"})
    prospective_core = {"schema_name": "batch2-development-pilot07-preingestion-v1", "schema_version": "1.0.0",
                        "status": "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED", "validation_commit": COMMIT, "validation_identity": VALIDATION_ID,
                        "governance_identity": "4848bd025e43eff6652e4c2024072760d372ca4ac7427e5f21e1d2c4bcdb35dc",
                        "source_sha256": SOURCE_SHA, "source_byte_length": len(source_bytes), "declaration_sha256": DECLARATION_SHA,
                        "source_commitment": source_commitment, "rights_instrument_identity": rights_identity,
                        "immutable_archive_commitment": archive_commitment, "prospective_git_blob_oid_sha1": source_blob,
                        "source_package_identity": source_package_identity, "factual_authority_envelope": envelope,
                        "factual_authority_envelope_identity": envelope_identity, "family_independence_identity": independence["family_independence_identity"],
                        "family_identities": {"source_family": source_family, "event_family": event_family, "authority_family": authority_family,
                                              "topic_entity_family": topic_family, "revision_family": revision_family, "family_closure": family_closure,
                                              "creative_premise_family_id": "UNASSIGNED"},
                        "partition": "DEVELOPMENT", "prospective_partition_identity": partition_identity,
                        "selected_proposition": "UNASSIGNED", "target_mechanism": "UNASSIGNED", "operational_obligation": "UNASSIGNED",
                        "proposition_sufficiency_evaluated": False, "archive_write": False, "git_archival": False, "ingested": False,
                        "g01a_admitted": False, "g01b_admitted": False, "g04b_pool_certification_performed": False,
                        "authority_matrix": {key: False for key in ("custodial_signing", "immutable_ingestion", "archive_write", "g01a_admission", "g01b_admission",
                                                                     "proposition_sufficiency_evaluation", "assignment", "constructor_release", "construction",
                                                                     "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")}}
    prospective = {**prospective_core, "preingestion_identity": seal("B2_DEVELOPMENT_PILOT07_PREINGESTION_V1", prospective_core)}
    operations = [("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"], rights_identity),
                  ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], source_package_identity),
                  ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], archive_commitment),
                  ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"], family_closure),
                  ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"], partition_identity),
                  ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"], prospective["preingestion_identity"])]
    records = [{"ordinal": i, "purpose": purpose, "object_identity": obj, "required_signer_roles": roles, "distinct_signers_required": len(roles) > 1}
               for i, (purpose, roles, obj) in enumerate(operations)]
    packet_core = {"preingestion_identity": prospective["preingestion_identity"], "source_sha256": SOURCE_SHA, "declaration_sha256": DECLARATION_SHA,
                   "registration_identity": REGISTRATION_ID, "prior_ledger_head": LEDGER_HEAD, "operations": records, "atomic": True}
    packet_identity = seal("B2_DEVELOPMENT_PILOT07_SIGNING_PACKET_V1", packet_core)
    registration = git_json("docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json")
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    requests = []
    for operation in records:
        for role in operation["required_signer_roles"]:
            challenge_core = {"domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT07_PREINGESTION_V1", "purpose": operation["purpose"], "role": role,
                              "principal_identity": principals[role], "object_identity": operation["object_identity"], "packet_identity": packet_identity,
                              "source_sha256": SOURCE_SHA, "declaration_sha256": DECLARATION_SHA,
                              "preingestion_identity": prospective["preingestion_identity"],
                              "nonce": seal("B2_PILOT07_SIGNING_NONCE_V1", {"packet": packet_identity, "ordinal": operation["ordinal"], "role": role}),
                              "prior_ledger_head": LEDGER_HEAD, "grants_operational_content_access": False}
            challenge = {**challenge_core, "challenge_identity": seal("B2_PILOT07_SIGNING_CHALLENGE_V1", challenge_core)}
            requests.append({"operation_ordinal": operation["ordinal"], "purpose": operation["purpose"], "role": role,
                             "challenge": challenge, "signature_status": "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION"})
    packet = {"schema_name": "batch2-development-pilot07-custodial-signing-packet-v1", "schema_version": "1.0.0",
              "packet_core": packet_core, "packet_identity": packet_identity, "signature_requests": requests, "status": "UNSIGNED",
              "signatures_present": 0, "source_ingested": False, "archive_written": False, "ledger_events_appended": 0,
              "proposition_sufficiency_evaluated": False}
    write("humor-mechanics-batch2-development-pilot07-preingestion-v1.json", prospective)
    write("humor-mechanics-batch2-development-pilot07-family-independence-v1.json", independence)
    write("humor-mechanics-batch2-development-pilot07-signing-packet-v1.json", packet)
    print(json.dumps({"preparation_verdict": "PASS_UNSIGNED_PREPARATION", "preingestion_identity": prospective["preingestion_identity"],
                      "source_commitment": source_commitment, "rights_identity": rights_identity, "archive_commitment": archive_commitment,
                      "source_package_identity": source_package_identity, "authority_envelope_identity": envelope_identity,
                      "family_independence_identity": independence["family_independence_identity"], "family_closure": family_closure,
                      "partition_identity": partition_identity, "signing_packet_identity": packet_identity, "signature_requests": len(requests)}, sort_keys=True))


if __name__ == "__main__":
    main()

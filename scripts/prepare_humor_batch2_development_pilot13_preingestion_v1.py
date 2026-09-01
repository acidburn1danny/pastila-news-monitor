"""Prepare Pilot 13 prospective identities and an unsigned signing packet only."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot13-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot13-v1.json"
VALIDATION_COMMIT = "9f6a8de9f4ae7395fb7173cbad70b6ac9315c109"
VALIDATION_IDENTITY = "38448411de35df15b12cfa5113541820bc21f4812ffe49a3f8b180580a35f7f3"
SOURCE_SHA256 = "9d79b45d06fba5b950f97e7d09f38450177b7ff7d5cbf962a9e4f7af452b6a76"
DECLARATION_SHA256 = "5e18c30cab71ee0ab1e3599e1abc433af3bcebea881d683ed8322387d0d570e3"
LEDGER_HEAD = "cc0493c97949a0426ff7ab9427a45fc23be468a0cac7ebd5732eaef5c96dcf1b"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def blob_oid(value: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def git_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{VALIDATION_COMMIT}:{path}"], cwd=ROOT))


def coords(source: str, start: int, end: int) -> dict[str, Any]:
    value = source[start:end].encode()
    return {"character_coordinates": [start, end], "utf8_byte_coordinates": [len(source[:start].encode()), len(source[:end].encode())], "sha256": sha256(value)}


def located(source: str, span: tuple[int, int], text: str) -> dict[str, Any]:
    start = source.find(text, span[0], span[1])
    require(start >= 0 and source.find(text, start + 1, span[1]) < 0, f"non-unique part: {text}")
    return coords(source, start, start + len(text))


def prop(identifier: str, source: str, span: tuple[int, int], subject: str, predicate: str, obj: str,
         qualification: str | None, time: str, known: str, unknown: str) -> dict[str, Any]:
    start, end = span
    return {"proposition_id": identifier,
            "supporting_span": {**coords(source, start, end), "span_sha256": sha256(source[start:end].encode())},
            "subject": located(source, span, subject), "predicate": located(source, span, predicate),
            "object": located(source, span, obj), "qualification": located(source, span, qualification) if qualification else None,
            "modality": "ASSERTED", "time": time, "scope": "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY",
            "attribution": "OWNER_AUTHORED_SOURCE", "known_boundary": known, "unknown_boundary": unknown,
            "prohibited_inferences": ["NO_REAL_WORLD_ASSERTION", "NO_UNSTATED_CAUSAL_INFERENCE",
                "NO_UNSTATED_PERSON_INTENT_OR_INTERNAL_STATE_INFERENCE", "NO_UNSTATED_SENSOR_POSITION_OR_INSTALLATION_OUTCOME_INFERENCE"],
            "quotation_status": "NO_QUOTATION", "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC"}


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == VALIDATION_COMMIT, "HEAD")
    validation = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot13-strict-preingestion-validation-v1.json")
    require(validation["validation_identity"] == VALIDATION_IDENTITY and validation["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY", "validation")
    require(validation["deterministic_blockers"] == [] and validation["repair_performed"] is False, "validation boundary")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(sha256(source_bytes) == SOURCE_SHA256 and sha256(declaration_bytes) == DECLARATION_SHA256, "owner inputs")
    source, declaration = source_bytes.decode(), json.loads(declaration_bytes)
    spans = [(m.start() + len(m.group()) - len(m.group().lstrip()), m.end()) for m in re.finditer(r"[^.!?]+[.!?]", source, re.S)]
    require(len(spans) == 8, "eight propositions")
    propositions = [
        prop("P1", source, spans[0], "o echipă tehnică", "a pregătit", "18 senzori acustici pentru o campanie de măsurare desfășurată într-o sală de concerte", "În seara de 28 august 2026", "EXPLICIT_2026_08_28_EVENING", "SENSOR_QUANTITY_CAMPAIGN_AND_HALL_PREPARATION", "NO_OTHER_CAMPAIGN_OR_INSTALLATION_FACT"),
        prop("P2", source, spans[1], "Fiecare senzor", "avea un număr de serie și era asociat", "în fișa campaniei cu o poziție numerotată din sală", None, "CAMPAIGN_RECORD_STATE", "SERIAL_NUMBER_AND_NUMBERED_POSITION_ASSOCIATION", "NO_ASSERTION_POSITION_WAS_USABLE"),
        prop("P3", source, spans[2], "tehnicianul", "a verificat", "numărul de serie al fiecărui senzor și a consultat fișa pentru a identifica poziția care îi era atribuită", "Înainte de instalare", "BEFORE_INSTALLATION", "SERIAL_CHECK_AND_ASSIGNED_POSITION_IDENTIFICATION", "NO_ASSERTION_INSTALLATION_SUCCEEDED"),
        prop("P4", source, spans[3], "Senzorii", "au fost montați", "individual în pozițiile înscrise în fișă", None, "INSTALLATION_PHASE", "INDIVIDUAL_INSTALLATION_IN_RECORDED_POSITIONS", "NO_ASSERTION_ALL_ASSIGNED_POSITIONS_WERE_USABLE"),
        prop("P5", source, spans[4], "poziția efectivă a fiecărui senzor și ora instalării", "au fost consemnate", "în jurnalul campaniei", "După montare", "AFTER_INSTALLATION", "ACTUAL_POSITION_AND_INSTALLATION_TIME_LOGGING", "NO_UNSTATED_LOG_CONTENT"),
        prop("P6", source, spans[5], "Un senzor", "a rămas nemontat", "iar situația a fost notată separat în jurnal", "care nu a putut fi instalat în poziția atribuită", "IF_ASSIGNED_POSITION_INSTALLATION_IMPOSSIBLE", "NONINSTALLATION_AND_SEPARATE_LOGGING", "NO_ASSERTION_ANY_SENSOR_MET_CONDITION"),
        prop("P7", source, spans[6], "Operațiunea", "s-a referit", "și nu a stabilit amplasarea altor echipamente din sala de concerte", "numai la cei 18 senzori pregătiți pentru această campanie", "THIS_CAMPAIGN_OPERATION_ONLY", "EIGHTEEN_SENSOR_SCOPE_AND_OTHER_EQUIPMENT_EXCLUSION", "NO_ASSERTION_ABOUT_OTHER_EQUIPMENT_PLACEMENT"),
        prop("P8", source, spans[7], "toate pozițiile atribuite", "nu era cunoscut", "dacă toate pozițiile atribuite vor putea fi folosite și nici dacă vreun senzor va rămâne nemontat", "Înainte de începerea instalării", "BEFORE_INSTALLATION_START", "POSITION_USABILITY_AND_NONINSTALLATION_OUTCOMES_UNKNOWN", "NO_ASSERTION_OF_FUTURE_USABILITY_OR_NONINSTALLATION"),
    ]
    metadata = declaration["source"]
    source_commitment = seal("B2_OWNED_SOURCE_COMMITMENT_V1", {"sha256": SOURCE_SHA256, "byte_length": len(source_bytes), "encoding": "UTF-8", "source_version": metadata["source_version"], "capture_timestamp": metadata["capture_timestamp"]})
    rights_identity = seal("B2_INTERNALLY_OWNED_RIGHTS_INSTRUMENT_PROSPECTIVE_V1", {"declaration_sha256": DECLARATION_SHA256, "owner_identity": declaration["contributor"]["public_identity"], "grants": declaration["independent_grants"]})
    envelope = {"source_commitment": source_commitment, "source_sha256": SOURCE_SHA256, "world_scope": metadata["world_scope"], "authority_scope": metadata["authority_scope"], "propositions": propositions, "proposition_selection": "NOT_PERFORMED", "creative_premise_family_id": "UNASSIGNED"}
    envelope_identity = seal("B2_FACTUAL_AUTHORITY_ENVELOPE_PROSPECTIVE_V1", envelope)
    source_blob = blob_oid(source_bytes)
    archive_commitment = seal("B2_IMMUTABLE_ARCHIVE_COMMITMENT_PROSPECTIVE_V1", {"source_commitment": source_commitment, "source_sha256": SOURCE_SHA256, "byte_length": len(source_bytes), "prospective_git_blob_oid_sha1": source_blob, "write_status": "NOT_WRITTEN"})
    admissions = [git_json(f"docs/artifacts/humor-mechanics-batch2-development-pilot{i:02d}-g01a-g01b-admission-v1.json") for i in range(1, 13)]
    prior_hashes = [item["g01a"]["source_sha256"] for item in admissions]
    prior_blobs = [item["g01a"]["source_git_object"] for item in admissions]
    independence_core = {"schema_name": "batch2-development-pilot13-family-independence-v1", "schema_version": "1.0.0", "pilot13_source_sha256": SOURCE_SHA256, "prior_source_sha256": prior_hashes, "prior_family_identities": {f"pilot{i:02d}": item["g01b"]["family_identities"] for i, item in enumerate(admissions, 1)}, "pilot13_topology": ["SYNTHETIC_ACOUSTIC_SENSOR_INSTALLATION", "SERIAL_TO_NUMBERED_POSITION_ASSOCIATION", "PREINSTALLATION_SERIAL_AND_POSITION_VERIFICATION", "INDIVIDUAL_POSITION_INSTALLATION", "ACTUAL_POSITION_AND_TIME_LOGGING", "INSTALLATION_FAILURE_NONMOUNT_AND_SEPARATE_LOG", "CAMPAIGN_ONLY_SCOPE", "POSITION_USABILITY_AND_NONINSTALLATION_UNKNOWN"], "source_hash_distinct": SOURCE_SHA256 not in prior_hashes, "git_blob_distinct": source_blob not in prior_blobs, "exact_prior_line_reuse": False, "source_event_topic_revision_sibling_syndication_same_event_relation": False, "prior_downstream_or_expected_result_shaping": False, "blind_family_access": False, "result": "PASS_FRESH_FAMILY_INDEPENDENCE"}
    independence = {**independence_core, "family_independence_identity": seal("B2_DEVELOPMENT_PILOT13_FAMILY_INDEPENDENCE_V1", independence_core)}
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {"pilot_id": declaration["pilot_id"], "event_class": "OWNER_AUTHORED_SYNTHETIC_ACOUSTIC_SENSOR_INSTALLATION"})
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {"rights_identity": rights_identity, "authority_envelope_identity": envelope_identity})
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {"topic_entity_class": "SYNTHETIC_ACOUSTIC_SENSOR_INSTALLATION_CONTROL"})
    revision_family = seal("B2_REVISION_FAMILY_V1", {"source_family": source_family, "source_version": metadata["source_version"], "supersedes": None})
    family_closure = seal("B2_FAMILY_CLOSURE_PROSPECTIVE_V1", {"source": source_family, "event": event_family, "authority": authority_family, "topic_entity": topic_family, "revision": revision_family, "family_independence_identity": independence["family_independence_identity"], "creative_premise": "UNASSIGNED", "construction_revision_family": "UNASSIGNED", "creative_marker_family": "UNASSIGNED"})
    partition_identity = seal("B2_DEVELOPMENT_PARTITION_SEAL_PROSPECTIVE_V1", {"family_closure": family_closure, "partition": "DEVELOPMENT", "curriculum_candidate": False, "blind_evaluation": False})
    source_package_identity = seal("B2_SOURCE_PACKAGE_PROSPECTIVE_V1", {"source_commitment": source_commitment, "archive_commitment": archive_commitment, "rights_identity": rights_identity, "authority_envelope_identity": envelope_identity, "family_closure": family_closure, "partition_identity": partition_identity, "status": "NOT_INGESTED_NOT_ARCHIVED"})
    request = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot13-owner-input-request-v1.json")
    core = {"schema_name": "batch2-development-pilot13-preingestion-v1", "schema_version": "1.0.0", "status": "PROSPECTIVE_UNSIGNED_NOT_INGESTED_NOT_G01_ADMITTED", "pilot_role": "LEGITIMATE_END_TO_END_MECHANISM_TRIAL", "validation_commit": VALIDATION_COMMIT, "validation_identity": VALIDATION_IDENTITY, "qualification_identity": request["qualification_identity"], "executable_implementation_identity": request["executable_implementation_identity"], "provider_identity": request["provider_identity"], "emitter_identity": request["emitter_identity"], "source_sha256": SOURCE_SHA256, "source_byte_length": len(source_bytes), "declaration_sha256": DECLARATION_SHA256, "source_commitment": source_commitment, "rights_instrument_identity": rights_identity, "immutable_archive_commitment": archive_commitment, "prospective_git_blob_oid_sha1": source_blob, "source_package_identity": source_package_identity, "factual_authority_envelope": envelope, "factual_authority_envelope_identity": envelope_identity, "family_independence_identity": independence["family_independence_identity"], "family_identities": {"source_family": source_family, "event_family": event_family, "authority_family": authority_family, "topic_entity_family": topic_family, "revision_family": revision_family, "family_closure": family_closure}, "partition": "DEVELOPMENT", "prospective_partition_identity": partition_identity, "proposition_binding_count": 8, "proposition_binding_status": "PASS_8_BOUND_NOT_SELECTED", "selected_proposition": "UNASSIGNED", "proposition_sufficiency_evaluated": False, "assignment": "UNASSIGNED", "target_mechanism": "UNASSIGNED", "semantic_role_affordance_realization_witness_or_alignment_planning": "NOT_PERFORMED", "archive_write": False, "ingested": False, "authority_matrix": {key: False for key in ("custodial_signing", "signature_verification", "immutable_ingestion", "g01a", "g01b", "proposition_sufficiency", "assignment", "constructor_compatibility", "constructor_release", "constructor_invocation", "realization", "candidate_emission", "semantic_conformance", "fragment_collision", "g02", "g02c", "g03", "g04b", "model_exposure", "training", "runtime_integration", "production_routing")}}
    prospective = {**core, "preingestion_identity": seal("B2_DEVELOPMENT_PILOT13_PREINGESTION_V1", core)}
    operations = [("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"], rights_identity), ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], source_package_identity), ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"], archive_commitment), ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"], family_closure), ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"], partition_identity), ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"], prospective["preingestion_identity"])]
    records = [{"ordinal": i, "purpose": purpose, "object_identity": obj, "required_signer_roles": roles, "distinct_signers_required": len(roles) > 1} for i, (purpose, roles, obj) in enumerate(operations)]
    registration = git_json("docs/artifacts/humor-mechanics-batch2-custodial-public-key-registration-v1.json")
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    packet_core = {"preingestion_identity": prospective["preingestion_identity"], "source_sha256": SOURCE_SHA256, "declaration_sha256": DECLARATION_SHA256, "registration_identity": registration["registration_identity"], "prior_ledger_head": LEDGER_HEAD, "operations": records, "atomic": True}
    packet_identity = seal("B2_DEVELOPMENT_PILOT13_SIGNING_PACKET_V1", packet_core)
    requests = []
    for operation in records:
        for role in operation["required_signer_roles"]:
            challenge_core = {"domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT13_PREINGESTION_V1", "purpose": operation["purpose"], "role": role, "principal_identity": principals[role], "object_identity": operation["object_identity"], "packet_identity": packet_identity, "source_sha256": SOURCE_SHA256, "declaration_sha256": DECLARATION_SHA256, "preingestion_identity": prospective["preingestion_identity"], "nonce": seal("B2_PILOT13_SIGNING_NONCE_V1", {"packet": packet_identity, "ordinal": operation["ordinal"], "role": role}), "prior_ledger_head": LEDGER_HEAD, "grants_operational_content_access": False}
            requests.append({"operation_ordinal": operation["ordinal"], "purpose": operation["purpose"], "role": role, "challenge": {**challenge_core, "challenge_identity": seal("B2_PILOT13_SIGNING_CHALLENGE_V1", challenge_core)}, "signature_status": "UNSIGNED_AWAITING_SEPARATE_OWNER_ACTION"})
    require(len(requests) == 8, "eight signature requests")
    packet = {"schema_name": "batch2-development-pilot13-custodial-signing-packet-v1", "schema_version": "1.0.0", "packet_core": packet_core, "packet_identity": packet_identity, "signature_requests": requests, "status": "UNSIGNED", "signatures_present": 0, "source_ingested": False, "archive_written": False, "ledger_events_appended": 0, "proposition_sufficiency_evaluated": False, "downstream_planning_or_construction_performed": False}
    write("humor-mechanics-batch2-development-pilot13-preingestion-v1.json", prospective)
    write("humor-mechanics-batch2-development-pilot13-family-independence-v1.json", independence)
    write("humor-mechanics-batch2-development-pilot13-signing-packet-v1.json", packet)
    print(json.dumps({"preparation_verdict": "PASS_UNSIGNED_PREPARATION", "preingestion_identity": prospective["preingestion_identity"], "source_commitment": source_commitment, "rights_identity": rights_identity, "archive_commitment": archive_commitment, "source_package_identity": source_package_identity, "authority_envelope_identity": envelope_identity, "family_independence_identity": independence["family_independence_identity"], "family_closure": family_closure, "partition_identity": partition_identity, "signing_packet_identity": packet_identity, "proposition_bindings": 8, "signature_requests": 8}, sort_keys=True))


if __name__ == "__main__":
    main()

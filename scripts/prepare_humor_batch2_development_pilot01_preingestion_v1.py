"""Validate Pilot 01 and freeze prospective metadata plus unsigned packet."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "artifacts"
SOURCE = ROOT / "owner-source-v1.txt"
DECLARATION = ROOT / "owner-declaration-v1.json"
SOURCE_SHA = "84261f1a6b97f951f70a1b86d42114da9703996607d43d2fc3779bffd7a97cb2"
DECLARATION_SHA = "26712ba98a4022dc72d1a41b6c178665fbd7cb27aeb76da1aa08ff02b960aa81"
LEDGER_HEAD = "5b47822411f6e000bfb0e28bc9e7e2e74c54f95ac663bc740c34f71f7fe212c8"
REGISTRATION_ID = "01912e139471ec23cba5861c8f575f098a6248d39ebbe5ec2ee043493d392ebe"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_oid(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def words(text: str, absolute_start: int) -> list[tuple[int, int]]:
    return [(absolute_start + match.start(), absolute_start + match.end())
            for match in re.finditer(r"\S+", text)]


def component(word_spans: list[tuple[int, int]], start: int, end: int,
              source: str) -> dict[str, Any]:
    char_start, char_end = word_spans[start][0], word_spans[end - 1][1]
    value = source[char_start:char_end]
    return {
        "character_coordinates": [char_start, char_end],
        "utf8_byte_coordinates": [len(source[:char_start].encode()), len(source[:char_end].encode())],
        "sha256": sha(value.encode()),
    }


def proposition(identifier: str, source: str, start: int, end: int,
                subject_words: tuple[int, int], predicate_words: tuple[int, int],
                object_words: tuple[int, int], qualification_words: tuple[int, int] | None = None) -> dict[str, Any]:
    surface = source[start:end]
    word_spans = words(surface, start)
    record = {
        "proposition_id": identifier,
        "supporting_span": {
            "character_coordinates": [start, end],
            "utf8_byte_coordinates": [len(source[:start].encode()), len(source[:end].encode())],
            "span_sha256": sha(surface.encode()),
        },
        "subject": component(word_spans, *subject_words, source),
        "predicate": component(word_spans, *predicate_words, source),
        "object": component(word_spans, *object_words, source),
        "modality": "ASSERTED", "qualification": None,
        "time": "EXPLICIT_IF_BOUND_IN_OBJECT_OTHERWISE_UNSPECIFIED",
        "scope": "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE_ONLY",
        "attribution": "OWNER_AUTHORED_SOURCE",
        "known_boundary": "ONLY_THE_EXACT_BOUND_PROPOSITION",
        "unknown_boundary": "ALL_UNSTATED_CONDITIONS_AND_REAL_WORLD_APPLICABILITY",
        "prohibited_inferences": [
            "NO_REAL_WORLD_ASSERTION", "NO_UNSTATED_CAUSAL_INFERENCE",
            "NO_UNSTATED_PERSON_OR_INTENT_INFERENCE",
        ],
        "quotation_status": "OWNER_AUTHORED_NOT_THIRD_PARTY_QUOTATION",
        "sensitive_protected_target_classification": "NONE_DECLARED_LOW_RISK_SYNTHETIC",
    }
    if qualification_words:
        record["qualification"] = component(word_spans, *qualification_words, source)
    return record


def exact_fields(declaration: dict[str, Any]) -> None:
    require(set(declaration) == {"schema_name", "schema_version", "pilot_id", "source", "contributor",
                                 "ownership_declarations", "independent_grants", "rights_terms",
                                 "source_status_declarations", "owner_instruction", "owner_confirmation"},
            "declaration top-level fields")
    require(set(declaration["source"]) == {"filename", "declared_encoding", "bom", "line_endings",
                                           "terminal_lf_count", "source_version", "capture_timestamp",
                                           "acquisition_timestamp", "acquisition_channel",
                                           "intended_partition", "subject_class", "authority_scope",
                                           "world_scope"}, "source fields")
    require(set(declaration["contributor"]) == {"public_identity", "legal_identity",
                                                "legal_identity_verification_reference", "role",
                                                "rights_holder_identity", "rights_holder_relationship",
                                                "identity_disclosure_approved_for_commit"}, "contributor fields")
    require(set(declaration["independent_grants"]) == {"immutable_archival",
                                                       "factual_annotation_and_authority_binding",
                                                       "internal_discovery", "construction_and_evaluation",
                                                       "model_exposure", "training", "runtime_integration",
                                                       "production_routing"}, "grant fields")


def main() -> None:
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(sha(source_bytes) == SOURCE_SHA and sha(declaration_bytes) == DECLARATION_SHA, "input hash")
    require(not source_bytes.startswith(b"\xef\xbb\xbf") and b"\r" not in source_bytes and
            source_bytes.endswith(b"\n") and not source_bytes.endswith(b"\n\n"), "source encoding/newline")
    source = source_bytes.decode("utf-8")
    declaration = json.loads(declaration_bytes)
    exact_fields(declaration)
    source_meta = declaration["source"]
    require(source_meta == {**source_meta, "filename": "owner-source-v1.txt"} and
            source_meta["declared_encoding"] == "UTF-8" and source_meta["bom"] is False and
            source_meta["line_endings"] == "LF" and source_meta["terminal_lf_count"] == 1 and
            re.fullmatch(r"\d+\.\d+\.\d+", source_meta["source_version"]) and
            source_meta["acquisition_channel"] == "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE" and
            source_meta["intended_partition"] == "DEVELOPMENT" and
            source_meta["subject_class"] == source_meta["world_scope"] ==
            "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE", "source declaration")
    for timestamp in (source_meta["capture_timestamp"], source_meta["acquisition_timestamp"],
                      declaration["rights_terms"]["effective_at"]):
        require(isinstance(timestamp, str) and datetime.fromisoformat(timestamp.replace("Z", "+00:00")),
                "timestamp")
    contributor = declaration["contributor"]
    require(all(isinstance(contributor[key], str) and contributor[key] for key in
                ("public_identity", "legal_identity", "legal_identity_verification_reference",
                 "rights_holder_identity")) and
            contributor["public_identity"] == contributor["legal_identity"] ==
            contributor["rights_holder_identity"] and
            contributor["public_identity"].startswith("urn:pastila:party:") and
            contributor["identity_disclosure_approved_for_commit"] is False and
            contributor["legal_identity"] == "urn:pastila:party:pastila-acida-owner-v1",
            "committable owner identity")
    ownership = declaration["ownership_declarations"]
    require(ownership["original_authorship"] and ownership["owns_or_controls_required_rights"] and
            ownership["has_authority_to_make_each_selected_grant"] and
            not any(ownership[key] for key in ownership if key not in
                    {"original_authorship", "owns_or_controls_required_rights",
                     "has_authority_to_make_each_selected_grant"}), "ownership declarations")
    grants = declaration["independent_grants"]
    require(all(grants[key] for key in ("immutable_archival",
                                        "factual_annotation_and_authority_binding",
                                        "internal_discovery", "construction_and_evaluation")) and
            not any(grants[key] for key in ("model_exposure", "training",
                                            "runtime_integration", "production_routing")),
            "independent grant boundary")
    require(declaration["rights_terms"]["territory"] == "WORLDWIDE" and
            declaration["rights_terms"]["expires_at"] == "NO_EXPIRY" and
            declaration["rights_terms"]["correction_policy"] == "NEW_IMMUTABLE_REVISION_ONLY" and
            declaration["rights_terms"]["supersession_policy"] ==
            "EXPLICIT_PREDECESSOR_SUCCESSOR_CHAIN", "rights terms")
    require(all(declaration["source_status_declarations"].values()) and
            declaration["owner_confirmation"]["confirmed"] is True and
            declaration["owner_instruction"]["permit_derived_hashes_and_coordinates"] is True and
            declaration["owner_instruction"]["permit_registered_custodial_signing_requests"] is True and
            declaration["owner_instruction"]["permit_git_object_archival"] is True and
            declaration["owner_instruction"]["permit_partition_seal_for_development_only"] is True and
            declaration["owner_instruction"]["operational_content_access_after_ingestion"] is False,
            "owner instruction/status")
    lines = source.splitlines(keepends=True)
    require(len(lines) == 5, "expected neutral pilot proposition layout")
    starts, cursor = [], 0
    for line in lines:
        starts.append(cursor)
        cursor += len(line)
    # Six propositions: line two contains two independently asserted clauses.
    p1_end = starts[0] + len(lines[0].rstrip("\n"))
    line2_text = lines[1].rstrip("\n")
    separator = line2_text.index(", iar ")
    p2_start, p2_end = starts[1], starts[1] + separator
    p3_start, p3_end = starts[1] + separator + len(", iar "), starts[1] + len(line2_text)
    spans = [
        ("P1", starts[0], p1_end, (0, 4), (4, 6), (6, 12), None),
        ("P2", p2_start, p2_end, (0, 2), (2, 3), (3, 6), None),
        ("P3", p3_start, p3_end, (0, 2), (2, 3), (3, 6), None),
        ("P4", starts[2], starts[2] + len(lines[2].rstrip("\n")), (0, 2), (2, 3), (3, 4), None),
        ("P5", starts[3], starts[3] + len(lines[3].rstrip("\n")), (0, 1), (1, 3), (3, 12), None),
        ("P6", starts[4], starts[4] + len(lines[4].rstrip("\n")), (5, 7), (7, 10), (10, 14), (0, 5)),
    ]
    propositions = [proposition(identifier, source, start, end, subject, predicate, obj, qualification)
                    for identifier, start, end, subject, predicate, obj, qualification in spans]
    source_commitment = seal("B2_OWNED_SOURCE_COMMITMENT_V1", {
        "sha256": SOURCE_SHA, "byte_length": len(source_bytes), "encoding": "UTF-8",
        "source_version": source_meta["source_version"], "capture_timestamp": source_meta["capture_timestamp"],
    })
    rights_identity = seal("B2_INTERNALLY_OWNED_RIGHTS_INSTRUMENT_PROSPECTIVE_V1", {
        "declaration_sha256": DECLARATION_SHA, "owner_identity": contributor["public_identity"],
        "grants": grants, "rights_terms": declaration["rights_terms"],
    })
    authority_envelope = {
        "source_commitment": source_commitment, "source_sha256": SOURCE_SHA,
        "world_scope": source_meta["world_scope"], "authority_scope": source_meta["authority_scope"],
        "propositions": propositions, "creative_premise_family_id": "UNASSIGNED",
    }
    authority_envelope_identity = seal("B2_FACTUAL_AUTHORITY_ENVELOPE_PROSPECTIVE_V1", authority_envelope)
    prospective_git_blob_oid = git_blob_oid(source_bytes)
    archive_commitment = seal("B2_IMMUTABLE_ARCHIVE_COMMITMENT_PROSPECTIVE_V1", {
        "source_commitment": source_commitment, "source_sha256": SOURCE_SHA,
        "byte_length": len(source_bytes), "prospective_git_blob_oid_sha1": prospective_git_blob_oid,
        "write_status": "NOT_WRITTEN",
    })
    source_family = seal("B2_SOURCE_FAMILY_V1", {"source_commitment": source_commitment})
    event_family = seal("B2_EVENT_FAMILY_V1", {"pilot_id": declaration["pilot_id"],
                                               "world_scope": source_meta["world_scope"]})
    authority_family = seal("B2_AUTHORITY_FAMILY_V1", {
        "rights_identity": rights_identity, "authority_envelope_identity": authority_envelope_identity})
    topic_family = seal("B2_TOPIC_ENTITY_FAMILY_METADATA_V1", {
        "subject_class": source_meta["subject_class"], "entity_class": "SYNTHETIC_ROOM_AND_CABINETS"})
    revision_family = seal("B2_REVISION_FAMILY_V1", {
        "source_family": source_family, "source_version": source_meta["source_version"], "supersedes": None})
    family_closure = seal("B2_FAMILY_CLOSURE_V1", {
        "source": source_family, "event": event_family, "authority": authority_family,
        "topic_entity": topic_family, "revision": revision_family,
        "creative_premise": "UNASSIGNED"})
    partition_identity = seal("B2_DEVELOPMENT_PARTITION_SEAL_PROSPECTIVE_V1", {
        "family_closure": family_closure, "partition": "DEVELOPMENT",
        "curriculum_candidate": False, "blind_evaluation": False})
    source_package_identity = seal("B2_SOURCE_PACKAGE_PROSPECTIVE_V1", {
        "source_commitment": source_commitment, "archive_commitment": archive_commitment,
        "rights_identity": rights_identity, "authority_envelope_identity": authority_envelope_identity,
        "family_closure": family_closure, "partition_identity": partition_identity,
        "status": "NOT_INGESTED_NOT_ARCHIVED"})
    prospective = {
        "schema_name": "batch2-development-pilot01-preingestion-v1", "schema_version": "1.0.0",
        "source_sha256": SOURCE_SHA, "source_byte_length": len(source_bytes),
        "declaration_sha256": DECLARATION_SHA, "source_commitment": source_commitment,
        "rights_instrument_identity": rights_identity,
        "immutable_archive_commitment": archive_commitment,
        "prospective_git_blob_oid_sha1": prospective_git_blob_oid,
        "source_package_identity": source_package_identity,
        "factual_authority_envelope": authority_envelope,
        "factual_authority_envelope_identity": authority_envelope_identity,
        "family_identities": {
            "source_family": source_family, "event_family": event_family,
            "authority_family": authority_family, "topic_entity_family": topic_family,
            "revision_family": revision_family, "family_closure": family_closure,
            "creative_premise_family_id": "UNASSIGNED",
        },
        "partition": "DEVELOPMENT", "partition_identity": partition_identity,
        "duplicate_revision_same_event_status": "NO_EXISTING_RELATIONSHIP_DECLARED_PILOT_GENERATION_1",
        "archive_write": False, "git_archival": False, "ingested": False,
        "authority_matrix": {
            "preingestion_validation": True, "signing_packet_preparation": True,
            "immutable_ingestion": False, "archive_write": False, "content_access": False,
            "mechanism_assignment": False, "creative_premise_assignment": False,
            "construction": False, "generation": False, "model_exposure": False,
            "training": False, "runtime_integration": False, "production_routing": False,
        },
        "verdict": "PASS_PREINGESTION_READY_FOR_CUSTODIAL_SIGNATURES",
    }
    prospective["preingestion_identity"] = seal("B2_DEVELOPMENT_PILOT01_PREINGESTION_V1", prospective)
    operations = [
        ("RIGHTS_ADMISSION", ["RIGHTS_CUSTODIAN"]),
        ("ACQUISITION_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"]),
        ("IMMUTABLE_ARCHIVE_ADMISSION", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"]),
        ("FAMILY_CLOSURE", ["FAMILY_CUSTODIAN"]),
        ("DEVELOPMENT_PARTITION_SEAL", ["PARTITION_CUSTODIAN"]),
        ("CONTAMINATION_LEDGER_ADVANCEMENT", ["CONTAMINATION_AUDITOR"]),
    ]
    op_records = []
    for ordinal, (purpose, roles) in enumerate(operations):
        object_identity = {
            "RIGHTS_ADMISSION": rights_identity,
            "ACQUISITION_ADMISSION": source_package_identity,
            "IMMUTABLE_ARCHIVE_ADMISSION": archive_commitment,
            "FAMILY_CLOSURE": family_closure,
            "DEVELOPMENT_PARTITION_SEAL": partition_identity,
            "CONTAMINATION_LEDGER_ADVANCEMENT": prospective["preingestion_identity"],
        }[purpose]
        op_records.append({"ordinal": ordinal, "purpose": purpose, "object_identity": object_identity,
                           "required_signer_roles": roles, "distinct_signers_required": len(roles) > 1})
    packet_core = {
        "preingestion_identity": prospective["preingestion_identity"],
        "source_sha256": SOURCE_SHA, "declaration_sha256": DECLARATION_SHA,
        "registration_identity": REGISTRATION_ID, "prior_ledger_head": LEDGER_HEAD,
        "operations": op_records, "atomic": True,
    }
    packet_identity = seal("B2_DEVELOPMENT_PILOT01_SIGNING_PACKET_V1", packet_core)
    registration = json.loads((OUT / "humor-mechanics-batch2-custodial-public-key-registration-v1.json").read_text())
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    requests = []
    for operation in op_records:
        for role in operation["required_signer_roles"]:
            challenge = {
                "domain": "PASTILA_BATCH2_DEVELOPMENT_PILOT01_PREINGESTION_V1",
                "purpose": operation["purpose"], "role": role,
                "principal_identity": principals[role],
                "object_identity": operation["object_identity"],
                "packet_identity": packet_identity, "source_sha256": SOURCE_SHA,
                "declaration_sha256": DECLARATION_SHA,
                "preingestion_identity": prospective["preingestion_identity"],
                "nonce": seal("B2_PILOT01_SIGNING_NONCE_V1",
                              {"packet": packet_identity, "ordinal": operation["ordinal"], "role": role}),
                "prior_ledger_head": LEDGER_HEAD, "grants_operational_content_access": False,
            }
            challenge["challenge_identity"] = seal("B2_PILOT01_SIGNING_CHALLENGE_V1", challenge)
            requests.append({"operation_ordinal": operation["ordinal"], "purpose": operation["purpose"],
                             "role": role, "challenge": challenge,
                             "signature_status": "AWAITING_OWNER_CONTROLLED_SIGNATURE"})
    packet = {
        "schema_name": "batch2-development-pilot01-custodial-signing-packet-v1",
        "schema_version": "1.0.0", "packet_core": packet_core,
        "packet_identity": packet_identity, "signature_requests": requests,
        "status": "AWAITING_CUSTODIAL_SIGNATURES", "source_ingested": False,
        "archive_written": False, "ledger_events_appended": 0,
    }
    for name, value in (
        ("humor-mechanics-batch2-development-pilot01-preingestion-v1.json", prospective),
        ("humor-mechanics-batch2-development-pilot01-signing-packet-v1.json", packet),
    ):
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8", newline="\n")
    print(json.dumps({
        "verdict": prospective["verdict"], "preingestion_identity": prospective["preingestion_identity"],
        "source_commitment": source_commitment, "rights_instrument_identity": rights_identity,
        "archive_commitment": archive_commitment, "source_package_identity": source_package_identity,
        "authority_envelope_identity": authority_envelope_identity,
        "packet_identity": packet_identity, "signature_requests": len(requests),
    }, sort_keys=True))


if __name__ == "__main__":
    main()

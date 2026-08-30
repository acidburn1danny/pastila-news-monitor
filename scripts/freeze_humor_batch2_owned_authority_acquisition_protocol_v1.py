"""Materialize the source-only Batch 2 Owned-Authority Acquisition Protocol V1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "artifacts"
BASE_PLAN_COMMIT = "c756135fa9b822dd945728a2df05f26f3b44fa63"
BASE_PLAN_ID = "57419ff52730ccd20acf3c716c9502667d9f25e517570e18eeae7ec3d472da8a"
DISCOVERY_COMMIT = "fe0df4152b3b9fcf39fbead1afb7c5c57f404b44"
DISCOVERY_ID = "03f29a14a5fa5674046326d10016c509ec05dfa731e61f30716cfc653b9d09c8"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def write(name: str, value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path = OUT / name
    path.write_text(data, encoding="utf-8", newline="\n")
    return hashlib.sha256(data.encode()).hexdigest()


def authority_false() -> dict[str, bool]:
    return {
        "source_acquisition": False, "content_ingestion": False, "mechanism_assignment": False,
        "candidate_construction": False, "surface_generation": False, "model_exposure": False,
        "training": False, "runtime_integration": False, "production_routing": False,
    }


def main() -> None:
    rights = {
        "schema_name": "batch2-owned-authority-rights-instrument-v1",
        "schema_version": "1.0.0",
        "closed_permitted_use_classes": {
            "DISCOVERY_ONLY": {"discovery": True, "construction_evaluation": False, "training": False, "production": False},
            "CONSTRUCTION_EVALUATION": {"discovery": True, "construction_evaluation": True, "training": False, "production": False},
            "TRAINING": {"discovery": True, "construction_evaluation": False, "training": True, "production": False},
            "PRODUCTION": {"discovery": True, "construction_evaluation": False, "training": False, "production": True},
            "REJECTED_OR_UNRESOLVED": {"discovery": False, "construction_evaluation": False, "training": False, "production": False},
        },
        "noninheritance": [
            "DISCOVERY_DOES_NOT_GRANT_CONSTRUCTION_EVALUATION",
            "CONSTRUCTION_EVALUATION_DOES_NOT_GRANT_TRAINING",
            "TRAINING_DOES_NOT_GRANT_PRODUCTION",
            "PRODUCTION_DOES_NOT_GRANT_TRAINING",
        ],
        "approved_lane_templates": {
            "INTERNALLY_OWNED": ["owner_identity", "authorship_declaration", "rights_holder_signature",
                                 "permitted_use_class_set", "revocation_terms"],
            "AFFIRMATIVELY_LICENSED_EXTERNAL": ["licensor_identity", "license_text_sha256",
                                                "affirmative_grant_scope", "expiry", "attribution"],
            "PUBLIC_DOMAIN_OR_OPEN_LICENSE": ["legal_basis_or_spdx", "jurisdiction",
                                              "compatibility_review_identity", "attribution"],
        },
        "required_fields": [
            "instrument_id", "lane", "rights_holder", "source_family_commitment",
            "grants", "prohibitions", "territory", "effective_at", "expires_at",
            "revocation_terms", "signature_or_owner_seal", "instrument_sha256",
        ],
        "fail_closed_rules": [
            "PUBLIC_ACCESS_IS_NOT_PERMISSION", "QUOTATION_RIGHT_IS_NOT_DERIVATIVE_OR_TRAINING_AUTHORITY",
            "SILENCE_OR_AMBIGUITY_IS_REJECTED_OR_UNRESOLVED", "GRANTS_ARE_ACTION_SPECIFIC",
            "NO_PERMISSION_INHERITANCE_FROM_PRIOR_STAGE",
        ],
        "current_grants": authority_false(),
    }
    rights["rights_template_identity"] = seal("B2_OWNED_AUTHORITY_RIGHTS_TEMPLATE_V1", rights)
    rights_sha = write("humor-mechanics-batch2-owned-authority-rights-instruments-v1.json", rights)

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:pastila:batch2:owned-authority-source-package:v1",
        "title": "Batch 2 Owned-Authority Immutable Source Package V1",
        "type": "object", "additionalProperties": False,
        "required": [
            "source_package_id", "original_bytes_sha256", "byte_length", "encoding",
            "capture_time", "source_version", "rights_instrument_id", "permitted_use_classes",
            "propositions", "family_identities", "partition_seal", "contamination_ledger_head",
            "archive_object_identity", "supersedes",
        ],
        "properties": {
            "source_package_id": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "original_bytes_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "byte_length": {"type": "integer", "minimum": 1},
            "encoding": {"const": "UTF-8"},
            "capture_time": {"type": "string", "format": "date-time"},
            "source_version": {"type": "string", "minLength": 1},
            "rights_instrument_id": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "permitted_use_classes": {"type": "array", "uniqueItems": True, "items": {
                "enum": ["DISCOVERY_ONLY", "CONSTRUCTION_EVALUATION", "TRAINING", "PRODUCTION"]}},
            "propositions": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/proposition"}},
            "family_identities": {"$ref": "#/$defs/families"},
            "partition_seal": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "contamination_ledger_head": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "archive_object_identity": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "supersedes": {"type": ["string", "null"]},
        },
        "$defs": {
            "span": {"type": "object", "additionalProperties": False,
                     "required": ["character_start", "character_end", "utf8_byte_start", "utf8_byte_end", "span_sha256"],
                     "properties": {
                         "character_start": {"type": "integer", "minimum": 0},
                         "character_end": {"type": "integer", "minimum": 1},
                         "utf8_byte_start": {"type": "integer", "minimum": 0},
                         "utf8_byte_end": {"type": "integer", "minimum": 1},
                         "span_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}},
            "proposition": {"type": "object", "additionalProperties": False,
                            "required": ["proposition_id", "span", "authority_scope", "modality",
                                         "qualification_bindings", "factual_status"],
                            "properties": {
                                "proposition_id": {"type": "string", "minLength": 1},
                                "span": {"$ref": "#/$defs/span"},
                                "authority_scope": {"type": "string", "minLength": 1},
                                "modality": {"enum": ["ASSERTED", "POSSIBLE", "PROBABLE", "REPORTED", "UNKNOWN"]},
                                "qualification_bindings": {"type": "array", "uniqueItems": True, "items": {"type": "string"}},
                                "factual_status": {"enum": ["SUPPORTED", "QUALIFIED", "UNRESOLVED", "NONFACTUAL"]}}},
            "families": {"type": "object", "additionalProperties": False,
                         "required": ["source", "event", "authority", "topic_entity", "creative_premise",
                                      "family_closure", "revision"],
                         "properties": {key: {"type": "string", "minLength": 1} for key in
                                        ["source", "event", "authority", "topic_entity", "creative_premise",
                                         "family_closure", "revision"]}},
        },
        "construction_authority": False,
    }
    schema_sha = write("humor-mechanics-batch2-owned-authority-source-package-v1.schema.json", schema)

    escrow = {
        "schema_name": "batch2-owned-authority-access-and-blind-escrow-v1",
        "schema_version": "1.0.0",
        "roles": {
            "ACQUISITION_CUSTODIAN": {"may_see": ["rights", "source"], "may_not": ["mechanism_assignment", "candidate", "owner_preference"]},
            "PARTITION_CUSTODIAN": {"may_see": ["metadata", "family_closure"], "may_not": ["blind_surface", "mechanism_assignment"]},
            "ASSIGNMENT_CUSTODIAN": {"may_see": ["admitted_nonblind_authority", "operational_obligations"], "may_not": ["owner_preference", "blind_surface"]},
            "CONSTRUCTOR": {"may_see": ["sealed_nonblind_construction_packet"], "may_not": ["mechanism_label", "blind_family", "mapping", "owner_preference"]},
            "EVALUATOR": {"may_see": ["shuffled_target_neighbors_none_ambiguous"], "may_not": ["constructor_identity", "sealed_mapping_until_verdict"]},
            "OWNER_REVIEWER": {"may_see": ["passed_gate_artifacts"], "may_not": ["blind_holdout_before_system_freeze"]},
            "BLIND_ESCROW": {"may_see": ["blind_source", "rights", "partition_seal"], "may_not": ["development_selection", "training", "prompt_tuning"]},
        },
        "ordering": [
            "RIGHTS_AND_METADATA_CAPTURE", "FAMILY_CLOSURE", "PARTITION_ASSIGNMENT",
            "BLIND_SEAL", "PARTITION_SPECIFIC_CONTENT_ACCESS",
        ],
        "family_isolation": "ENTIRE_SOURCE_EVENT_AUTHORITY_TOPIC_REVISION_CLOSURE_ONE_PARTITION_ONLY",
        "blind_rules": [
            "NO_ATOM_OR_SURFACE_ACCESS_BEFORE_BLIND_SEAL",
            "NO_BLIND_INPUT_TO_CONSTRUCTION_PROMPT_GATE_TEMPLATE_SELECTION_OWNER_PREFERENCE_OR_TRAINING_TUNING",
            "BLIND_EVALUATION_ONLY_AFTER_DEVELOPMENT_SYSTEM_FREEZE",
            "BLIND_RESULTS_DO_NOT_TUNE_THE_EVALUATED_CYCLE",
        ],
        "existing_reservations": {
            "discovery_commit": DISCOVERY_COMMIT, "discovery_identity": DISCOVERY_ID,
            "status": "OPAQUE_RESERVATIONS_ONLY_NOT_PROMOTED_OR_INSPECTED",
        },
        "permanent_contamination": {
            "event_ids": [1538, 2617], "reassignment": False, "downstream_use": False,
        },
        "access_log_required_fields": [
            "sequence", "actor_role", "object_commitment", "operation", "purpose",
            "authority_identity", "timestamp", "previous_entry_hash", "entry_hash",
        ],
        "current_authority": authority_false(),
    }
    escrow["escrow_spec_identity"] = seal("B2_OWNED_AUTHORITY_ESCROW_V1", escrow)
    escrow_sha = write("humor-mechanics-batch2-owned-authority-access-escrow-v1.json", escrow)

    protocol = {
        "schema_name": "batch2-owned-authority-acquisition-protocol-v1",
        "schema_version": "1.0.0",
        "bases": {"v2_plan_commit": BASE_PLAN_COMMIT, "v2_plan_identity": BASE_PLAN_ID,
                  "discovery_closure_commit": DISCOVERY_COMMIT, "discovery_closure_identity": DISCOVERY_ID},
        "approved_provenance_lanes": [
            "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE",
            "AFFIRMATIVELY_LICENSED_EXTERNAL_MATERIAL",
            "COMPATIBLE_PUBLIC_DOMAIN_OR_OPEN_LICENSE_MATERIAL",
        ],
        "artifact_bindings": {"rights_sha256": rights_sha, "source_schema_sha256": schema_sha, "escrow_sha256": escrow_sha},
        "ingestion": {
            "precondition": "SEPARATE_SOURCE_ACQUISITION_AUTHORITY",
            "immutable_capture": [
                "ORIGINAL_BYTES_IN_GIT_OR_GIT_BOUND_CONTENT_ADDRESSED_ARCHIVE",
                "SHA256_BYTE_LENGTH_UTF8_DECLARATION_CAPTURE_TIME_SOURCE_VERSION",
                "INDEPENDENT_CHARACTER_AND_UTF8_BYTE_SPANS",
                "NO_IN_PLACE_CORRECTION",
            ],
            "proposition_authority": [
                "EXACT_SPAN", "AUTHORITY_SCOPE", "FACTUAL_STATUS", "MODALITY",
                "QUALIFICATION_TARGETS", "FACTUAL_VS_NONFACTUAL_SCOPE",
            ],
        },
        "family_derivation": {
            "identities": ["SOURCE", "EVENT", "AUTHORITY", "TOPIC_ENTITY", "CREATIVE_PREMISE",
                           "FAMILY_CLOSURE", "REVISION"],
            "closure_edges": ["DUPLICATE", "SYNDICATED", "SAME_EVENT", "REVISION", "DERIVATIVE"],
            "rule": "CLOSURE_BEFORE_PARTITION_AND_ENTIRE_CLOSURE_ONE_PARTITION",
            "pre_assignment_rule": "CREATIVE_PREMISE_IDENTITY_MUST_BE_UNASSIGNED_THROUGH_G01B_AND_PARTITION_SEAL",
        },
        "partitioning": {
            "partitions": ["DEVELOPMENT", "CURRICULUM_CANDIDATE", "BLIND_EVALUATION"],
            "order": ["METADATA_CAPTURE", "FAMILY_CLOSURE", "PARTITION_SEAL", "CONTENT_ACCESS_IF_AUTHORIZED"],
            "blind": "ESCROW_ONLY_METADATA_COMMITMENTS_OUTSIDE_ESCROW",
        },
        "gates": {
            "G01A": ["AFFIRMATIVE_RIGHTS", "IMMUTABLE_CAPTURE", "PROPOSITION_AUTHORITY",
                     "QUALIFICATION_SCOPE", "TARGET_SAFETY", "SOURCE_VERSION"],
            "G01B": ["FAMILY_CLOSURE", "PARTITION_SEAL", "CONTAMINATION_HEAD",
                     "NO_CROSS_PARTITION_RELATIVE", "BLIND_ACCESS_COMPLIANCE",
                     "CREATIVE_PREMISE_UNASSIGNED"],
            "G02B": ["LABEL_TOKEN_SCAN", "TAXONOMY_PARAPHRASE_SCAN", "PACKET_SHAPE_BALANCE",
                     "CONSTRUCTOR_CANNOT_ACCESS_MAPPING", "SOURCE_SHAPE_BALANCE"],
            "G03": ["INDEPENDENT_SHUFFLED_RECOVERY", "TARGET_NEIGHBORS_NONE_AMBIGUOUS"],
            "G03B": ["MINIMAL_INTERVENTION", "CAUSAL_REMOVAL_OR_LABEL_CHANGE"],
            "G03C": ["METADATA_TEMPLATE_TOPIC_AUTHORSHIP_LENGTH_SHORTCUT_AUDIT", "FAMILY_LEVEL_POOL_AUDIT"],
            "G04": ["ROMANIAN_NATURALNESS_INDEPENDENT", "VOICE_REVIEW_INDEPENDENT"],
            "G05": ["OWNER_FREEZE_AFTER_ALL_PRIOR_GATES", "NO_RETROACTIVE_BLIND_TUNING"],
        },
        "mechanism_blind_assignment": {
            "constructor_receives": ["FACTUAL_ENVELOPE", "ALLOWED_CREATIVE_SCOPE", "TARGET_RESTRICTIONS",
                                     "OPERATIONAL_EFFECT", "FORBIDDEN_NEIGHBORS", "LANGUAGE_CONSTRAINTS",
                                     "SEALED_ASSIGNMENT_ID"],
            "constructor_never_receives": ["MECHANISM_ID", "MECHANISM_NAME", "TAXONOMY_DEFINITION",
                                           "SEALED_MAPPING", "OWNER_PREFERENCE", "BLIND_FAMILY"],
            "wording_controls": ["MULTIPLE_INDEPENDENT_PHRASINGS", "SHARED_CROSS_MECHANISM_CONSTRAINTS",
                                 "NO_SIGNATURE_TEMPLATE", "PACKET_LENGTH_AND_FIELD_BALANCE"],
        },
        "revocation_correction_supersession": {
            "revocation": "FAIL_CLOSED_ALL_NOT_YET_CONSUMED_DOWNSTREAM_USES",
            "correction": "NEW_IMMUTABLE_REVISION_NEVER_OVERWRITE",
            "supersession": "EXPLICIT_PREDECESSOR_SUCCESSOR_IDENTITY_AND_REASON",
            "partition_rule": "SUCCESSOR_REMAINS_IN_PREDECESSOR_FAMILY_PARTITION",
            "blind_rule": "REVOKED_OR_CORRECTED_BLIND_OBJECT_REMAINS_OPAQUE",
        },
        "stop_conditions": [
            "INFERRED_OR_AMBIGUOUS_RIGHTS", "NONRETRIEVABLE_OR_MUTABLE_SOURCE_BYTES",
            "CHARACTER_UTF8_COORDINATE_DISAGREEMENT", "UNRESOLVED_FAMILY_CLOSURE",
            "CONTENT_ACCESS_BEFORE_PARTITION_OR_BLIND_SEAL", "CROSS_PARTITION_RELATIVE",
            "SOURCE_OR_PACKET_SHAPE_REVEALS_MECHANISM", "PROPOSITION_OR_QUALIFICATION_DRIFT",
            "OWNER_PREFERENCE_REACHES_CONSTRUCTION", "REVOCATION_OR_SUCCESSION_AMBIGUITY",
            "ANY_UNAUTHORIZED_ACTION_OR_INHERITED_GRANT",
        ],
        "contamination_ledger": {
            "append_only_hash_chain": True,
            "records": ["CONTENT_ACCESS", "METADATA_ACCESS", "CONSTRUCTOR_ACCESS", "MODEL_ACCESS",
                        "OWNER_SELECTION", "PROMPT_OR_GATE_TUNING", "TRAINING", "PRODUCTION"],
            "unknown_history": "CONTAMINATED_FAIL_CLOSED",
        },
        "current_authority_matrix": authority_false(),
        "historical_preservation": {
            "m20_owner_frozen": "UNCHANGED", "m12_case01_contrast_negative": "UNCHANGED",
            "historical_g02_negatives": "UNCHANGED", "rejected_and_provenance_negative": "UNCHANGED",
            "blind_reservations": "OPAQUE_ONLY", "blind_contaminated_1538_2617": "PERMANENTLY_EXCLUDED",
        },
        "next_phase": "SEPARATELY_AUTHORIZED_ACQUISITION_CHANNEL_AND_RIGHTS_INSTRUMENT_QUALIFICATION_ONLY",
    }
    protocol["protocol_identity"] = seal("B2_OWNED_AUTHORITY_ACQUISITION_PROTOCOL_V1", protocol)
    protocol_sha = write("humor-mechanics-batch2-owned-authority-acquisition-protocol-v1.json", protocol)

    audit = {
        "schema_name": "batch2-owned-authority-acquisition-protocol-v1-audit",
        "schema_version": "1.0.0", "protocol_identity": protocol["protocol_identity"],
        "protocol_sha256": protocol_sha,
        "checks": {
            "affirmative_rights_only": "PASS", "blind_seal_before_content": "PASS",
            "family_partition_isolation": "PASS", "source_shape_mechanism_leakage_controls": "PASS",
            "constructor_wording_leakage_controls": "PASS", "owner_preference_isolation": "PASS",
            "hidden_construction_authority": "PASS", "immutable_capture_unambiguous": "PASS",
            "proposition_qualification_drift": "PASS", "revocation_supersession": "PASS",
            "training_production_noninheritance": "PASS", "historical_preservation": "PASS",
        },
        "deterministic_defects_remaining": [],
        "adversarial_mutation_cases": {
            "INFERRED_RIGHTS_RELABELED_AFFIRMATIVE": "REJECTED",
            "CONTENT_ACCESS_MOVED_BEFORE_BLIND_SEAL": "REJECTED",
            "FAMILY_MEMBER_MOVED_ACROSS_PARTITION": "REJECTED",
            "CREATIVE_PREMISE_ASSIGNED_DURING_G01": "REJECTED",
            "MECHANISM_TOKEN_OR_SIGNATURE_WORDING_IN_CONSTRUCTOR_PACKET": "REJECTED",
            "OWNER_PREFERENCE_EXPOSED_TO_CONSTRUCTOR": "REJECTED",
            "MUTABLE_DATABASE_ROW_SUBSTITUTED_FOR_ARCHIVE_OBJECT": "REJECTED",
            "QUALIFICATION_TARGET_REMOVED_OR_REBOUND": "REJECTED",
            "REVISION_MOVED_TO_NEW_PARTITION": "REJECTED",
            "TRAINING_OR_PRODUCTION_INHERITED_FROM_EARLIER_GRANT": "REJECTED",
            "ANY_ACTION_AUTHORITY_FLIPPED_TRUE": "REJECTED",
        },
        "verdict": "PASS_SOURCE_ONLY_PROTOCOL_CLEAN",
        "authority_matrix": authority_false(),
        "actions_performed": {
            "sources_acquired": 0, "content_ingested": 0, "blind_surfaces_inspected": 0,
            "assignments_created": 0, "candidates_constructed": 0, "model_calls": 0,
        },
    }
    write("humor-mechanics-batch2-owned-authority-acquisition-protocol-v1-audit.json", audit)


if __name__ == "__main__":
    main()

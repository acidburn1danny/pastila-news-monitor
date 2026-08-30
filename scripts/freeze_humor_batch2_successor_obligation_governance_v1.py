"""Freeze source-only successor obligation governance and its audit artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
DISPOSITION_COMMIT = "82517cf7bc3dc97881f86151cff8eeff5e970596"
DISPOSITION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot01-candidate01-disposition-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def sealed(namespace: str, key: str, core: dict[str, Any]) -> dict[str, Any]:
    return {**core, key: seal(namespace, core)}


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    if path.exists():
        raise SystemExit(f"already frozen: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    disposition = json.loads(subprocess.check_output(["git", "show", f"{DISPOSITION_COMMIT}:{DISPOSITION_PATH}"], cwd=ROOT))
    assert disposition["disposition_identity"] == "f8e5efe963f0fc2bfdef975a2da4408cb3b91eb3268451f4e77576352948e3c8"
    assert disposition["disposition"] == "DEVELOPMENT_NONPOSITIVE_AMBIGUOUS_CONFUSABLE_EVIDENCE"
    visible_obligation = {
        "obligation_version": "SUCCESSOR_FORMULATION_B_V1",
        "transformation": [
            "Preserve exactly one authorized proposition without altering its factual content or qualification.",
            "Create a short, explicitly fictional continuation containing exactly two distinct changes; sentence and clause count are unconstrained.",
            "Keep one relation from the selected proposition operative across both changes.",
            "Make the second change unavailable unless the first change has occurred.",
            "Keep each change locally understandable from the selected proposition and the immediately preceding change.",
        ],
        "entity_status_rule": "Preserve every entity's authorized attributes, capabilities, agency status, and roles; do not add an attribute, capability, agency, or role absent from the factual-authority envelope.",
        "forbidden_operations": [
            "Do not import another domain or frame to provide the connection between changes.",
            "Do not obtain the result only by comparison, increasing magnitude or intensity, enumeration, or a disconnected surprise.",
            "Do not replace either change with an unrelated invented event.",
        ],
        "surface_freedom": [
            "No required catchphrase, connective, register, sentence count, clause pattern, or punchline form.",
            "Do not expose dependency-receipt field names or reviewer-only tests in constructor-visible bytes.",
        ],
        "factual_safety": [
            "Every nonfactual change must be locally unmistakable as fictional.",
            "No new factual premise, private knowledge, quotation, protected-target assertion, or pragmatic real-world implication.",
        ],
    }
    governance_core = {
        "schema_name": "batch2-successor-obligation-governance-v1", "schema_version": "1.0.0",
        "status": "FROZEN_SOURCE_ONLY_ZERO_CONSTRUCTION",
        "governance_parent": {"plan_commit": "c756135fa9b822dd945728a2df05f26f3b44fa63", "plan_identity": "57419ff52730ccd20acf3c716c9502667d9f25e517570e18eeae7ec3d472da8a"},
        "diagnostic_lineage": {"disposition_commit": DISPOSITION_COMMIT, "disposition_identity": disposition["disposition_identity"], "g03_reconciliation": "AMBIGUOUS_MECHANISM", "sealed_target": "ABSURD_LOGICAL_EXTENSION"},
        "constructor_visible_obligation": visible_obligation,
        "gate_sequence": [
            "B2_G02B_PRECONSTRUCTION_BLINDING",
            "CONSTRUCTION_SEPARATELY_AUTHORIZED_ONE_SHOT",
            "B2_G02B_POSTCONSTRUCTION_EXPOSURE_RECONCILIATION",
            "B2_G02_FACTUAL_AND_TARGET_BOUNDARY",
            "B2_G02C_OBLIGATION_CONFORMANCE",
            "B2_G03_BLIND_MECHANISM_RECOVERY",
        ],
        "g02c_reviewer_visible": ["IMMUTABLE_CANDIDATE_BYTES", "EXACT_FACTUAL_AUTHORITY_ENVELOPE", "EXACT_CONSTRUCTOR_VISIBLE_OBLIGATION", "MECHANISM_NEUTRAL_CONFORMANCE_SCHEMA"],
        "g02c_reviewer_prohibited": ["MECHANISM_ID_NAME_ORDINAL", "SEALED_ASSIGNMENT_MAPPING", "TARGET_EVIDENCE_ROLE", "G03_CHOICE_SET", "HISTORICAL_LABELS_OR_EXAMPLES", "OWNER_PREFERENCE", "BLIND_EVALUATION_MATERIAL"],
        "constructor_must_not_receive": ["CONFORMANCE_SCHEMA", "DEPENDENCY_RECEIPT_SCHEMA", "CONFORMANCE_FIELD_NAMES", "REMOVAL_TEST", "SEALED_TARGET_OR_MAPPING"],
        "failure_disposition": "DEVELOPMENT_NONPOSITIVE_OBLIGATION_NONCONFORMANT_DIAGNOSTIC",
        "repair_at_gate": False,
        "pilot01": {"regression_only": True, "another_construction_attempt": False, "candidate_rewrite_or_repair": False},
        "future_source_rule": {"fresh_independently_acquired_and_admitted_development_family_required": True, "prior_target_assignment_allowed": False, "prior_construction_exposure_allowed": False, "selection_by_target_friendly_topic_or_shape": False},
        "authority_matrix": {key: False for key in ("source_acquisition", "family_assignment", "candidate_construction", "generation", "repair", "g03b", "g03c", "g04", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    governance = sealed("B2_SUCCESSOR_OBLIGATION_GOVERNANCE_V1", "obligation_governance_identity", governance_core)
    schema_core = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:pastila:batch2:obligation-conformance-receipt:v1",
        "title": "Mechanism-neutral post-construction obligation conformance receipt V1",
        "type": "object", "additionalProperties": False,
        "required": ["candidate_identity", "obligation_identity", "selected_proposition", "continued_relation", "steps", "dependency", "imported_relation", "entity_status", "neighbor_substitution", "verdict"],
        "properties": {
            "candidate_identity": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "obligation_identity": {"const": governance["obligation_governance_identity"]},
            "selected_proposition": {"type": "object", "additionalProperties": False, "required": ["proposition_id", "source_span"], "properties": {"proposition_id": {"type": "string", "minLength": 1}, "source_span": {"$ref": "#/$defs/span"}}},
            "continued_relation": {"type": "object", "additionalProperties": False, "required": ["subject_span", "predicate_span", "object_span", "relation_fingerprint"], "properties": {"subject_span": {"$ref": "#/$defs/span"}, "predicate_span": {"$ref": "#/$defs/span"}, "object_span": {"$ref": "#/$defs/span"}, "relation_fingerprint": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}},
            "steps": {
                "type": "array", "minItems": 2, "maxItems": 2, "items": False,
                "prefixItems": [{
                    "type": "object", "additionalProperties": False,
                    "required": ["ordinal", "candidate_span", "same_relation_operates", "locally_understandable"],
                    "properties": {
                        "ordinal": {"const": 1}, "candidate_span": {"$ref": "#/$defs/span"},
                        "same_relation_operates": {"const": True}, "locally_understandable": {"const": True},
                    },
                }, {
                    "type": "object", "additionalProperties": False,
                    "required": ["ordinal", "candidate_span", "same_relation_operates", "locally_understandable"],
                    "properties": {
                        "ordinal": {"const": 2}, "candidate_span": {"$ref": "#/$defs/span"},
                        "same_relation_operates": {"const": True}, "locally_understandable": {"const": True},
                    },
                }],
            },
            "dependency": {"type": "object", "additionalProperties": False, "required": ["step2_requires_step1", "removal_test", "unrelated_replacement_possible"], "properties": {"step2_requires_step1": {"const": True}, "removal_test": {"const": "STEP2_STRUCTURALLY_UNAVAILABLE_WITHOUT_STEP1"}, "unrelated_replacement_possible": {"const": False}}},
            "imported_relation": {"type": "object", "additionalProperties": False, "required": ["present", "primary_connector"], "properties": {"present": {"const": False}, "primary_connector": {"const": False}}},
            "entity_status": {"type": "object", "additionalProperties": False, "required": ["unauthorized_attribute_or_role_added", "human_agency_supplies_connection"], "properties": {"unauthorized_attribute_or_role_added": {"const": False}, "human_agency_supplies_connection": {"const": False}}},
            "neighbor_substitution": {"type": "object", "additionalProperties": False, "required": ["comparison_or_domain_transfer", "magnitude_only", "enumeration", "disconnected_surprise"], "properties": {"comparison_or_domain_transfer": {"const": False}, "magnitude_only": {"const": False}, "enumeration": {"const": False}, "disconnected_surprise": {"const": False}}},
            "verdict": {"const": "PASS"},
        },
        "$defs": {"span": {"type": "object", "additionalProperties": False, "required": ["character_coordinates", "utf8_byte_coordinates", "sha256"], "properties": {"character_coordinates": {"$ref": "#/$defs/pair"}, "utf8_byte_coordinates": {"$ref": "#/$defs/pair"}, "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}}, "pair": {"type": "array", "prefixItems": [{"type": "integer", "minimum": 0}, {"type": "integer", "minimum": 0}], "items": False, "minItems": 2, "maxItems": 2}},
        "visibility": "REVIEWER_ONLY_NEVER_CONSTRUCTOR_VISIBLE",
        "fail_closed": True,
        "semantic_verification_rules": [
            "EVERY_SPAN_NONEMPTY_ORDERED_AND_ON_UTF8_BOUNDARIES",
            "CHARACTER_AND_UTF8_COORDINATES_RESOLVE_TO_IDENTICAL_TEXT",
            "EVERY_SPAN_SHA256_REDERIVED_FROM_EXACT_BOUND_BYTES",
            "SELECTED_PROPOSITION_AND_RELATION_SPANS_EQUAL_AUTHORITY_ENVELOPE_FIELDS",
            "RELATION_FINGERPRINT_REDERIVED_FROM_PROPOSITION_ID_AND_SUBJECT_PREDICATE_OBJECT_SPANS",
            "STEP_SPANS_DISTINCT_AND_ORDINALS_EXACTLY_1_THEN_2",
            "REMOVAL_TEST_PERFORMED_BY_BLIND_REVIEWER_NOT_CANDIDATE_OR_CONSTRUCTOR",
            "ANY_UNVERIFIABLE_OR_FREE_TEXT_ONLY_DEPENDENCY_CLAIM_FAILS_CLOSED",
        ],
    }
    schema = sealed("B2_OBLIGATION_CONFORMANCE_SCHEMA_V1", "conformance_schema_identity", schema_core)
    regression_core = {
        "schema_name": "batch2-pilot01-successor-obligation-regression-v1", "schema_version": "1.0.0",
        "candidate_identity": disposition["candidate_identity"], "disposition_identity": disposition["disposition_identity"],
        "obligation_governance_identity": governance["obligation_governance_identity"], "conformance_schema_identity": schema["conformance_schema_identity"],
        "expected_verdict": "FAIL", "observed_verdict": "FAIL",
        "stable_reasons": ["ABSTRACT_RULE_ASSIGNED_OCCUPATIONAL_AGENCY", "EMPLOYMENT_TIMESHEET_DOMAIN_IMPORTED", "IMPORTED_FRAME_SUPPLIES_PRIMARY_CONNECTION", "P6_DERIVED_SAME_RELATION_CHAIN_NOT_DEMONSTRATED", "STEP2_DEPENDS_ON_IMPORTED_FRAME_NOT_P6_RELATION"],
        "candidate_modified": False, "construction_invoked": False, "another_pilot01_attempt_allowed": False,
    }
    regression = sealed("B2_PILOT01_SUCCESSOR_OBLIGATION_REGRESSION_V1", "regression_identity", regression_core)
    audit_core = {
        "schema_name": "batch2-successor-obligation-leakage-audit-v1", "schema_version": "1.0.0",
        "obligation_governance_identity": governance["obligation_governance_identity"], "conformance_schema_identity": schema["conformance_schema_identity"],
        "verdict": "PASS_AFTER_REMEDIATION",
        "remediations": ["PRESERVED_PRECONSTRUCTION_G02B_IN_GATE_ORDER", "MOVED_TYPED_SPAN_DEPENDENCY_FIELDS_TO_REVIEWER_ONLY_SCHEMA", "REPLACED_VISIBLE_HUMAN_CATEGORY_LIST_AS_PRIMARY_RULE_WITH_GENERIC_AUTHORIZED_ENTITY_STATUS_RULE", "PROHIBITED_FIXED_SENTENCE_OR_CLAUSE_SHAPE", "REQUIRED_EXACT_RELATION_AND_STEP_SPANS", "REQUIRED_STRUCTURAL_REMOVAL_TEST"],
        "checks": {
            "taxonomy_name_id_ordinal_leakage": "PASS_NONE_IN_CONSTRUCTOR_VISIBLE_BYTES",
            "definitional_paraphrase_leakage": "PASS_OPERATIONAL_DETAIL_NECESSARY_AND_NOT_MATERIALLY_GREATER_THAN_PREDECESSOR",
            "neighbor_answer_leakage": "PASS_GENERIC_ENTITY_STATUS_RULE_AND_OPERATIONAL_EXCLUSIONS",
            "lexical_shortcuts": "PASS_NO_REQUIRED_LEXEME",
            "grammatical_form_shortcuts": "PASS_NO_REQUIRED_FORM",
            "fixed_two_sentence_or_clause_template": "PASS_TWO_CHANGES_BUT_SURFACE_SHAPE_UNCONSTRAINED",
            "causal_connective_shortcut": "PASS_NO_REQUIRED_CONNECTIVE",
            "source_shape_correlation": "PASS_FRESH_FAMILY_SELECTION_MUST_PRECEDE_TARGET_AND_IGNORE_TARGET_FRIENDLY_SHAPE",
            "state_machine_signature": "PASS_NO_VISIBLE_STATE_TRANSITION_VOCABULARY",
            "register_or_punchline_repetition": "PASS_REGISTER_AND_LANDING_UNCONSTRAINED",
            "receipt_field_leakage": "PASS_SCHEMA_REVIEWER_ONLY_AND_HASH_BOUND",
            "hidden_construction_authority": "PASS_ALL_OPERATIONAL_AUTHORITIES_FALSE",
        },
        "constructor_visible_schema_exposure": False, "pilot01_surface_reused_for_construction": False,
    }
    audit = sealed("B2_SUCCESSOR_OBLIGATION_LEAKAGE_AUDIT_V1", "leakage_audit_identity", audit_core)
    write("humor-mechanics-batch2-successor-obligation-governance-v1.json", governance)
    write("humor-mechanics-batch2-obligation-conformance-schema-v1.json", schema)
    write("humor-mechanics-batch2-pilot01-successor-obligation-regression-v1.json", regression)
    write("humor-mechanics-batch2-successor-obligation-leakage-audit-v1.json", audit)
    print(json.dumps({"obligation_identity": governance["obligation_governance_identity"], "conformance_schema_identity": schema["conformance_schema_identity"], "regression_identity": regression["regression_identity"], "leakage_audit_identity": audit["leakage_audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()

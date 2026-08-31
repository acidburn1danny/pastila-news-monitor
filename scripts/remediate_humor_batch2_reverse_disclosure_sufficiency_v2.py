"""Freeze source-only reverse-disclosure proposition-sufficiency governance V2."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
DISPOSITION_COMMIT = "6662562b7034d08e73cdbc8b4db038636969c4ba"
ASSIGNMENT_COMMIT = "def90e29e81f42e41e3cb77417000710207dc88a"
DISPOSITION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-g02c-rejection-disposition-v1.json"
ASSIGNMENT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-sealed-rebalancing-assignment-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def sealed(namespace: str, field: str, core: dict[str, Any]) -> dict[str, Any]:
    return {**core, field: seal(namespace, core)}


def write(name: str, value: Any) -> None:
    path = ART / name
    require(not path.exists(), f"already exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == DISPOSITION_COMMIT, "HEAD")
    disposition = load(DISPOSITION_COMMIT, DISPOSITION_PATH)
    assignment = load(ASSIGNMENT_COMMIT, ASSIGNMENT_PATH)
    require(disposition["disposition_identity"] == "6214b4423ebe627d28b57ad816d14b446b66f6094806ca708d6db1eb38154f9f", "disposition")
    require(disposition["g02c_verdict"] == "FAIL_INCOMPLETE_RECOVERABLE_REVERSE_DEPENDENCY", "failure")
    require(assignment["obligation_family_identity"] == "8379c38c191ab850a6af30ee16a751fb750710554a957e6e57c3f89955de404a", "family")

    analysis_core = {
        "schema_name": "batch2-pilot05-reverse-dependency-root-cause-analysis-v1", "schema_version": "1.0.0",
        "disposition_commit": DISPOSITION_COMMIT, "disposition_identity": disposition["disposition_identity"],
        "candidate_identity": disposition["candidate_identity"], "candidate_modified": False,
        "observed_failure": {"g02c_verdict": disposition["g02c_verdict"],
                             "earliest_failed_link": disposition["earliest_failed_link"],
                             "selected_proposition_id": "P3",
                             "missing_anchor": "NUMERIC_VALUE_OF_THE_SAME_REFERENCE",
                             "unsupported_intermediate": "INVENTED_0_1_DIFFERENCE"},
        "selected_proposition_sufficiency": {
            "p3_standalone_semantic_closure": "FAIL_UNRESOLVED_SAME_REFERENCE_OUTSIDE_SELECTED_SPAN",
            "p3_numeric_operand_closure": "FAIL_ONLY_20_1_IS_PRESENT",
            "p3_supports_non_arbitrary_adjacent_reverse_link": False,
            "candidate_could_substitute_another_difference_without_changing_p3": True,
        },
        "governance_root_causes": [
            "NEGATIVE_NOT_PRECLUDED_TEST_USED_IN_PLACE_OF_POSITIVE_SUFFICIENCY_PROOF",
            "ALL_SEVEN_PROPOSITIONS_MARKED_SATISFIABLE_WITHOUT_PROPOSITION_SPECIFIC_WITNESSES",
            "NO_STANDALONE_SEMANTIC_CLOSURE_CHECK_FOR_DEICTIC_OR_CROSS_PROPOSITION_REFERENCES",
            "NO_OPERAND_CLOSURE_CHECK_FOR_DERIVED_QUANTITIES",
            "SELECTED_PROPOSITION_NOT_BOUND_BEFORE_CONSTRUCTOR_RELEASE",
            "G02B_DID_NOT_VERIFY_SELECTED_PROPOSITION_SUFFICIENCY_ARTIFACT",
        ],
        "primary_responsibility": "REBALANCING_ASSIGNMENT_GOVERNANCE_BOUNDARY",
        "constructor_contribution": "SELECTED_P3_AND_INVENTED_0_1_WITHOUT_A_CLOSED_ANCHOR",
        "verdict": "ROOT_CAUSE_CONFIRMED_GOVERNANCE_ALLOWED_AN_UNPROVEN_PROPOSITION",
    }
    analysis = sealed("B2_PILOT05_REVERSE_DEPENDENCY_ROOT_CAUSE_ANALYSIS_V1", "analysis_identity", analysis_core)

    governance_core = {
        "schema_name": "batch2-reverse-disclosure-dependency-governance-v2", "schema_version": "2.0.0",
        "supersedes_obligation_family_identity": assignment["obligation_family_identity"],
        "family_version": "REVERSE_DISCLOSURE_DEPENDENCY_V2",
        "scope": "SOURCE_ONLY_ASSIGNMENT_AND_PRECONSTRUCTION_ADMISSION_GOVERNANCE",
        "mandatory_pre_assignment_gate": {
            "gate_name": "REVERSE_DISCLOSURE_SELECTED_PROPOSITION_SUFFICIENCY_V2",
            "evaluation_order": "BEFORE_SEALED_ASSIGNMENT_AND_BEFORE_CONSTRUCTOR_PACKET",
            "required_checks": [
                "EXACTLY_ONE_SELECTED_PROPOSITION_BOUND",
                "SELECTED_SUPPORTING_SPAN_STANDALONE_SEMANTICALLY_CLOSED",
                "ALL_DEICTIC_PRONOMINAL_COMPARATIVE_AND_REFERENCE_DEPENDENCIES_RESOLVED_INSIDE_AUTHORIZED_VISIBLE_CONTEXT",
                "ALL_OPERANDS_NEEDED_FOR_ANY_REQUIRED_DERIVED_QUANTITY_BOUND",
                "AT_LEAST_ONE_NON_ARBITRARY_ADJACENT_LINK_FROM_SELECTED_FACTUAL_RELATION_HAS_A_SOURCE_ONLY_WITNESS",
                "WITNESS_USES_ABSTRACT_RELATIONS_ONLY_AND_CONTAINS_NO_CANDIDATE_SURFACE_OR_HUMOR",
                "QUALIFICATION_SCOPE_TIME_MODALITY_AND_UNKNOWN_BOUNDARIES_PRESERVED",
            ],
            "fail_closed_outcomes": ["NO_SAFE_SELECTED_PROPOSITION", "NO_SAFE_REBALANCING_ASSIGNMENT"],
            "not_sufficient": ["NOT_PRECLUDED", "CLOSED_AUTHORITY_AVAILABLE", "TOPIC_PLAUSIBILITY", "CONSTRUCTOR_CAN_INVENT_A_LINK"],
        },
        "assignment_binding_rules": {
            "selected_proposition_id_bound_before_release": True,
            "selected_supporting_span_hash_bound_before_release": True,
            "authorized_visible_context_bound_before_release": True,
            "sufficiency_receipt_identity_bound_before_release": True,
            "constructor_may_not_choose_an_unbound_proposition": True,
            "multi_proposition_context_requires_separate_explicit_authorization_and_combined_envelope": True,
            "target_mechanism_mapping_remains_sealed": True,
        },
        "g02b_additional_checks": [
            "EXACT_SELECTED_PROPOSITION_AND_CONTEXT_EQUALITY",
            "SUFFICIENCY_RECEIPT_SEAL_AND_STATUS_PASS",
            "NO_EXTRA_PROPOSITION_OR_UNBOUND_CONTEXT",
            "NO_LABEL_OR_TARGET_MAPPING_EXPOSURE",
        ],
        "g02c_additional_checks": [
            "TRACE_EACH_REVERSE_LINK_TO_ITS_IMMEDIATE_SUCCESSOR",
            "REJECT_ANY_LINK_REPLACEABLE_WITH_AN_ARBITRARY_VALUE_OR_EVENT",
            "REJECT_DERIVED_QUANTITY_IF_ANY_OPERAND_IS_UNBOUND",
            "REJECT_UNRESOLVED_DEICTIC_OR_CROSS_PROPOSITION_REFERENCE",
        ],
        "construction_authority": False, "model_exposure_authority": False, "training_authority": False,
        "runtime_authority": False, "production_authority": False,
    }
    governance = sealed("B2_REVERSE_DISCLOSURE_DEPENDENCY_GOVERNANCE_V2", "governance_identity", governance_core)

    schema_core = {
        "schema_name": "batch2-reverse-disclosure-selected-proposition-sufficiency-receipt-v2", "schema_version": "2.0.0",
        "governance_identity": governance["governance_identity"],
        "required_fields": ["source_package_identity", "authority_envelope_identity", "selected_proposition_id",
                            "selected_supporting_span_sha256", "authorized_visible_context_sha256", "standalone_semantic_closure",
                            "reference_resolution", "operand_closure", "abstract_adjacent_link_witness", "qualification_preservation",
                            "verdict"],
        "pass_condition": "ALL_REQUIRED_CHECKS_TRUE_AND_WITNESS_NONEMPTY_AND_MECHANISM_NEUTRAL",
        "allowed_verdicts": ["PASS_SELECTED_PROPOSITION_SUFFICIENT", "NO_SAFE_SELECTED_PROPOSITION", "NO_SAFE_REBALANCING_ASSIGNMENT"],
        "candidate_surface_forbidden": True, "mechanism_label_forbidden": True, "construction_authority": False,
    }
    schema = sealed("B2_REVERSE_DISCLOSURE_SUFFICIENCY_SCHEMA_V2", "schema_identity", schema_core)

    regression_core = {
        "schema_name": "batch2-pilot05-reverse-disclosure-regression-v1", "schema_version": "1.0.0",
        "analysis_identity": analysis["analysis_identity"], "governance_identity": governance["governance_identity"],
        "fixture": {"source_sha256": "e3404a694bf1203f8a11ceeed0e682511882237e4777bd0e092876994c4326cc",
                    "selected_proposition_id": "P3", "selected_span_sha256": "28360169bf1e83a0a487fabb520866ae734337e1dd42652952b8af82b7101089",
                    "unresolved_reference": "aceeași referință", "available_numeric_operands": ["20.1"],
                    "attempted_derived_quantity": "0.1"},
        "expected_preconstruction_result": "NO_SAFE_SELECTED_PROPOSITION",
        "old_governance_result": "INCORRECTLY_ADMITTED_AS_NOT_PRECLUDED",
        "new_governance_result": "REJECTED_BEFORE_CONSTRUCTOR_RELEASE",
        "candidate_reexecution_performed": False,
    }
    regression = sealed("B2_PILOT05_REVERSE_DISCLOSURE_REGRESSION_V1", "regression_identity", regression_core)

    audit_core = {
        "schema_name": "batch2-reverse-disclosure-governance-v2-audit-v1", "schema_version": "1.0.0",
        "analysis_identity": analysis["analysis_identity"], "governance_identity": governance["governance_identity"],
        "schema_identity": schema["schema_identity"], "regression_identity": regression["regression_identity"],
        "positive_sufficiency_replaces_not_precluded": "PASS", "standalone_reference_closure": "PASS",
        "derived_operand_closure": "PASS", "selected_proposition_prebinding": "PASS",
        "g02b_binding_propagation": "PASS", "g02c_fail_closed_predicates": "PASS",
        "mechanism_label_leakage": "PASS_NONE", "candidate_surface_created_or_modified": False,
        "hidden_construction_authority": "PASS_NONE", "blind_material_accessed": False,
        "deterministic_blockers": [], "verdict": "PASS_SOURCE_ONLY_ZERO_CONSTRUCTION",
    }
    audit = sealed("B2_REVERSE_DISCLOSURE_GOVERNANCE_V2_AUDIT_V1", "audit_identity", audit_core)
    write("humor-mechanics-batch2-pilot05-reverse-dependency-root-cause-analysis-v1.json", analysis)
    write("humor-mechanics-batch2-reverse-disclosure-dependency-governance-v2.json", governance)
    write("humor-mechanics-batch2-reverse-disclosure-sufficiency-schema-v2.json", schema)
    write("humor-mechanics-batch2-pilot05-reverse-disclosure-regression-v1.json", regression)
    write("humor-mechanics-batch2-reverse-disclosure-governance-v2-audit-v1.json", audit)
    print(json.dumps({"analysis_verdict": analysis["verdict"], "analysis_identity": analysis["analysis_identity"],
                      "governance_identity": governance["governance_identity"], "schema_identity": schema["schema_identity"],
                      "regression_identity": regression["regression_identity"], "audit_identity": audit["audit_identity"],
                      "audit_verdict": audit["verdict"]}, sort_keys=True))


if __name__ == "__main__":
    main()

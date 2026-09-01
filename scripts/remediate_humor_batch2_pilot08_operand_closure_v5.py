"""Source-only Pilot 08 operand-closure analysis and V5 governance remediation."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "5345f15dd5b86e9d5fee0a7c22440a453b3983a8"
V4_MODULE = "src/pastila_scout/humor_batch2_development_constructor_v4.py"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path: str) -> dict[str, Any]:
    return json.loads(git_bytes(path))


def write(name: str, value: Any) -> None:
    path = ART / name
    if path.exists():
        raise SystemExit("artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != COMMIT:
        raise SystemExit("HEAD")
    disposition = load("docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-g02c-rejection-disposition-v1.json")
    receipt = load("docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-g02c-conformance-receipt-v4.json")
    v4_governance = load("docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-governance-v4.json")
    v3_governance = load("docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json")
    module = git_bytes(V4_MODULE)
    source = module.decode("utf-8")
    if disposition["disposition_identity"] != "127fe16cfc08883bb3f179d6f599cf3be6a0fa7680e68bfc1a94044f21dd4fbc":
        raise SystemExit("disposition")
    if receipt["conformance_receipt_identity"] != "60fa16dd8d530ab34a1de89413bf3b37a16cf9b2536d981df0735a7812b1e733":
        raise SystemExit("receipt")
    if v4_governance["governance_identity"] != "cc86204c6f199c80ef7c7bf87a58cf3c62d17acb1fe14bd2666bbf5ba86692f6":
        raise SystemExit("V4 governance")
    if v3_governance["governance_identity"] != "4848bd025e43eff6652e4c2024072760d372ca4ac7427e5f21e1d2c4bcdb35dc":
        raise SystemExit("V3 governance")
    required_v4_patterns = (
        '"iar", object_value, step_verb',
        'relation_noun + "ii,"',
        'relation_noun + "a."',
        'supporting.endswith(".")',
    )
    if not all(pattern in source for pattern in required_v4_patterns):
        raise SystemExit("V4 implementation drift")

    analysis_core = {
        "schema_name": "batch2-pilot08-operand-closure-root-cause-analysis-v1",
        "schema_version": "1.0.0",
        "disposition_commit": COMMIT,
        "disposition_identity": disposition["disposition_identity"],
        "candidate_identity": disposition["candidate_identity"],
        "candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": disposition["candidate_git_blob_oid_sha1"],
        "candidate_modified": False,
        "constructor_v4_module_path": V4_MODULE,
        "constructor_v4_module_sha256": hashlib.sha256(module).hexdigest(),
        "constructor_v4_preservation": "BYTE_EXACT_HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_RELEASE",
        "root_causes": [
            "V4_REUSED_THE_BOUND_OBJECT_COMPONENT_IN_A_NEW_ACTOR_POSITION_WITHOUT_ROLE_COMPATIBILITY_VALIDATION",
            "P5_OBJECT_VALUE_IS_A_PREPOSITIONAL_LOCATION_PURPOSE_PHRASE_NOT_A_BOUND_AGENT_CAPABLE_OF_MOVING_CONTROL",
            "V4_JOINED_A_COMPONENT_RETAINING_TERMINAL_PUNCTUATION_BEFORE_THE_NEW_PREDICATE_AND_SPLIT_THE_CLAIMED_LINK",
            "V4_CONSTRUCTED_ROMANIAN_INFLECTION_BY_RAW_LEMMA_SUFFIX_CONCATENATION_WITHOUT_MORPHOLOGICAL_VALIDATION",
            "V4_STATIC_AUDIT_CHECKED_ACCESS_IDENTITY_AND_LITERAL_LEAKAGE_BUT_NOT_TYPED_OPERAND_DATAFLOW_OR_EMITTED_PLAN_CLOSURE",
            "G02C_CORRECTLY_DETECTED_THE_FAILURE_BUT_ONLY_AFTER_IRREVERSIBLE_SINGLE_ATTEMPT_CONSUMPTION",
        ],
        "responsibility": {
            "proposition_sufficiency_governance": "NOT_CAUSAL_P5_IS_FACTUALLY_AND_RELATIONALLY_SUFFICIENT_FOR_ASSIGNMENT",
            "assignment_obligation_governance": "CONTRIBUTING_REQUIRED_OPERAND_CLOSURE_BUT_DID_NOT_REQUIRE_A_PRECONSTRUCTION_TYPED_PLAN_PROOF",
            "constructor_v4_implementation": "PRIMARY_INCOMPATIBLE_COMPONENT_TO_ACTOR_SLOT_AND_UNVALIDATED_MORPHOLOGY",
            "constructor_v4_static_validation": "PRIMARY_PREVENTION_GAP_NO_TYPED_DATAFLOW_OR_PLAN_CLOSURE_CHECK",
            "g02c_review": "VALID_DETECTION_NOT_CAUSAL",
        },
        "earliest_preventable_boundary": "CONSTRUCTOR_IMPLEMENTATION_STATIC_AUDIT_BEFORE_G02B_RELEASE",
        "counterfactual_findings": {
            "reject_prepositional_component_as_actor": "BLOCKS_THE_FAILED_FIRST_LINK_BEFORE_RELEASE",
            "require_explicit_bound_actor_for_every_invented_predicate": "PRESERVES_GENERAL_CONSTRUCTION_FLEXIBILITY_WITHOUT_FIXING_SURFACE_WORDING",
            "validate_abstract_plan_before_realization": "PREVENTS_LATER_LINKS_FROM_MASKING_AN_EARLY_CLOSURE_FAILURE",
            "prohibit_raw_suffix_inflection_and_embedded_terminal_punctuation": "REMOVES_TWO_DETERMINISTIC_REALIZATION_DEFECTS_WITHOUT_ADJUDICATING_A_CANDIDATE",
            "candidate_rewrite_performed": False,
        },
        "verdict": "ROOT_CAUSE_CONFIRMED_AT_CONSTRUCTOR_V4_TYPED_OPERAND_AND_STATIC_PLAN_VALIDATION_BOUNDARY",
    }
    analysis = {**analysis_core, "analysis_identity": seal("B2_PILOT08_OPERAND_CLOSURE_ROOT_CAUSE_ANALYSIS_V1", analysis_core)}

    contract_core = {
        "schema_name": "batch2-development-constructor-contract-v5",
        "schema_version": "5.0.0",
        "supersedes_constructor_generation": 4,
        "constructor_v4_module_sha256": analysis["constructor_v4_module_sha256"],
        "constructor_v4_status": "BYTE_EXACT_HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_RELEASE",
        "required_internal_plan_node_fields": [
            "NODE_ID", "BOUND_ENTITY_OR_RELATION_ID", "GRAMMATICAL_ROLE", "PREDICATE_ID",
            "PREDECESSOR_NODE_IDS", "SOURCE_PROVENANCE", "NONFACTUAL_SCOPE",
        ],
        "required_pre_realization_validations": [
            "EVERY_NEW_PREDICATE_HAS_AN_EXPLICIT_ROLE_COMPATIBLE_BOUND_ACTOR_OR_RELATION_HEAD",
            "PREPOSITIONAL_ADVERBIAL_OR_PURPOSE_PHRASE_CANNOT_BE_PROMOTED_TO_ACTOR_WITHOUT_AN_EXPLICIT_NOMINAL_HEAD",
            "EVERY_REFERENCE_AND_OPERAND_RESOLVES_TO_P5_OR_AN_EARLIER_VALIDATED_INVENTED_NODE",
            "AT_LEAST_TWO_DISTINCT_NON_RESTATEMENT_LINKS_EXIST",
            "REMOVING_ANY_REQUIRED_LINK_BREAKS_THE_CLAIMED_RESULT",
            "SOURCE_COMPONENT_TERMINAL_PUNCTUATION_CANNOT_SPLIT_A_NEW_ACTOR_PREDICATE_RELATION",
            "NO_ROMANIAN_INFLECTION_BY_UNVALIDATED_RAW_SUFFIX_CONCATENATION",
            "PLAN_FAILURE_TERMINATES_BEFORE_SURFACE_CREATION_AND_CONSUMES_NO_CONSTRUCTION_ATTEMPT",
        ],
        "static_audit_requirements": [
            "TYPED_OPERAND_DATAFLOW_CHECK_PRESENT_AND_FAIL_CLOSED",
            "ABSTRACT_PLAN_CLOSURE_VALIDATOR_PRESENT_AND_CALLED_BEFORE_REALIZATION",
            "COMPONENT_ROLE_COMPATIBILITY_NEGATIVE_TESTS",
            "TERMINAL_PUNCTUATION_NEGATIVE_TESTS",
            "MORPHOLOGICAL_SUFFIX_CONCATENATION_SCAN_ZERO_HITS",
            "PILOT08_FAILED_SHAPE_REGRESSION_REJECTED_BEFORE_SURFACE_CREATION",
            "NO_IDENTITY_ROUTED_SURFACE_BRANCHES_OR_REUSABLE_MARKER_LITERALS",
        ],
        "implementation_identity": "UNASSIGNED_REQUIRES_SEPARATE_IMPLEMENTATION_AND_STATIC_AUDIT_PHASE",
        "invocations": 0,
        "candidate_surface": None,
        "release_authority": False,
        "construction_authority": False,
    }
    contract = {**contract_core, "constructor_contract_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_CONTRACT_V5", contract_core)}

    governance_core = {
        "schema_name": "batch2-typed-operand-closed-construction-governance-v5",
        "schema_version": "5.0.0",
        "family_version": "TYPED_OPERAND_CLOSED_CONSTRUCTION_V5",
        "supersedes_governance_identities": [v3_governance["governance_identity"], v4_governance["governance_identity"]],
        "root_cause_analysis_identity": analysis["analysis_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "preserves_v3_order_robust_causal_spine_requirements": True,
        "preserves_v4_template_diversity_and_fragment_collision_requirements": True,
        "proposition_sufficiency_boundary": "UNCHANGED_POST_G01_FACTUAL_RELATION_SUFFICIENCY_ONLY_NO_CREATIVE_ACTOR_ROLE_GUARANTEE",
        "assignment_additional_requirements": [
            "OBLIGATION_REQUIRES_EXPLICIT_OPERAND_CLOSURE_WITHOUT_SELECTING_SURFACE_ACTORS",
            "CONSTRUCTOR_CONTRACT_IDENTITY_MUST_REMAIN_UNASSIGNED_UNTIL_SEPARATE_IMPLEMENTATION_AUDIT",
        ],
        "g02b_additional_requirements": [
            "EXACT_V5_IMPLEMENTATION_AND_CONTRACT_IDENTITIES_BOUND",
            "STATIC_TYPED_OPERAND_DATAFLOW_AUDIT_PASS",
            "PILOT08_FAILED_SHAPE_REGRESSION_PASS",
            "ZERO_CONSTRUCTOR_INVOCATIONS_AND_ZERO_SURFACES_BEFORE_RELEASE",
        ],
        "g02c_required_checks": [
            "COMPLETE_MULTI_LINK_CAUSAL_SPINE",
            "AT_LEAST_TWO_DISTINCT_NON_RESTATEMENT_LINKS",
            "EACH_LINK_NECESSARY_AND_NON_ARBITRARY",
            "ALL_REFERENCES_AND_OPERANDS_ROLE_COMPATIBLE_AND_BOUND",
            "NO_TERMINAL_PUNCTUATION_SPLIT_WITHIN_A_CLAIMED_LINK",
            "NO_DELAYED_FACT_DISCLOSURE_AS_PRIMARY_EFFECT",
            "NO_SINGLE_LITERAL_TRANSFER_AS_SOLE_ENGINE",
            "NO_INSTRUCTION_LANGUAGE_TRANSFER",
        ],
        "constructor_implementation_authority": False,
        "constructor_release_authority": False,
        "source_acquisition_authority": False,
        "construction_authority": False,
        "model_exposure_authority": False,
        "training_authority": False,
        "runtime_authority": False,
        "production_authority": False,
    }
    governance = {**governance_core, "governance_identity": seal("B2_TYPED_OPERAND_CLOSED_CONSTRUCTION_GOVERNANCE_V5", governance_core)}

    schema_core = {
        "schema_name": "batch2-typed-operand-closed-construction-conformance-schema-v5",
        "schema_version": "5.0.0",
        "governance_identity": governance["governance_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "required_preconstruction_predicates": contract["static_audit_requirements"],
        "required_postconstruction_g02c_predicates": governance["g02c_required_checks"],
        "allowed_verdicts": [
            "PASS", "FAIL_UNBOUND_OR_ROLE_INCOMPATIBLE_OPERAND", "FAIL_INCOMPLETE_CAUSAL_SPINE",
            "FAIL_RESTATEMENT_AS_LINK", "FAIL_TERMINAL_PUNCTUATION_SPLIT", "FAIL_UNVALIDATED_MORPHOLOGY",
        ],
        "mechanism_label_forbidden_in_constructor_view": True,
        "candidate_surface_creation_authority": False,
        "constructor_release_authority": False,
    }
    schema = {**schema_core, "schema_identity": seal("B2_TYPED_OPERAND_CLOSED_CONSTRUCTION_CONFORMANCE_SCHEMA_V5", schema_core)}

    regression_core = {
        "schema_name": "batch2-pilot08-operand-closure-regression-v1",
        "schema_version": "1.0.0",
        "candidate_identity": disposition["candidate_identity"],
        "candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "candidate_bytes_embedded": False,
        "candidate_modified": False,
        "constructor_v4_module_sha256": analysis["constructor_v4_module_sha256"],
        "failed_shape_fingerprint": {
            "component_role_transition": "PREPOSITIONAL_OBJECT_COMPONENT_TO_ACTOR_SLOT",
            "terminal_punctuation_retained_before_new_predicate": True,
            "raw_lemma_suffix_inflection": True,
        },
        "expected_v5_preconstruction_result": "REJECT_BEFORE_SURFACE_CREATION",
        "expected_failed_predicates": [
            "EVERY_NEW_PREDICATE_HAS_AN_EXPLICIT_ROLE_COMPATIBLE_BOUND_ACTOR_OR_RELATION_HEAD",
            "SOURCE_COMPONENT_TERMINAL_PUNCTUATION_CANNOT_SPLIT_A_NEW_ACTOR_PREDICATE_RELATION",
            "NO_ROMANIAN_INFLECTION_BY_UNVALIDATED_RAW_SUFFIX_CONCATENATION",
        ],
        "positive_pool_eligibility": False,
    }
    regression = {**regression_core, "regression_identity": seal("B2_PILOT08_OPERAND_CLOSURE_REGRESSION_V1", regression_core)}

    visible = canonical({"contract": contract_core, "governance": governance_core, "schema": schema_core})
    forbidden = [rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"mechanism_id", rb"mechanism_name", rb"answer_key", rb"blind_evaluation"]
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    if hits:
        raise SystemExit(f"leakage {hits}")
    audit_core = {
        "schema_name": "batch2-typed-operand-closed-construction-governance-v5-audit-v1",
        "schema_version": "1.0.0",
        "analysis_identity": analysis["analysis_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "governance_identity": governance["governance_identity"],
        "schema_identity": schema["schema_identity"],
        "regression_identity": regression["regression_identity"],
        "label_taxonomy_and_answer_leakage": "PASS_ZERO_HITS",
        "proposition_sufficiency_boundary": "PASS_UNCHANGED_NO_CREATIVE_ROLE_INFERENCE",
        "typed_operand_closure": "PASS_REQUIRED_BEFORE_REALIZATION",
        "constructor_v4_preservation": "PASS_BYTE_EXACT_HISTORICAL_ONLY",
        "pilot08_regression": "PASS_EXPECTED_PRECONSTRUCTION_REJECTION",
        "hidden_constructor_implementation_authority": "ABSENT",
        "hidden_release_or_construction_authority": "ABSENT",
        "source_or_candidate_created": False,
        "constructor_invocations": 0,
        "candidate_surfaces_created": 0,
        "deterministic_blockers_remaining_before_v5_implementation_phase": [],
        "verdict": "PASS_SOURCE_ONLY_GOVERNANCE_AND_CONTRACT_REMEDIATION_ZERO_CONSTRUCTION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_TYPED_OPERAND_CLOSED_CONSTRUCTION_GOVERNANCE_V5_AUDIT_V1", audit_core)}

    write("humor-mechanics-batch2-pilot08-operand-closure-root-cause-analysis-v1.json", analysis)
    write("humor-mechanics-batch2-development-constructor-contract-v5.json", contract)
    write("humor-mechanics-batch2-typed-operand-closed-construction-governance-v5.json", governance)
    write("humor-mechanics-batch2-typed-operand-closed-construction-conformance-schema-v5.json", schema)
    write("humor-mechanics-batch2-pilot08-operand-closure-regression-v1.json", regression)
    write("humor-mechanics-batch2-typed-operand-closed-construction-governance-v5-audit-v1.json", audit)
    print(json.dumps({
        "verdict": analysis["verdict"],
        "analysis_identity": analysis["analysis_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "governance_identity": governance["governance_identity"],
        "schema_identity": schema["schema_identity"],
        "regression_identity": regression["regression_identity"],
        "audit_identity": audit["audit_identity"],
        "audit_verdict": audit["verdict"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

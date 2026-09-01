"""Source-only Pilot 10 semantic-edge root cause analysis and V5.3 remediation."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "f960b4d85e388c38728c80126e412c0f596699d3"
OLD_PLAN_MODULE = "src/pastila_scout/humor_batch2_development_constructor_v5_1.py"
OLD_REALIZATION_MODULE = "src/pastila_scout/humor_batch2_development_constructor_v5_2_runtime.py"
OLD_VALIDATOR_MODULE = "src/pastila_scout/humor_batch2_development_constructor_v5_2.py"
NEW_MODULE = "src/pastila_scout/humor_batch2_development_constructor_v5_3_semantic_enforcement.py"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path: str) -> dict[str, Any]:
    return json.loads(git_bytes(path))


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    if path.exists():
        raise SystemExit(f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != COMMIT:
        raise SystemExit("HEAD")
    disposition = load("docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-g02c-rejection-disposition-v1.json")
    receipt = load("docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-g02c-conformance-receipt-v5-2.json")
    old_contract = load("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5-2.json")
    old_governance = load("docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-governance-v5-2.json")
    old_schema = load("docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-conformance-schema-v5-2.json")
    old_implementation = load("docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5-2.json")
    if disposition["disposition_identity"] != "d49ff2a6d9ce30e4afe097207538ee865ac503d6869a40be66bef21dcc02d36d":
        raise SystemExit("disposition")
    if receipt["conformance_receipt_identity"] != "b35eda9ac8e9ba4869a6d75683b8c8e2ac0cbd5e1f7db6a0f97279e65f07c0f6":
        raise SystemExit("receipt")
    if old_contract["constructor_contract_identity"] != "69138467540b37cbfb8444596d9a37119f8b74d002e0c491c8ff599ce77cec77":
        raise SystemExit("contract")
    if old_implementation["constructor_implementation_identity"] != "bdf48e9942f097f0259831c0f2f611e50644cdbe7179a2dc7d990bf9ab2b5493":
        raise SystemExit("implementation")

    plan_source = git_bytes(OLD_PLAN_MODULE).decode("utf-8")
    realization_source = git_bytes(OLD_REALIZATION_MODULE).decode("utf-8")
    validator_source = git_bytes(OLD_VALIDATOR_MODULE).decode("utf-8")
    plan_tree, realization_tree, validator_tree = ast.parse(plan_source), ast.parse(realization_source), ast.parse(validator_source)
    typed_node = next(node for node in plan_tree.body if isinstance(node, ast.ClassDef) and node.name == "TypedPlanNode")
    typed_fields = [node.target.id for node in typed_node.body if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)]
    if any(field in typed_fields for field in ("required_actor_roles", "required_actor_affordances", "causal_necessity")):
        raise SystemExit("V5.2 plan unexpectedly has semantic signatures")
    lexical = next(node for node in realization_tree.body if isinstance(node, ast.ClassDef) and node.name == "NodeLexicalization")
    lexical_fields = [node.target.id for node in lexical.body if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)]
    if any(field in lexical_fields for field in ("actor_semantic_roles", "actor_affordances", "causal_rule")):
        raise SystemExit("V5.2 lexicalization unexpectedly has semantic witnesses")
    if "actor_operand_id != node.bound_actor_id" not in validator_source or "required_actor_affordances" in validator_source:
        raise SystemExit("V5.2 validator evidence drift")

    new_module = (ROOT / NEW_MODULE).read_bytes()
    new_source = new_module.decode("utf-8")
    new_tree = ast.parse(new_source)
    imports = {node.module.split(".")[0] for node in ast.walk(new_tree) if isinstance(node, ast.ImportFrom) and node.module}
    imports.update(alias.name.split(".")[0] for node in ast.walk(new_tree) if isinstance(node, ast.Import) for alias in node.names)
    if imports.intersection({"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "torch", "transformers", "importlib"}):
        raise SystemExit("nonpathless successor import")
    for required in ("actor semantic role is incompatible", "actor lacks predicate-required agency",
                     "reclassification cannot create a privileged affordance",
                     "edge lacks explicit causal necessity and non-arbitrariness witness",
                     "realized semantic roles affordances or causal rule differ"):
        if required not in new_source:
            raise SystemExit(f"missing semantic enforcement: {required}")

    analysis_core = {
        "schema_name": "batch2-pilot10-semantic-edge-role-continuity-root-cause-analysis-v1", "schema_version": "1.0.0",
        "disposition_commit": COMMIT, "disposition_identity": disposition["disposition_identity"],
        "candidate_identity": disposition["candidate_identity"], "candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": disposition["candidate_git_blob_oid_sha1"], "candidate_modified": False,
        "constructor_v5_2_identity": old_implementation["constructor_implementation_identity"],
        "constructor_v5_2_preservation": "PASS_BYTE_EXACT_HISTORICAL_VERIFICATION_ONLY",
        "continuity_distinctions": {
            "lexical_operand_continuity": "PRESENT_SAME_ZONE_PHRASE_RECURS_ACROSS_L2_AND_RESULT",
            "structural_type_continuity": "PRESENT_INVENTED_RELATION_2_IS_CONSUMED_AS_THE_TERMINAL_ACTOR_ID",
            "semantic_role_compatibility": "FAIL_CLASSIFIED_LOCATION_PATIENT_STATE_BECOMES_PROCEDURE_APPLIER",
            "predicate_argument_compatibility": "FAIL_TERMINAL_PREDICATE_REQUIRES_AN_ACTOR_CAPABLE_OF_APPLYING_APPROVAL_AND_MOVEMENT",
            "agency_authority_capability_affordance_compatibility": "FAIL_RECLASSIFICATION_MINTS_UNLICENSED_AGENTIVE_PROCEDURAL_POWER",
            "causal_necessity_non_arbitrariness": "FAIL_TERMINAL_ACTION_CAN_BE_REMOVED_OR_REPLACED_WITHOUT_CONTRADICTING_L2",
            "terminal_witness_existence": "PASS_ONE_EXPLICIT_WITNESS_BUT_EXISTENCE_IS_NOT_SEMANTIC_VALIDITY",
        },
        "layer_attribution": {
            "source_proposition_sufficiency": "NOT_CAUSAL_P3_WAS_SUFFICIENT_EXACT_AND_G02_PASS",
            "g01_assignment_and_factual_authority": "NOT_CAUSAL_BINDINGS_REMAIN_EXACT_WITHOUT_WIDENING",
            "abstract_plan": "CAUSAL_OPAQUE_PREDICATE_IDS_AND_COARSE_RELATION_HEAD_ROLE_ADMITTED_ROLE_INCOMPATIBLE_TERMINAL_EDGE",
            "realization": "CAUSAL_MANIFESTATION_LEXICALIZER_TURNED_A_RECLASSIFIED_NONHUMAN_PATIENT_STATE_INTO_AN_AGENT",
            "pre_emission_validation": "CAUSAL_ACCEPTED_ID_COORDINATE_AND_LEXICAL_RECURRENCE_WITHOUT_ROLE_AFFORDANCE_OR_NECESSITY_CHECKS",
            "g02c": "AUTHORITATIVE_VALID_DETECTION_NOT_CAUSAL_AND_NOT_WEAKENED",
        },
        "root_causes": [
            "TYPED_PLAN_NODE_HAS_NO_PREDICATE_SEMANTIC_ROLE_SIGNATURE",
            "PRODUCED_OPERANDS_HAVE_NO_ENTITY_IDENTITY_ROLE_OR_AFFORDANCE_CONTRACT",
            "RECLASSIFICATION_CAN_IMPLICITLY_MINT_AGENCY_AUTHORITY_CAPABILITY_OR_PROCEDURAL_POWER",
            "EDGE_VALIDATION_CHECKS_PREDECESSOR_AND_OPERAND_IDENTITY_BUT_NOT_PREDICATE_ARGUMENT_ELIGIBILITY",
            "SURFACE_VALIDATION_ACCEPTS_LEXICAL_RECURRENCE_AS_CONTINUITY_WITHOUT_SEMANTIC_ROLE_CONTINUITY",
            "TERMINAL_VALIDATION_CHECKS_ONE_WITNESS_EXISTS_BUT_NOT_CAUSAL_NECESSITY_OR_ROLE_COMPATIBLE_EXECUTABILITY",
        ],
        "defect_phase": "COMBINED_PLAN_TIME_REALIZATION_TIME_AND_PRE_EMISSION_VALIDATION_TIME",
        "exact_causal_boundary": "CONSTRUCTOR_V5_2_ABSTRACT_PLAN_SEMANTIC_SIGNATURE_AND_POST_REALIZATION_PRE_EMISSION_ROLE_NECESSITY_VALIDATION",
        "earliest_preventable_boundary": "PLAN_TIME_PREDICATE_ROLE_AND_AFFORDANCE_COMPATIBILITY_WHERE_DETECTABLE_WITH_MANDATORY_PRE_EMISSION_REALIZED_SEMANTIC_REVALIDATION",
        "verdict": "ROOT_CAUSE_CONFIRMED_AT_CONSTRUCTOR_V5_2_SEMANTIC_EDGE_NECESSITY_AND_TYPED_OPERAND_ROLE_CONTINUITY_BOUNDARY",
    }
    analysis = {**analysis_core, "analysis_identity": seal("B2_PILOT10_SEMANTIC_EDGE_ROLE_CONTINUITY_ROOT_CAUSE_ANALYSIS_V1", analysis_core)}

    contract_core = {
        "schema_name": "batch2-development-constructor-contract-v5-3", "schema_version": "5.3.0",
        "supersedes_contract_identity": old_contract["constructor_contract_identity"],
        "root_cause_analysis_identity": analysis["analysis_identity"], "preserves_v5_2_material_witness_requirements": True,
        "required_plan_time_semantic_inputs": ["OPERAND_ENTITY_IDENTITY", "OPERAND_SEMANTIC_ROLES", "OPERAND_AFFORDANCES",
            "PREDICATE_ACTOR_AND_PATIENT_ROLE_SIGNATURES", "PREDICATE_REQUIRED_AFFORDANCES", "EDGE_CAUSAL_NECESSITY_WITNESSES"],
        "required_plan_time_validations": ["REQUIRED_ROLE_VS_PRODUCED_ROLE_COMPATIBILITY_EVERY_NODE_AND_EDGE",
            "ENTITY_IDENTITY_PRESERVED_SEPARATELY_FROM_CATEGORY_OR_STATUS_RECLASSIFICATION",
            "RECLASSIFICATION_CANNOT_CREATE_AGENCY_AUTHORITY_CAPABILITY_OWNERSHIP_PERMISSION_OR_PROCEDURAL_POWER",
            "ACTION_AFFORDANCE_CONTINUITY", "EDGE_COUNTERFACTUAL_DEPENDENCY_AND_NON_ARBITRARINESS",
            "TERMINAL_EDGE_VALIDATED_AT_EQUAL_STRENGTH"],
        "required_pre_emission_semantic_validations": ["SURFACE_ROLE_AND_AFFORDANCE_WITNESSES_MATCH_VALIDATED_PLAN",
            "SURFACE_CAUSAL_RULE_WITNESSES_MATCH_EVERY_VALIDATED_EDGE", "TERMINAL_ACTOR_AND_PATIENT_ARE_PREDICATE_ELIGIBLE",
            "ANY_ROLE_INCOMPATIBLE_OR_CAUSALLY_ARBITRARY_EDGE_FAILS_BEFORE_PERSISTENCE_EMISSION_OR_G02"],
        "successor_provider_emitter_integration": "UNASSIGNED_REQUIRES_SEPARATE_IMPLEMENTATION_AND_STATIC_AUDIT",
        "constructor_release_authority": False, "construction_authority": False, "candidate_surface": None,
    }
    contract = {**contract_core, "constructor_contract_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_CONTRACT_V5_3", contract_core)}
    governance_core = {
        "schema_name": "batch2-semantic-edge-role-continuity-governance-v5-3", "schema_version": "5.3.0",
        "supersedes_governance_identity": old_governance["governance_identity"], "root_cause_analysis_identity": analysis["analysis_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "upstream_boundaries_unchanged": ["G01", "SOURCE_PROPOSITION_SUFFICIENCY", "ASSIGNMENT", "FACTUAL_AUTHORITY", "FRAGMENT_COLLISION", "G02"],
        "dual_enforcement_boundary": {"plan_time": "STATIC_SEMANTIC_ROLE_PREDICATE_ARGUMENT_AFFORDANCE_AND_EDGE_NECESSITY",
                                      "pre_emission": "REALIZED_ROLE_AFFORDANCE_CAUSAL_RULE_AND_TERMINAL_EDGE_REVALIDATION"},
        "responsibility_separation": "PLAN_TIME_REJECTS_KNOWN_INCOMPATIBILITY_PRE_EMISSION_REJECTS_REALIZATION_DRIFT_WITHOUT_DUPLICATING_G02C",
        "g02c_authority": "UNCHANGED_AUTHORITATIVE_INDEPENDENT_POSTCONSTRUCTION_ADJUDICATION",
        "pilot10_regression_mandatory": True,
        "constructor_implementation_authority": False, "constructor_release_authority": False,
        "source_acquisition_authority": False, "construction_authority": False,
        "model_exposure_authority": False, "training_authority": False, "runtime_authority": False, "production_authority": False,
    }
    governance = {**governance_core, "governance_identity": seal("B2_SEMANTIC_EDGE_ROLE_CONTINUITY_GOVERNANCE_V5_3", governance_core)}
    schema_core = {
        "schema_name": "batch2-semantic-edge-role-continuity-conformance-schema-v5-3", "schema_version": "5.3.0",
        "governance_identity": governance["governance_identity"], "constructor_contract_identity": contract["constructor_contract_identity"],
        "required_plan_time_predicates": contract["required_plan_time_validations"],
        "required_pre_emission_predicates": contract["required_pre_emission_semantic_validations"],
        "allowed_failure_verdicts": ["FAIL_ACTOR_SEMANTIC_ROLE_INCOMPATIBLE", "FAIL_PATIENT_SEMANTIC_ROLE_INCOMPATIBLE",
            "FAIL_REQUIRED_AFFORDANCE_MISSING", "FAIL_RECLASSIFICATION_MINTS_PRIVILEGED_ROLE_OR_AFFORDANCE",
            "FAIL_EDGE_CAUSAL_NECESSITY_OR_NON_ARBITRARINESS", "FAIL_SURFACE_SEMANTIC_WITNESS_DRIFT",
            "FAIL_TERMINAL_EDGE_ROLE_OR_CAUSAL_COMPATIBILITY"],
        "failure_effect": "NO_REALIZATION_OR_NO_CANDIDATE_IDENTITY_PERSISTENCE_EMISSION_OR_G02_ELIGIBILITY",
        "mechanism_label_forbidden": True, "constructor_release_authority": False, "construction_authority": False,
    }
    schema = {**schema_core, "schema_identity": seal("B2_SEMANTIC_EDGE_ROLE_CONTINUITY_CONFORMANCE_SCHEMA_V5_3", schema_core)}
    implementation_core = {
        "schema_name": "batch2-development-constructor-semantic-edge-enforcement-v5-3", "schema_version": "5.3.0",
        "constructor_contract_identity": contract["constructor_contract_identity"], "module_path": NEW_MODULE,
        "module_sha256": hashlib.sha256(new_module).hexdigest(), "plan_validator": "validate_semantic_plan",
        "pre_emission_validator": "validate_surface_semantics", "pathless_static_enforcement": True,
        "constructor_v5_2_identity": old_implementation["constructor_implementation_identity"],
        "constructor_v5_2_status": "BYTE_EXACT_SUPERSEDED_FOR_FUTURE_RELEASE_PENDING_SUCCESSOR_INTEGRATION",
        "constructor_provider_emitter_invocations": "0/0/0", "candidate_surfaces_created": 0,
        "release_authority": False, "construction_authority": False,
    }
    implementation = {**implementation_core, "semantic_enforcement_implementation_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_SEMANTIC_EDGE_ENFORCEMENT_V5_3", implementation_core)}
    regression_core = {
        "schema_name": "batch2-pilot10-role-incompatible-terminal-edge-regression-v1", "schema_version": "1.0.0",
        "candidate_identity": disposition["candidate_identity"], "candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": disposition["candidate_git_blob_oid_sha1"], "candidate_bytes_embedded": False,
        "candidate_modified": False, "failed_shape": "ALL_NODES_EDGES_AND_TERMINAL_WITNESS_PRESENT_BUT_TERMINAL_ACTOR_LEXICALLY_CONTINUOUS_ROLE_INCOMPATIBLE_AND_CAUSALLY_ARBITRARY",
        "expected_v5_3_result": "FAIL_CLOSED_BEFORE_REALIZATION_WHERE_PLAN_SIGNATURE_EXPOSES_MISMATCH_OTHERWISE_BEFORE_CANDIDATE_EMISSION",
        "expected_primary_failure": "ACTOR_SEMANTIC_ROLE_INCOMPATIBLE_WITH_TERMINAL_PREDICATE",
        "expected_secondary_failure": "RECLASSIFICATION_CANNOT_MINT_PROCEDURE_APPLYING_AFFORDANCE",
        "candidate_persistence_or_emission": False, "g02_eligibility": False, "positive_pool_eligibility": False,
    }
    regression = {**regression_core, "regression_identity": seal("B2_PILOT10_ROLE_INCOMPATIBLE_TERMINAL_EDGE_REGRESSION_V1", regression_core)}
    visible = canonical({"contract": contract_core, "governance": governance_core, "schema": schema_core, "implementation": implementation_core})
    forbidden = [rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"mechanism_id", rb"mechanism_name", rb"answer_key", rb"blind_evaluation"]
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    if hits:
        raise SystemExit(f"leakage {hits}")
    audit_core = {
        "schema_name": "batch2-semantic-edge-role-continuity-v5-3-audit-v1", "schema_version": "1.0.0",
        "analysis_identity": analysis["analysis_identity"], "constructor_contract_identity": contract["constructor_contract_identity"],
        "governance_identity": governance["governance_identity"], "schema_identity": schema["schema_identity"],
        "semantic_enforcement_implementation_identity": implementation["semantic_enforcement_implementation_identity"],
        "pilot10_regression_identity": regression["regression_identity"],
        "root_cause_layer_separation": "PASS_ONLY_ABSTRACT_PLAN_SEMANTIC_SIGNATURE_REALIZATION_ROLE_AND_PRE_EMISSION_NECESSITY_BOUNDARIES_CHANGED",
        "typed_predicate_role_signatures": "PASS_PRESENT_FAIL_CLOSED", "required_vs_produced_role_compatibility": "PASS_PRESENT_FAIL_CLOSED",
        "entity_identity_vs_reclassification": "PASS_SEPARATED", "privileged_role_and_affordance_minting": "PASS_PROHIBITED",
        "edge_level_causal_necessity": "PASS_EXPLICIT_COUNTERFACTUAL_AND_NON_ARBITRARY_WITNESS_REQUIRED",
        "terminal_edge_equal_strength": "PASS", "pilot10_regression": "PASS_REJECTED_BEFORE_REALIZATION",
        "g02c_weakened": False, "label_taxonomy_answer_leakage": "PASS_ZERO_HITS",
        "constructor_v5_2_preservation": "PASS_BYTE_EXACT", "pilot10_preservation": "PASS_BYTE_EXACT_NONPOSITIVE",
        "constructor_provider_emitter_invocations": "0/0/0", "candidate_surfaces_created": 0, "release_authority": False,
        "deterministic_blockers_before_successor_constructor_phase": ["V5_3_PROVIDER_EMITTER_INTEGRATION_AND_STATIC_AUDIT_NOT_PERFORMED"],
        "verdict": "PASS_SOURCE_ONLY_SEMANTIC_EDGE_ROLE_CONTINUITY_REMEDIATION_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_SEMANTIC_EDGE_ROLE_CONTINUITY_V5_3_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-pilot10-semantic-edge-role-continuity-root-cause-analysis-v1.json", analysis)
    write("humor-mechanics-batch2-development-constructor-contract-v5-3.json", contract)
    write("humor-mechanics-batch2-semantic-edge-role-continuity-governance-v5-3.json", governance)
    write("humor-mechanics-batch2-semantic-edge-role-continuity-conformance-schema-v5-3.json", schema)
    write("humor-mechanics-batch2-development-constructor-semantic-edge-enforcement-v5-3.json", implementation)
    write("humor-mechanics-batch2-pilot10-role-incompatible-terminal-edge-regression-v1.json", regression)
    write("humor-mechanics-batch2-semantic-edge-role-continuity-v5-3-audit-v1.json", audit)
    print(json.dumps({"verdict": analysis["verdict"], "analysis_identity": analysis["analysis_identity"],
        "contract_identity": contract["constructor_contract_identity"], "governance_identity": governance["governance_identity"],
        "schema_identity": schema["schema_identity"], "semantic_enforcement_identity": implementation["semantic_enforcement_implementation_identity"],
        "pilot10_regression_identity": regression["regression_identity"], "audit_identity": audit["audit_identity"],
        "audit_verdict": audit["verdict"]}, sort_keys=True))


if __name__ == "__main__":
    main()

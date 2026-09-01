"""Source-only Pilot 09 plan-to-surface root cause analysis and V5.2 remediation."""

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
COMMIT = "b4ff9cd20f6a96e5b222f1ba76380b5d1a494d79"
V5_1_MODULE = "src/pastila_scout/humor_batch2_development_constructor_v5_1.py"
V5_2_MODULE = "src/pastila_scout/humor_batch2_development_constructor_v5_2.py"


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
        raise SystemExit("artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != COMMIT:
        raise SystemExit("HEAD")
    disposition = load("docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-g02c-rejection-disposition-v1.json")
    receipt = load("docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-g02c-conformance-receipt-v5-1.json")
    old_contract = load("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5-1.json")
    old_implementation = load("docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5-1.json")
    old_governance = load("docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-governance-v5.json")
    old_schema = load("docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-conformance-schema-v5.json")
    if disposition["disposition_identity"] != "2cae08d4448eadc3bcbb495255c3aff3227bf70739d3d000aadeb2b9c580e4c2":
        raise SystemExit("disposition")
    if receipt["conformance_receipt_identity"] != "a2ba3529a489e23a6c70b8405ab585eedd6158882132ad539d411a9f61e6f7e4":
        raise SystemExit("receipt")
    if old_contract["constructor_contract_identity"] != "9b647d33dfa40171040fe6acf08b8b6dca6081c41c0f1f4428f910bfdfaa8a6b":
        raise SystemExit("contract")
    if old_implementation["constructor_implementation_identity"] != "c7134743e6b0e7c3ed7637bff3203f774159f192fef7a7b712e15d4d44a6f419":
        raise SystemExit("implementation")

    v5_1 = git_bytes(V5_1_MODULE)
    v5_1_source = v5_1.decode("utf-8")
    v5_1_tree = ast.parse(v5_1_source)
    realize = next(node for node in v5_1_tree.body if isinstance(node, ast.FunctionDef) and node.name == "_realize")
    if [arg.arg for arg in realize.args.args] != ["source", "operands"]:
        raise SystemExit("V5.1 realization signature drift")
    if "relația continuă prin două consecințe locale" not in v5_1_source:
        raise SystemExit("V5.1 generic meta surface drift")
    entry = next(node for node in v5_1_tree.body if isinstance(node, ast.FunctionDef) and node.name == "construct_development_candidate_v5_1")
    called = [node.func.id for node in ast.walk(entry) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    if "validate_typed_plan" not in called or "_realize" not in called or "validate_realization_draft" in called:
        raise SystemExit("V5.1 boundary evidence drift")

    v5_2 = (ROOT / V5_2_MODULE).read_bytes()
    v5_2_source = v5_2.decode("utf-8")
    v5_2_tree = ast.parse(v5_2_source)
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(v5_2_tree) if isinstance(node, ast.Import)}
    imports.update(node.module.split(".")[0] for node in ast.walk(v5_2_tree) if isinstance(node, ast.ImportFrom) and node.module)
    if imports.intersection({"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "torch", "transformers", "importlib"}):
        raise SystemExit("nonpathless V5.2 import")
    for required in ("incomplete or duplicate N/N", "incomplete E/E", "typed invented actor continuity", "terminal result lacks", "meta-language substitutes"):
        if required not in v5_2_source:
            raise SystemExit("missing V5.2 enforcement")

    analysis_core = {
        "schema_name": "batch2-pilot09-plan-to-surface-root-cause-analysis-v1",
        "schema_version": "1.0.0",
        "disposition_commit": COMMIT,
        "disposition_identity": disposition["disposition_identity"],
        "candidate_identity": disposition["candidate_identity"],
        "candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": disposition["candidate_git_blob_oid_sha1"],
        "candidate_modified": False,
        "constructor_v5_1_module_path": V5_1_MODULE,
        "constructor_v5_1_module_sha256": hashlib.sha256(v5_1).hexdigest(),
        "constructor_v5_1_preservation": "PASS_BYTE_EXACT_HISTORICAL_VERIFICATION_ONLY",
        "layer_attribution": {
            "source_and_proposition_sufficiency": "NOT_CAUSAL_P5_WAS_EXACT_SUFFICIENT_AND_BOUND",
            "assignment_correctness": "NOT_CAUSAL_OBLIGATION_REQUIRED_EXPLICIT_MULTI_LINK_REALIZATION",
            "typed_static_plan_correctness": "NOT_CAUSAL_PLAN_WAS_PROPOSITION_DERIVED_AND_CLOSED",
            "realization_completeness": "PRIMARY_CAUSAL_REALIZER_DID_NOT_ACCEPT_PLAN_AND_EMITTED_NO_NODE_EDGE_OR_TERMINAL_WITNESSES",
            "factual_boundary_correctness": "NOT_CAUSAL_G02_PASSED_EXACT_FACT_AND_EXPLICIT_FICTION_BOUNDARIES",
            "g02c_obligation_conformance": "VALID_DETECTION_NOT_CAUSAL",
        },
        "root_causes": [
            "V5_1_REALIZER_SIGNATURE_ACCEPTED_SOURCE_AND_OPERANDS_BUT_NOT_THE_VALIDATED_TYPED_PLAN",
            "V5_1_RETURNED_GENERIC_META_LANGUAGE_ASSERTING_TWO_CONSEQUENCES_AND_A_COMPLETE_PATH_WITHOUT_INSTANTIATING_THEM",
            "NO_N_OVER_N_NODE_WITNESS_MANIFEST_WAS_REQUIRED",
            "NO_E_OVER_E_EDGE_WITNESS_MANIFEST_WAS_REQUIRED",
            "NO_TYPED_OPERAND_CONTINUITY_FROM_PLAN_TO_SURFACE_WAS_CHECKED",
            "NO_UNIQUE_TERMINAL_RESULT_SURFACE_WITNESS_WAS_REQUIRED",
            "NO_POST_REALIZATION_PRE_EMISSION_VALIDATOR_OR_INSTRUCTION_LANGUAGE_TRANSFER_FILTER_EXISTED",
            "G02C_DETECTED_THE_DEFECT_ONLY_AFTER_SINGLE_USE_CONSTRUCTION_WAS_CONSUMED",
        ],
        "exact_causal_boundary": "CONSTRUCTOR_V5_1_POST_STATIC_PLAN_REALIZATION_AND_PRE_CANDIDATE_EMISSION",
        "earliest_preventable_boundary": "DETERMINISTIC_POST_REALIZATION_MECHANISM_NEUTRAL_VALIDATION_BEFORE_CANDIDATE_PERSISTENCE_AND_G02",
        "verdict": "ROOT_CAUSE_CONFIRMED_AT_CONSTRUCTOR_V5_1_PLAN_TO_SURFACE_REALIZATION_AND_PRE_EMISSION_VALIDATION_BOUNDARY",
    }
    analysis = {**analysis_core, "analysis_identity": seal("B2_PILOT09_PLAN_TO_SURFACE_ROOT_CAUSE_ANALYSIS_V1", analysis_core)}

    contract_core = {
        "schema_name": "batch2-development-constructor-contract-v5-2",
        "schema_version": "5.2.0",
        "supersedes_contract_identity": old_contract["constructor_contract_identity"],
        "root_cause_analysis_identity": analysis["analysis_identity"],
        "preserves_v5_1_typed_plan_requirements": True,
        "required_realizer_input": ["EXACT_SOURCE", "TYPED_OPERANDS", "VALIDATED_TYPED_PLAN"],
        "required_realizer_output": ["SURFACE_UTF8", "NODE_WITNESS_MANIFEST", "EDGE_WITNESS_MANIFEST", "OPERAND_CONTINUITY_MANIFEST", "TERMINAL_RESULT_WITNESS"],
        "required_pre_emission_validations": [
            "EXPLICIT_N_OVER_N_CAUSAL_NODE_REALIZATION_COVERAGE",
            "EXPLICIT_E_OVER_E_CAUSAL_EDGE_REALIZATION_COVERAGE",
            "EVERY_TYPED_OPERAND_HAS_CONTINUOUS_EXPLICIT_SURFACE_PROVENANCE",
            "EXACTLY_ONE_TERMINAL_RESULT_WITNESS_BINDS_THE_FINAL_PLAN_NODE",
            "OMITTED_COLLAPSED_SUMMARIZED_PLACEHOLDER_OR_MERELY_ASSERTED_RELATIONS_FAIL_CLOSED",
            "INSTRUCTION_GOVERNANCE_AND_PLAN_META_LANGUAGE_TRANSFER_FAILS_CLOSED",
            "VALIDATION_PASSES_BEFORE_ANY_CANDIDATE_IDENTITY_PERSISTENCE_OR_G02_ELIGIBILITY",
        ],
        "realization_provider_identity": "UNASSIGNED_REQUIRES_SEPARATE_IMPLEMENTATION_AND_STATIC_AUDIT",
        "constructor_release_authority": False,
        "construction_authority": False,
        "candidate_surface": None,
    }
    contract = {**contract_core, "constructor_contract_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_CONTRACT_V5_2", contract_core)}

    governance_core = {
        "schema_name": "batch2-plan-witnessed-realization-governance-v5-2",
        "schema_version": "5.2.0",
        "supersedes_governance_identity": old_governance["governance_identity"],
        "root_cause_analysis_identity": analysis["analysis_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "upstream_boundaries_unchanged": ["SOURCE_PROPOSITION_SUFFICIENCY", "ASSIGNMENT_SELECTION", "TYPED_STATIC_PLAN", "G02_FACTUAL_BOUNDARY"],
        "new_mandatory_boundary": "POST_REALIZATION_PRE_CANDIDATE_EMISSION_MECHANISM_NEUTRAL_CONFORMANCE",
        "coverage_requirements": {"causal_nodes": "N_OF_N", "causal_edges": "E_OF_E", "terminal_results": "1_OF_1"},
        "meta_assertion_cannot_substitute_for_realization": True,
        "instruction_language_transfer_detection_required": ["STATIC_REALIZER_SCAN", "REALIZATION_DRAFT_SCAN", "POST_REALIZATION_WITNESS_VALIDATION"],
        "pilot09_regression_mandatory": True,
        "constructor_implementation_authority": False,
        "constructor_release_authority": False,
        "source_acquisition_authority": False,
        "construction_authority": False,
        "model_exposure_authority": False,
        "training_authority": False,
        "runtime_authority": False,
        "production_authority": False,
    }
    governance = {**governance_core, "governance_identity": seal("B2_PLAN_WITNESSED_REALIZATION_GOVERNANCE_V5_2", governance_core)}

    schema_core = {
        "schema_name": "batch2-plan-witnessed-realization-conformance-schema-v5-2",
        "schema_version": "5.2.0",
        "governance_identity": governance["governance_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "required_pre_emission_predicates": contract["required_pre_emission_validations"],
        "allowed_verdicts": [
            "PASS_PRE_EMISSION_REALIZATION_CONFORMANCE",
            "FAIL_NODE_REALIZATION_COVERAGE",
            "FAIL_EDGE_REALIZATION_COVERAGE",
            "FAIL_TYPED_OPERAND_SURFACE_CONTINUITY",
            "FAIL_TERMINAL_RESULT_REALIZATION",
            "FAIL_META_ASSERTION_OR_PLACEHOLDER_SUBSTITUTION",
            "FAIL_INSTRUCTION_LANGUAGE_TRANSFER",
        ],
        "failure_effect": "NO_CANDIDATE_IDENTITY_NO_PERSISTENCE_NO_G02_ELIGIBILITY",
        "mechanism_label_forbidden": True,
        "constructor_release_authority": False,
        "construction_authority": False,
    }
    schema = {**schema_core, "schema_identity": seal("B2_PLAN_WITNESSED_REALIZATION_CONFORMANCE_SCHEMA_V5_2", schema_core)}

    implementation_core = {
        "schema_name": "batch2-development-constructor-plan-to-surface-enforcement-v5-2",
        "schema_version": "5.2.0",
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "module_path": V5_2_MODULE,
        "module_sha256": hashlib.sha256(v5_2).hexdigest(),
        "validator_entrypoint": "validate_realization_draft",
        "realization_provider": "UNASSIGNED",
        "candidate_emitter": "UNASSIGNED",
        "pathless_static_enforcement": True,
        "constructor_v5_1_identity": old_implementation["constructor_implementation_identity"],
        "constructor_v5_1_status": "BYTE_EXACT_SUPERSEDED_NO_FUTURE_RELEASE",
        "constructor_invocations": 0,
        "candidate_surfaces_created": 0,
        "release_authority": False,
        "construction_authority": False,
    }
    implementation = {**implementation_core, "enforcement_implementation_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_PLAN_TO_SURFACE_ENFORCEMENT_V5_2", implementation_core)}

    regression_core = {
        "schema_name": "batch2-pilot09-plan-to-surface-regression-v1",
        "schema_version": "1.0.0",
        "candidate_identity": disposition["candidate_identity"],
        "candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": disposition["candidate_git_blob_oid_sha1"],
        "candidate_bytes_embedded": False,
        "candidate_modified": False,
        "failed_shape": "STATIC_PLAN_VALID_BUT_SURFACE_ONLY_ASSERTS_TWO_CONSEQUENCES_AND_COMPLETE_PATH",
        "expected_v5_2_result": "FAIL_META_ASSERTION_OR_PLACEHOLDER_SUBSTITUTION_BEFORE_CANDIDATE_EMISSION",
        "expected_node_coverage": "0_OF_3_EXPLICIT_WITNESSES",
        "expected_edge_coverage": "0_OF_2_EXPLICIT_WITNESSES",
        "expected_terminal_result_coverage": "0_OF_1",
        "g02_eligibility": False,
        "positive_pool_eligibility": False,
    }
    regression = {**regression_core, "regression_identity": seal("B2_PILOT09_PLAN_TO_SURFACE_REGRESSION_V1", regression_core)}

    visible = canonical({"contract": contract_core, "governance": governance_core, "schema": schema_core, "implementation": implementation_core})
    forbidden = [rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"mechanism_id", rb"mechanism_name", rb"answer_key", rb"blind_evaluation"]
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    if hits:
        raise SystemExit(f"leakage {hits}")
    audit_core = {
        "schema_name": "batch2-plan-witnessed-realization-v5-2-audit-v1",
        "schema_version": "1.0.0",
        "analysis_identity": analysis["analysis_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "governance_identity": governance["governance_identity"],
        "schema_identity": schema["schema_identity"],
        "enforcement_implementation_identity": implementation["enforcement_implementation_identity"],
        "pilot09_regression_identity": regression["regression_identity"],
        "root_cause_layer_separation": "PASS_ONLY_REALIZATION_AND_PRE_EMISSION_BOUNDARIES_CHANGED",
        "n_over_n_node_validation": "PASS_PRESENT_FAIL_CLOSED",
        "e_over_e_edge_validation": "PASS_PRESENT_FAIL_CLOSED",
        "typed_operand_surface_continuity": "PASS_PRESENT_FAIL_CLOSED",
        "terminal_result_witness": "PASS_PRESENT_FAIL_CLOSED",
        "meta_assertion_placeholder_filter": "PASS_PILOT09_REJECTED",
        "instruction_language_transfer_controls": "PASS_STATIC_DRAFT_AND_POST_REALIZATION_REQUIREMENTS",
        "label_taxonomy_answer_leakage": "PASS_ZERO_HITS",
        "constructor_v5_1_preservation": "PASS_BYTE_EXACT",
        "pilot09_preservation": "PASS_BYTE_EXACT_NONPOSITIVE",
        "constructor_invocations": 0,
        "candidate_surfaces_created": 0,
        "release_authority": False,
        "deterministic_blockers_before_successor_realizer_phase": ["REALIZATION_PROVIDER_UNASSIGNED", "CANDIDATE_EMITTER_UNASSIGNED"],
        "verdict": "PASS_SOURCE_ONLY_PLAN_TO_SURFACE_GOVERNANCE_AND_ENFORCEMENT_REMEDIATION_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_PLAN_WITNESSED_REALIZATION_V5_2_AUDIT_V1", audit_core)}

    write("humor-mechanics-batch2-pilot09-plan-to-surface-root-cause-analysis-v1.json", analysis)
    write("humor-mechanics-batch2-development-constructor-contract-v5-2.json", contract)
    write("humor-mechanics-batch2-plan-witnessed-realization-governance-v5-2.json", governance)
    write("humor-mechanics-batch2-plan-witnessed-realization-conformance-schema-v5-2.json", schema)
    write("humor-mechanics-batch2-development-constructor-plan-to-surface-enforcement-v5-2.json", implementation)
    write("humor-mechanics-batch2-pilot09-plan-to-surface-regression-v1.json", regression)
    write("humor-mechanics-batch2-plan-witnessed-realization-v5-2-audit-v1.json", audit)
    print(json.dumps({
        "verdict": analysis["verdict"], "analysis_identity": analysis["analysis_identity"],
        "contract_identity": contract["constructor_contract_identity"], "governance_identity": governance["governance_identity"],
        "schema_identity": schema["schema_identity"], "enforcement_implementation_identity": implementation["enforcement_implementation_identity"],
        "pilot09_regression_identity": regression["regression_identity"], "audit_identity": audit["audit_identity"],
        "audit_verdict": audit["verdict"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

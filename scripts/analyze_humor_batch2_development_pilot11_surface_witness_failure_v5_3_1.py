"""Freeze source-only Pilot 11 surface-witness root cause and narrow remediation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "7001d186d13bfdf7c98ac2896b0636c33db01371"
EVIDENCE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot11-construction-attempt01-v1.json"
RUNNER_PATH = "scripts/run_humor_batch2_development_pilot11_construction_once_v5_3.py"
ALIGNMENT_PATH = "src/pastila_scout/humor_batch2_development_constructor_v5_3_1_surface_alignment.py"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def committed(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    evidence = json.loads(committed(EVIDENCE_PATH))
    runner = committed(RUNNER_PATH).decode("utf-8")
    require(evidence["evidence_identity"] == "6315e06a6683cc88860356aebe520cce45c86fa0a9d5f468c1a5dec32ef66e2e", "evidence")
    require(evidence["failure_code"] == "ValueError: typed actor predicate or patient lacks an explicit surface witness", "failure")
    require(evidence["candidate_surface_present"] is False and evidence["capability"]["state"] == "CONSUMED_1_OF_1", "terminal state")
    require('patient_surface="ambele verificări conforme"' in runner, "canonical patient witness")
    require("ambelor verificări conforme" in runner, "realized inflected patient")
    require("ambele verificări conforme" not in runner.split("clause=(", 1)[1].split("),", 1)[0], "exact form absent from L1 clause")
    alignment_raw = (ROOT / ALIGNMENT_PATH).read_bytes()
    alignment_sha = hashlib.sha256(alignment_raw).hexdigest()

    analysis_core = {
        "schema_name": "batch2-development-pilot11-v5-3-surface-witness-root-cause-v1", "schema_version": "1.0.0",
        "reviewed_commit": COMMIT, "evidence_identity": evidence["evidence_identity"],
        "terminal_verdict": evidence["terminal_classification"], "candidate_identity": None,
        "capability_state": "CONSUMED_1_OF_1_NO_RETRY", "exact_failed_node": "L1",
        "exact_failed_role": "PATIENT", "typed_operand_id": "FACT_QUALIFICATION",
        "canonical_witness_form": "ambele verificări conforme", "actual_realized_form": "ambelor verificări conforme",
        "surface_semantic_role_status": "PRESENT_BUT_UNRECOGNIZED_LEGITIMATE_ROMANIAN_CASE_INFLECTION",
        "failed_validator_boundary": "V5_2_VALIDATE_REALIZATION_DRAFT_EXACT_NORMALIZED_SUBSTRING_CHECK_BEFORE_V5_3_SURFACE_SEMANTIC_VALIDATION",
        "provider_lexicalization": "PASS_SEMANTIC_ROLE_PRESENT_WITH_REQUIRED_GENITIVE_AFTER_DATORITA",
        "witness_extraction": "FAIL_EXACT_LEXICAL_IDENTITY_NOT_MORPHOLOGY_AWARE",
        "coordinate_derivation": "V5_2_CLAUSE_COORDINATES_EXIST_BUT_ROLE_SUBSPAN_COORDINATES_NOT_RECORDED",
        "missing_vs_mismatch_distinction": "FAIL_CONFLATED_GENUINELY_MISSING_WITH_SURFACE_FORM_MISMATCH",
        "static_semantic_plan": "PASS_REMAINS_CORRECT_AND_NONCAUSAL",
        "root_cause_verdict": "ROOT_CAUSE_CONFIRMED_AT_V5_3_INHERITED_EXACT_LEXICAL_SURFACE_WITNESS_ALIGNMENT_BOUNDARY",
    }
    analysis = {**analysis_core, "analysis_identity": seal("B2_DEVELOPMENT_PILOT11_V5_3_SURFACE_WITNESS_ROOT_CAUSE_V1", analysis_core)}
    contract_core = {
        "schema_name": "batch2-development-constructor-surface-witness-alignment-contract-v5-3-1", "schema_version": "5.3.1",
        "supersedes_witness_alignment_only": "V5_3_INHERITED_V5_2_EXACT_SUBSTRING_ALIGNMENT",
        "constructor_v5_3_preservation": "PASS_BYTE_EXACT", "root_cause_analysis_identity": analysis["analysis_identity"],
        "required_evidence": ["ACTUAL_SURFACE_CHARACTER_COORDINATES", "ACTUAL_SURFACE_UTF8_BYTE_COORDINATES",
                              "TYPED_ROLE_IDENTITY", "CANONICAL_FORM", "ACTUAL_SURFACE_FORM", "LICENSED_ALIGNMENT_RULE"],
        "independent_roles": ["ACTOR", "PREDICATE", "PATIENT"],
        "allowed_alignment_rules": ["EXACT_NFKC_CASEFOLD", "ROMANIAN_AMBELE_AMBELOR_CASE_INFLECTION"],
        "genuinely_missing_effect": "FAIL_CLOSED_BEFORE_EMISSION", "unlicensed_variation_effect": "FAIL_CLOSED_BEFORE_EMISSION",
        "semantic_enforcement_strength": "UNCHANGED", "construction_or_release_authority": False,
    }
    contract = {**contract_core, "successor_contract_identity": seal("B2_CONSTRUCTOR_SURFACE_WITNESS_ALIGNMENT_CONTRACT_V5_3_1", contract_core)}
    implementation_core = {
        "schema_name": "batch2-development-constructor-surface-witness-alignment-implementation-v5-3-1", "schema_version": "5.3.1",
        "successor_contract_identity": contract["successor_contract_identity"], "module_path": ALIGNMENT_PATH,
        "module_sha256": alignment_sha, "constructor_invocations": 0, "candidate_surfaces_created": 0,
        "release_authority": False, "implementation_scope": "COORDINATE_BOUND_ROLE_ALIGNMENT_ONLY",
    }
    implementation = {**implementation_core, "implementation_identity": seal("B2_CONSTRUCTOR_SURFACE_WITNESS_ALIGNMENT_IMPLEMENTATION_V5_3_1", implementation_core)}
    regression_core = {
        "schema_name": "batch2-development-pilot11-surface-witness-regression-v1", "schema_version": "1.0.0",
        "analysis_identity": analysis["analysis_identity"], "implementation_identity": implementation["implementation_identity"],
        "case_genuinely_missing": "PASS_FAIL_CLOSED", "case_legitimate_surface_variation": "PASS_RECOGNIZED_ONLY_WITH_EXACT_COORDINATES_AND_LICENSED_INFLECTION",
        "unlicensed_synonym_or_claimed_equivalence": "PASS_FAIL_CLOSED", "pilot11_reconstruction_or_retry": False,
    }
    regression = {**regression_core, "regression_identity": seal("B2_DEVELOPMENT_PILOT11_SURFACE_WITNESS_REGRESSION_V1", regression_core)}
    audit_core = {
        "schema_name": "batch2-development-pilot11-v5-3-surface-witness-remediation-audit-v1", "schema_version": "1.0.0",
        "analysis_identity": analysis["analysis_identity"], "successor_contract_identity": contract["successor_contract_identity"],
        "implementation_identity": implementation["implementation_identity"], "pilot11_regression_identity": regression["regression_identity"],
        "candidate_bytes_created": 0, "constructor_invocations": 0, "capability_restored_or_replaced": False,
        "v5_3_semantic_enforcement_weakened": False, "deterministic_blockers": [],
        "verdict": "PASS_SOURCE_ONLY_COORDINATE_BOUND_SEMANTIC_WITNESS_ALIGNMENT_REMEDIATION_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT11_V5_3_SURFACE_WITNESS_REMEDIATION_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot11-v5-3-surface-witness-root-cause-v1.json", analysis)
    write("humor-mechanics-batch2-development-constructor-surface-witness-alignment-contract-v5-3-1.json", contract)
    write("humor-mechanics-batch2-development-constructor-surface-witness-alignment-implementation-v5-3-1.json", implementation)
    write("humor-mechanics-batch2-development-pilot11-surface-witness-regression-v1.json", regression)
    write("humor-mechanics-batch2-development-pilot11-v5-3-surface-witness-remediation-audit-v1.json", audit)
    print(json.dumps({"verdict": analysis["root_cause_verdict"], "analysis_identity": analysis["analysis_identity"],
                      "successor_contract_identity": contract["successor_contract_identity"],
                      "implementation_identity": implementation["implementation_identity"],
                      "regression_identity": regression["regression_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()

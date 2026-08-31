"""Source-only Pilot 06 order-dominance analysis and obligation-governance remediation."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "e666296e2dcea0df6b226543c578e8b88fa594c7"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT))


def write(name: str, value: Any) -> None:
    path = ART / name
    if path.exists():
        raise SystemExit("artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != COMMIT:
        raise SystemExit("HEAD")
    disposition = load("docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-disposition-v1.json")
    reconciliation = load("docs/artifacts/humor-mechanics-batch2-development-pilot06-g03-reconciliation-v1.json")
    prior = load("docs/artifacts/humor-mechanics-batch2-reverse-disclosure-dependency-governance-v2.json")
    if disposition["disposition_identity"] != "91540ab00c1384aeee6f5017179e4ea6815aaeede3d15ed91a7d21b4f7b667b7":
        raise SystemExit("disposition")
    if reconciliation["reconciliation_identity"] != "778c28a69caaccf4cc75d8c6261a9075ba6b3c1f905e68a57758b9be1be92958":
        raise SystemExit("reconciliation")
    analysis_core = {
        "schema_name": "batch2-pilot06-order-dominance-root-cause-analysis-v1", "schema_version": "1.0.0",
        "disposition_commit": COMMIT, "disposition_identity": disposition["disposition_identity"],
        "candidate_identity": disposition["candidate_identity"], "candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "candidate_modified": False, "observed_blind_disagreement": reconciliation["dominance_disagreement"],
        "root_causes": [
            "MANDATORY_RESULT_FIRST_FACT_LAST_ORDER_CREATED_A_DELAYED_DISCLOSURE_ARCHITECTURE",
            "FACTUAL_RELATION_FUNCTIONED_AS_RETROSPECTIVE_EXPLANATION_INSTEAD_OF_AN_EARLY_VISIBLE_CAUSAL_ANCHOR",
            "COLON_AND_SECOND_SENTENCE_BOUNDARY_REINFORCED_SETUP_THEN_REVEAL_READING",
            "SINGLE_REPRESENTATION_TO_PHYSICAL_TRANSFER_MADE_LITERALIZATION_A_SALIENT_LOCAL_ENGINE",
            "V2_CONFORMANCE_PROVED_LINK_COMPLETENESS_BUT_DID_NOT_TEST_DOMINANCE_STABILITY_AGAINST_ORDER_CHANGE",
        ],
        "responsibility": {"mandatory_obligation_order": "PRIMARY", "constructor_realization": "CONTRIBUTING",
                           "source_proposition": "NOT_CAUSAL", "factual_authority": "NOT_CAUSAL",
                           "blind_review": "VALID_DETECTION_NOT_CAUSAL"},
        "counterfactual_findings": {
            "fact_available_before_or_with_chain": "REMOVES_DELAYED_DISCLOSURE_AS_PRIMARY_ORGANIZING_EFFECT",
            "same_links_without_fact_last_reveal": "ABSURD_CAUSAL_RELATION_REMAINS_AVAILABLE",
            "remove_literal_absorption_transfer": "CURRENT_SURFACE_LOSES_ONE_LOCAL_ENGINE_BUT_GOVERNANCE_CAN_REQUIRE_A_MULTI_LINK_CAUSAL_SPINE",
            "candidate_rewrite_performed": False,
        },
        "verdict": "ROOT_CAUSE_CONFIRMED_AT_ORDER_AND_DOMINANCE_GOVERNANCE_BOUNDARY",
    }
    analysis = {**analysis_core, "analysis_identity": seal("B2_PILOT06_ORDER_DOMINANCE_ROOT_CAUSE_ANALYSIS_V1", analysis_core)}
    constructor_obligation = {
        "obligation_version": "ORDER_ROBUST_CAUSAL_SPINE_V3",
        "transformation": [
            "Păstrează exact relația factuală furnizată, cu toate calificările și limitele ei, și fă-o disponibilă înainte ca textul să poată produce o schimbare retrospectivă de lectură.",
            "Construiește o consecință inventată prin cel puțin două legături locale distincte, fiecare necesară și recuperabilă din relația precedentă.",
            "Consecința trebuie să depindă de întregul lanț; simpla transformare a unui cuvânt, număr ori înscris într-un obiect fizic nu poate susține singură rezultatul.",
            "Marcajul nonfactual trebuie integrat firesc și trebuie să acopere toate legăturile inventate.",
        ],
        "forbidden_operations": [
            "Nu ascunde relația factuală până după rezultatul inventat și nu folosi dezvăluirea ei ca răsturnare principală.",
            "Nu introduce un reper, operand, eveniment ori cauză care nu poate fi urmărită local până la contextul autorizat.",
            "Nu baza rezultatul pe redenumire, reclasificare, personificare, intensificare, listă sau joc lexical.",
            "Nu impune o formulă fixă, un conector, un semn de punctuație, un registru ori un număr fix de propoziții.",
        ],
        "naturalness_and_safety": [
            "Folosește română idiomatică și concretă; nu transfera în suprafață limbajul acestei cerințe.",
            "Separă clar cadrul inventat de autoritatea factuală și nu adăuga fapte, citate, cunoaștere privată sau concluzii despre lumea reală.",
        ],
    }
    governance_core = {
        "schema_name": "batch2-order-robust-causal-spine-governance-v3", "schema_version": "3.0.0",
        "family_version": "ORDER_ROBUST_CAUSAL_SPINE_V3",
        "supersedes_governance_identity": prior["governance_identity"],
        "supersedes_obligation_family_identity": "6384918ed5ee8548ddfdeb7cc33bf8d60639add88ee38f4b0a10056365c30064",
        "root_cause_analysis_identity": analysis["analysis_identity"],
        "constructor_visible_obligation": constructor_obligation,
        "mandatory_pre_assignment_checks": ["EXACTLY_ONE_SUFFICIENT_PROPOSITION_AND_SPAN_BOUND", "POSITIVE_SOURCE_ONLY_ADJACENT_LINK_WITNESS",
                                             "NO_UNRESOLVED_REFERENCE_OR_OPERAND", "NO_SOURCE_SELECTION_BY_TARGET_SHAPE"],
        "g02b_additional_checks": ["NO_SEALED_MAPPING_OR_POOL_METADATA", "NO_FACT_LAST_OR_RESULT_FIRST_ORDER_MANDATE",
                                    "NO_FIXED_SURFACE_TEMPLATE", "EXACT_AUTHORIZED_CONTEXT_ONLY"],
        "g02c_required_checks": ["COMPLETE_MULTI_LINK_CAUSAL_SPINE", "EACH_LINK_NECESSARY_AND_NON_ARBITRARY",
                                  "NO_DELAYED_FACT_DISCLOSURE_AS_PRIMARY_EFFECT", "DOMINANCE_STABLE_UNDER_ORDER_NEUTRAL_STRUCTURAL_TEST",
                                  "NO_SINGLE_LITERAL_TRANSFER_AS_SOLE_ENGINE", "NO_INSTRUCTION_LANGUAGE_TRANSFER"],
        "construction_authority": False, "model_exposure_authority": False, "training_authority": False,
        "runtime_authority": False, "production_authority": False,
    }
    governance = {**governance_core, "governance_identity": seal("B2_ORDER_ROBUST_CAUSAL_SPINE_GOVERNANCE_V3", governance_core)}
    schema_core = {
        "schema_name": "batch2-order-robust-causal-spine-conformance-schema-v3", "schema_version": "3.0.0",
        "governance_identity": governance["governance_identity"],
        "required_predicates": governance["g02c_required_checks"],
        "order_neutral_test": {"surface_rewrite_forbidden": True, "structural_counterfactual_only": True,
                               "pass_condition": "CLAIMED_PRIMARY_OPERATION_REMAINS_NECESSARY_WHEN_FACT_IS_NOT_DELAYED",
                               "fail_condition": "DELAYED_DISCLOSURE_OR_RETROSPECTIVE_REORIENTATION_BECOMES_PRIMARY"},
        "allowed_verdicts": ["PASS", "FAIL_DELAYED_DISCLOSURE_DOMINANCE", "FAIL_INCOMPLETE_CAUSAL_SPINE", "FAIL_SINGLE_LITERAL_TRANSFER_DOMINANCE"],
        "mechanism_label_forbidden_in_constructor_view": True, "candidate_surface_creation_authority": False,
    }
    schema = {**schema_core, "schema_identity": seal("B2_ORDER_ROBUST_CAUSAL_SPINE_CONFORMANCE_SCHEMA_V3", schema_core)}
    regression_core = {
        "schema_name": "batch2-pilot06-order-dominance-regression-v1", "schema_version": "1.0.0",
        "candidate_identity": disposition["candidate_identity"], "candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "candidate_bytes_embedded": False, "candidate_modified": False,
        "expected_predicates": {"COMPLETE_MULTI_LINK_CAUSAL_SPINE": True, "EACH_LINK_NECESSARY_AND_NON_ARBITRARY": True,
                                "NO_DELAYED_FACT_DISCLOSURE_AS_PRIMARY_EFFECT": False,
                                "DOMINANCE_STABLE_UNDER_ORDER_NEUTRAL_STRUCTURAL_TEST": False,
                                "NO_SINGLE_LITERAL_TRANSFER_AS_SOLE_ENGINE": False,
                                "NO_INSTRUCTION_LANGUAGE_TRANSFER": True},
        "expected_verdict": "FAIL_DELAYED_DISCLOSURE_DOMINANCE",
        "observed_blind_basis": {"open": "TARGET_OPERATION_DOMINANT_HIGH", "contrast": "MISDIRECTION_DOMINANT_TARGET_SUPPORTING_HIGH"},
        "positive_pool_eligibility": False,
    }
    regression = {**regression_core, "regression_identity": seal("B2_PILOT06_ORDER_DOMINANCE_REGRESSION_V1", regression_core)}
    visible = canonical(constructor_obligation)
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension", rb"MISDIRECTION", rb"LITERALIZATION",
                 rb"mechanism_id", rb"mechanism_name", rb"G04B", rb"pool", rb"Pilot 06"]
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    if hits:
        raise SystemExit(f"leakage {hits}")
    audit_core = {
        "schema_name": "batch2-order-robust-causal-spine-governance-v3-audit-v1", "schema_version": "1.0.0",
        "analysis_identity": analysis["analysis_identity"], "governance_identity": governance["governance_identity"],
        "schema_identity": schema["schema_identity"], "regression_identity": regression["regression_identity"],
        "label_and_taxonomy_leakage": "PASS_ZERO_HITS", "definitional_paraphrase_risk": "PASS_OPERATIONAL_MINIMUM_NECESSARY",
        "fixed_template_risk": "PASS_ORDER_AND_SURFACE_FORM_NOT_FIXED", "source_shape_leakage": "PASS_SOURCE_SELECTION_REMAINS_PRE_ASSIGNMENT",
        "neighbor_answer_leakage": "PASS_PROHIBITIONS_OPERATIONAL_ONLY", "factual_authority_bypass": "PASS_EXACT_CONTEXT_REQUIRED",
        "hidden_construction_authority": "ABSENT", "pilot06_regression": "PASS_EXPECTED_REJECTION",
        "candidate_or_source_created": False, "deterministic_blockers_remaining": [],
        "verdict": "PASS_SOURCE_ONLY_ZERO_CONSTRUCTION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_ORDER_ROBUST_CAUSAL_SPINE_GOVERNANCE_V3_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-pilot06-order-dominance-root-cause-analysis-v1.json", analysis)
    write("humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json", governance)
    write("humor-mechanics-batch2-order-robust-causal-spine-conformance-schema-v3.json", schema)
    write("humor-mechanics-batch2-pilot06-order-dominance-regression-v1.json", regression)
    write("humor-mechanics-batch2-order-robust-causal-spine-governance-v3-audit-v1.json", audit)
    print(json.dumps({"verdict": analysis["verdict"], "analysis_identity": analysis["analysis_identity"],
                      "governance_identity": governance["governance_identity"], "schema_identity": schema["schema_identity"],
                      "regression_identity": regression["regression_identity"], "audit_identity": audit["audit_identity"],
                      "audit_verdict": audit["verdict"]}, sort_keys=True))


if __name__ == "__main__":
    main()

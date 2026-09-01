"""Git-object-only post-G01 proposition-sufficiency evaluation for Pilot 10."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "fa7852b5d75f1bb3f0deb12409f9aaa3fea827fa"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot10-ingestion-v1/"
ADMISSION = "docs/artifacts/humor-mechanics-batch2-development-pilot10-g01a-g01b-admission-v1.json"
ADMISSION_AUDIT = "docs/artifacts/humor-mechanics-batch2-development-pilot10-g01a-g01b-admission-v1-audit.json"
GOVERNANCE_V5_2 = "docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-governance-v5-2.json"
SCHEMA_V5_2 = "docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-conformance-schema-v5-2.json"
GOVERNANCE_V5 = "docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-governance-v5.json"
SCHEMA_V5 = "docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-conformance-schema-v5.json"
OUT = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path: str) -> dict[str, Any]:
    return json.loads(blob(path))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    admission, admission_audit = load(ADMISSION), load(ADMISSION_AUDIT)
    governance, schema = load(GOVERNANCE_V5_2), load(SCHEMA_V5_2)
    inherited_governance, inherited_schema = load(GOVERNANCE_V5), load(SCHEMA_V5)
    package = load(INGESTION + "source-package.json")
    envelope = load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(admission["admission_identity"] == "fd604ed8ab9ce4779d312c2308add3d78719f501f893536a4b77157fdc8132bc", "admission")
    require(admission_audit["audit_identity"] == "47f42b1c8180b35f6a5777b8c6cdbb3c89a3368bd5774dc9b4be7148e663442d", "audit")
    require(admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS", "G01")
    require(admission["proposition_sufficiency_evaluated"] is False, "prior sufficiency")
    require(governance["governance_identity"] == "80bbf059956424ce6f20885de51ce900f6116b40a223a107a46a29d3b012efc6", "V5.2 governance")
    require(schema["schema_identity"] == "084ddf4d8e9f215db3665370221260c351d3befe747c4dbb45ab35baac4c993b", "V5.2 schema")
    require(governance["supersedes_governance_identity"] == inherited_governance["governance_identity"], "V5 inheritance")
    require(governance["upstream_boundaries_unchanged"] == ["SOURCE_PROPOSITION_SUFFICIENCY", "ASSIGNMENT_SELECTION", "TYPED_STATIC_PLAN", "G02_FACTUAL_BOUNDARY"], "unchanged sufficiency boundary")
    require(schema["governance_identity"] == governance["governance_identity"], "schema binding")
    require(inherited_schema["governance_identity"] == inherited_governance["governance_identity"], "inherited schema")
    require(package["source_package_identity"] == "cd1c968bb7d90416b5255ad14094410491e756ce58bc78512cca2e5297a044c1", "package")
    require(package["factual_authority_envelope_identity"] == "fbae8cb29dcf203bae478b010fe19036239623551f22949b3cb56ac34ba18d21", "envelope")
    require(package["partition"] == "DEVELOPMENT" and package["family_identities"]["creative_premise_family_id"] == "UNASSIGNED", "partition")
    require(len(envelope["propositions"]) == 7, "proposition count")

    eligibility = {
        "P1": (False, "NO_EXPLICIT_RELATION_FROM_CONDITION_TO_RESULT"),
        "P2": (False, "PROCEDURE_DESCRIPTION_WITHOUT_CLOSED_RESULT"),
        "P3": (True, "CLOSED_CONJUNCTIVE_CONDITION_TO_EXPLICIT_DUAL_DISPOSITION"),
        "P4": (True, "CLOSED_DISJUNCTIVE_CONDITION_TO_EXPLICIT_DUAL_DISPOSITION"),
        "P5": (False, "RECORDING_RULE_REFERENCES_A_DISCREPANCY_WITHOUT_ASSERTING_OCCURRENCE"),
        "P6": (False, "SCOPE_LIMITATION_NOT_A_POSITIVE_SOURCE_RELATION"),
        "P7": (False, "EXPLICIT_UNKNOWN_OUTCOME_BOUNDARY"),
    }
    assessments = []
    for proposition in envelope["propositions"]:
        pid, span = proposition["proposition_id"], proposition["supporting_span"]
        start, end = span["utf8_byte_coordinates"]
        visible = source[start:end]
        require(hashlib.sha256(visible).hexdigest() == span["span_sha256"], f"{pid} span")
        eligible, reason = eligibility[pid]
        assessments.append({
            "proposition_id": pid, "supporting_span_sha256": span["span_sha256"],
            "standalone_semantic_closure": True,
            "reference_resolution": "PASS_INTERNAL_TO_SELECTED_SPAN" if pid in {"P3", "P4"} else "PASS_NO_UNRESOLVED_REFERENCE",
            "qualification_scope_time_modality_closure": "PASS_EXACT_BOUNDARIES_PRESERVED",
            "operand_closure": "PASS_EXACT_SOURCE_OPERANDS_NO_DERIVED_OPERAND",
            "relation_sufficiency": reason,
            "safely_selectable": eligible,
            "selection_status": "SELECTED_FIRST_SOURCE_ORDER_SUFFICIENT" if pid == "P3" else ("ELIGIBLE_NOT_SELECTED" if eligible else "NOT_SELECTED"),
        })
    eligible_ids = [item["proposition_id"] for item in assessments if item["safely_selectable"]]
    require(eligible_ids == ["P3", "P4"], "eligible set")
    selected = envelope["propositions"][2]
    require(selected["proposition_id"] == "P3", "deterministic selection")
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    visible_sha = hashlib.sha256(source[bs:be]).hexdigest()
    require(visible_sha == span["span_sha256"], "selected visible context")
    source_relation = {
        "kind": "SOURCE_RELATION_SUFFICIENCY_ONLY_NOT_A_REALIZATION_OR_WITNESS_PLAN",
        "condition_operands": ["CRATE_WEIGHT_MATCHES_DOCUMENTED_VALUE", "LABEL_NUMBER_MATCHES_DOCUMENT_NUMBER"],
        "relation": "CONJUNCTIVE_CONDITION_ENTAILS_THE_EXPLICIT_STATED_DISPOSITION",
        "result_operands": ["CRATE_RECORDED_APPROVED", "CRATE_MOVED_TO_HORTICULTURAL_STORAGE"],
        "reference_closure": "ALL_REFERENTS_RESOLVE_WITHIN_EXACT_P3_SUPPORTING_SPAN",
        "non_arbitrariness": "REMOVING_THE_CONDITION_OR_EITHER_STATED_DISPOSITION_CHANGES_THE_BOUND_SOURCE_RELATION",
        "candidate_surface": None, "realization_plan": None, "witness_plan": None, "humor": None,
    }
    core = {
        "schema_name": "batch2-pilot10-post-g01-proposition-sufficiency-receipt-v5-2", "schema_version": "5.2.0",
        "governance_identity": governance["governance_identity"], "schema_identity": schema["schema_identity"],
        "inherited_typed_operand_governance_identity": inherited_governance["governance_identity"],
        "inherited_typed_operand_schema_identity": inherited_schema["schema_identity"],
        "admission_commit": COMMIT, "admission_identity": admission["admission_identity"],
        "source_package_identity": package["source_package_identity"],
        "authority_envelope_identity": package["factual_authority_envelope_identity"],
        "selected_proposition_id": "P3", "selection_rule": "FIRST_SOURCE_ORDER_PROPOSITION_PASSING_ALL_SUFFICIENCY_REQUIREMENTS",
        "selected_supporting_span_sha256": span["span_sha256"], "authorized_visible_context_sha256": visible_sha,
        "authorized_visible_context": "EXACT_SELECTED_SUPPORTING_SPAN_ONLY",
        "standalone_semantic_closure": True, "reference_resolution": "PASS_INTERNAL_TO_SELECTED_SPAN",
        "operand_closure": "PASS_EXACT_SOURCE_OPERANDS_NO_DERIVED_OPERAND", "source_relation_sufficiency": source_relation,
        "qualification_preservation": "PASS_BOUND_EXACTLY", "scope_time_modality_unknown_boundaries": "PASS_PRESERVED",
        "mechanism_label_exposed": False, "assignment_performed": False, "candidate_surface": None,
        "constructor_v5_2_compatibility_evaluated": False, "realization_or_witness_planning_performed": False,
        "creative_premise_family_id": "UNASSIGNED", "all_proposition_assessments": assessments,
        "verdict": "PASS_SELECTED_PROPOSITION_SUFFICIENT",
        "authority_matrix": {key: False for key in ("assignment", "constructor_v5_2_source_compatibility_evaluation",
            "realization_witness_planning", "constructor_release", "constructor_invocation", "realization", "candidate_emission",
            "post_realization_pre_emission_conformance", "fragment_collision_evaluation", "g02", "g02c", "g03",
            "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "receipt_identity": seal("B2_PILOT10_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V5_2", core)}
    audit_core = {
        "schema_name": "batch2-pilot10-post-g01-proposition-sufficiency-audit-v5-2", "schema_version": "1.0.0",
        "receipt_identity": receipt["receipt_identity"], "git_object_only": True,
        "exact_admission_binding": "PASS", "exact_source_and_envelope_binding": "PASS",
        "seven_proposition_spans_reverified": "PASS", "eligible_propositions": eligible_ids,
        "exactly_one_selected_proposition": "PASS_P3_FIRST_SOURCE_ORDER_SUFFICIENT",
        "source_relation_sufficiency": "PASS_MECHANISM_NEUTRAL_NO_PLAN",
        "candidate_surface_absent": True, "realization_or_witness_planning_performed": False,
        "constructor_v5_2_compatibility_evaluated": False, "mechanism_label_absent": True,
        "downstream_authority": False, "deterministic_blockers": [],
        "verdict": "PASS_SOURCE_ONLY_NO_ASSIGNMENT_NO_PLANNING_ZERO_CONSTRUCTION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_PILOT10_POST_G01_PROPOSITION_SUFFICIENCY_AUDIT_V5_2", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot10-proposition-sufficiency-receipt-v5-2.json", receipt),
                        ("humor-mechanics-batch2-development-pilot10-proposition-sufficiency-audit-v5-2.json", audit)):
        path = OUT / name
        require(not path.exists(), "artifact exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": receipt["verdict"], "selected_proposition": "P3",
                      "receipt_identity": receipt["receipt_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()

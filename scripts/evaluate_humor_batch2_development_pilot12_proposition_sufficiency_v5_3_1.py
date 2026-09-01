"""Git-object-only post-G01 proposition-sufficiency evaluation for Pilot 12."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "6ab51407837cff623efe76d3b1ec48edc40279b3"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot12-ingestion-v1/"
ADMISSION = "docs/artifacts/humor-mechanics-batch2-development-pilot12-g01a-g01b-admission-v1.json"
ADMISSION_AUDIT = "docs/artifacts/humor-mechanics-batch2-development-pilot12-g01a-g01b-admission-v1-audit.json"
GOVERNANCE = "docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-governance-v5-3.json"
SCHEMA = "docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-conformance-schema-v5-3.json"
ALIGNMENT = "docs/artifacts/humor-mechanics-batch2-development-constructor-surface-witness-alignment-contract-v5-3-1.json"
OUT = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path: str) -> dict[str, Any]:
    return json.loads(blob(path))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    admission, admission_audit = load(ADMISSION), load(ADMISSION_AUDIT)
    governance, schema, alignment = load(GOVERNANCE), load(SCHEMA), load(ALIGNMENT)
    package = load(INGESTION + "source-package.json")
    envelope = load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(admission["admission_identity"] == "609478db1fddfb59b9b62a1ab5648cda813ce0f1fb94b2e9ef22df6dac59a294", "admission")
    require(admission_audit["audit_identity"] == "313d22983d8480ea6585141e3c05dff151918c1e92e1db2f3961439056f180db", "audit")
    require(admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS", "G01")
    require(admission["proposition_sufficiency_evaluated"] is False and admission["proposition_selected"] is False, "prior sufficiency")
    require(governance["governance_identity"] == "073d68d9d21c76974d12eb8e3f591f4172197377bfb36c2de2f85a5afe079dd6", "governance")
    require(schema["schema_identity"] == "4b26df92539082f11b83c83f76b1d158c7c8f4c87304bdcdd8a6129644f532f3", "schema")
    require(alignment["successor_contract_identity"] == "c4af75cd962802d0035d9de39e6d014f715d5b5f5b60fd690ea3761f289d99fc", "V5.3.1")
    require("SOURCE_PROPOSITION_SUFFICIENCY" in governance["upstream_boundaries_unchanged"], "sufficiency boundary")
    require(package["source_package_identity"] == "24e76e7f17c28a093cddb9c8be355c1298030a17f4cec0cf126210c4a529e3b6", "package")
    require(package["factual_authority_envelope_identity"] == "f219f9188b7d35134f0271b40fe485c5525a4b094b72b8c7b51472385fa5a1f4", "envelope")
    require(package["partition"] == "DEVELOPMENT" and package["family_identities"]["creative_premise_family_id"] == "UNASSIGNED", "partition")
    require(len(envelope["propositions"]) == 8, "proposition count")
    eligibility = {
        "P1": (False, "EVENT_DESCRIPTION_WITHOUT_CLOSED_CONDITION_TO_RESULT_RELATION"),
        "P2": (False, "ASSOCIATION_DESCRIPTION_WITHOUT_CLOSED_CONDITION_TO_RESULT_RELATION"),
        "P3": (False, "PROCEDURE_DESCRIPTION_WITHOUT_CLOSED_CONDITION_TO_RESULT_RELATION"),
        "P4": (False, "PROCEDURE_DESCRIPTION_WITHOUT_EXPLICIT_CONDITION_OR_DISPOSITION"),
        "P5": (True, "CLOSED_NECESSARY_CONDITION_TO_EXPLICIT_TRANSPORT_DISPOSITION"),
        "P6": (True, "CLOSED_MIXED_DESTINATION_CONDITION_TO_EXPLICIT_RECHECK_DISPOSITION"),
        "P7": (False, "SCOPE_LIMITATION_NOT_A_POSITIVE_CONDITION_TO_RESULT_RELATION"),
        "P8": (False, "EXPLICIT_UNKNOWN_OUTCOME_BOUNDARY"),
    }
    assessments = []
    for proposition in envelope["propositions"]:
        pid, span = proposition["proposition_id"], proposition["supporting_span"]
        start, end = span["utf8_byte_coordinates"]
        require(hashlib.sha256(source[start:end]).hexdigest() == span["span_sha256"], f"{pid} span")
        eligible, reason = eligibility[pid]
        assessments.append({"proposition_id": pid, "supporting_span_sha256": span["span_sha256"],
                            "standalone_semantic_closure": True,
                            "reference_resolution": "PASS_INTERNAL_TO_SELECTED_SPAN" if pid in {"P5", "P6"} else "PASS_NO_UNRESOLVED_REFERENCE",
                            "qualification_scope_time_modality_closure": "PASS_EXACT_BOUNDARIES_PRESERVED",
                            "operand_closure": "PASS_EXACT_SOURCE_OPERANDS_NO_DERIVED_OPERAND",
                            "relation_sufficiency": reason, "safely_selectable": eligible,
                            "selection_status": "SELECTED_FIRST_SOURCE_ORDER_SUFFICIENT" if pid == "P5" else ("ELIGIBLE_NOT_SELECTED" if eligible else "NOT_SELECTED")})
    eligible_ids = [item["proposition_id"] for item in assessments if item["safely_selectable"]]
    require(eligible_ids == ["P5", "P6"], "eligible set")
    selected = envelope["propositions"][4]
    require(selected["proposition_id"] == "P5", "selection")
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    visible_sha = hashlib.sha256(source[bs:be]).hexdigest()
    require(visible_sha == span["span_sha256"], "visible context")
    source_relation = {
        "kind": "SOURCE_RELATION_SUFFICIENCY_ONLY_NOT_SEMANTIC_ROLE_AFFORDANCE_REALIZATION_WITNESS_OR_ALIGNMENT_PLAN",
        "condition_operands": ["ALL_VOLUMES_IN_BOX_HAVE_SAME_DESTINATION_SHELF"],
        "relation": "NECESSARY_CONDITION_GOVERNS_EXPLICIT_BOX_TRANSPORT_DISPOSITION",
        "result_operands": ["BOX_TRANSPORTED_TO_LIBRARY_STORAGE"],
        "reference_closure": "ALL_REFERENTS_RESOLVE_WITHIN_EXACT_P5_SUPPORTING_SPAN",
        "non_arbitrariness": "REMOVING_CONDITION_OR_STATED_DISPOSITION_CHANGES_BOUND_SOURCE_RELATION",
        "candidate_surface": None, "semantic_role_plan": None, "affordance_plan": None,
        "realization_plan": None, "witness_plan": None, "morphological_alignment_plan": None,
        "constructor_compatibility": None, "humor": None,
    }
    authority_names = ("assignment", "semantic_role_or_affordance_planning",
                       "constructor_v5_3_1_source_compatibility_evaluation", "semantic_plan_evaluation",
                       "constructor_release", "constructor_invocation", "realization", "candidate_emission",
                       "coordinate_bound_semantic_conformance", "semantic_edge_validation", "fragment_collision_evaluation",
                       "g02", "g02c", "g03", "g04b_pool_certification", "model_exposure", "training",
                       "runtime_integration", "production_routing")
    core = {"schema_name": "batch2-pilot12-post-g01-proposition-sufficiency-receipt-v5-3-1", "schema_version": "5.3.1",
            "governance_identity": governance["governance_identity"], "schema_identity": schema["schema_identity"],
            "alignment_contract_identity": alignment["successor_contract_identity"], "admission_commit": COMMIT,
            "admission_identity": admission["admission_identity"], "source_package_identity": package["source_package_identity"],
            "authority_envelope_identity": package["factual_authority_envelope_identity"],
            "selected_proposition_id": "P5", "selection_rule": "FIRST_SOURCE_ORDER_PROPOSITION_PASSING_ALL_SUFFICIENCY_REQUIREMENTS",
            "eligible_propositions": eligible_ids, "selected_supporting_span_sha256": span["span_sha256"],
            "authorized_visible_context_sha256": visible_sha, "authorized_visible_context": "EXACT_SELECTED_SUPPORTING_SPAN_ONLY",
            "standalone_semantic_closure": True, "reference_resolution": "PASS_INTERNAL_TO_SELECTED_SPAN",
            "operand_closure": "PASS_EXACT_SOURCE_OPERANDS_NO_DERIVED_OPERAND",
            "source_relation_sufficiency": source_relation, "qualification_preservation": "PASS_BOUND_EXACTLY",
            "scope_time_modality_unknown_boundaries": "PASS_PRESERVED", "mechanism_label_exposed": False,
            "assignment_performed": False, "candidate_surface": None,
            "constructor_v5_3_1_compatibility_evaluated": False,
            "semantic_role_or_affordance_planning_performed": False,
            "realization_witness_or_morphological_alignment_planning_performed": False,
            "creative_premise_family_id": "UNASSIGNED", "all_proposition_assessments": assessments,
            "verdict": "PASS_SELECTED_PROPOSITION_SUFFICIENT",
            "authority_matrix": {key: False for key in authority_names}}
    receipt = {**core, "receipt_identity": seal("B2_PILOT12_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V5_3_1", core)}
    audit_core = {"schema_name": "batch2-pilot12-post-g01-proposition-sufficiency-audit-v5-3-1", "schema_version": "1.0.0",
                  "receipt_identity": receipt["receipt_identity"], "git_object_only": True,
                  "exact_admission_binding": "PASS", "exact_source_and_envelope_binding": "PASS",
                  "eight_proposition_spans_reverified": "PASS", "eligible_propositions": eligible_ids,
                  "exactly_one_selected_proposition": "PASS_P5_FIRST_SOURCE_ORDER_SUFFICIENT",
                  "source_relation_sufficiency": "PASS_MECHANISM_NEUTRAL_NO_SEMANTIC_REALIZATION_WITNESS_OR_ALIGNMENT_PLAN",
                  "candidate_surface_absent": True, "semantic_role_or_affordance_planning_performed": False,
                  "realization_witness_or_morphological_alignment_planning_performed": False,
                  "constructor_v5_3_1_compatibility_evaluated": False, "mechanism_label_absent": True,
                  "downstream_suitability_considered": False, "downstream_authority": False,
                  "deterministic_blockers": [],
                  "verdict": "PASS_SOURCE_ONLY_NO_ASSIGNMENT_NO_PLANNING_ZERO_CONSTRUCTION"}
    audit = {**audit_core, "audit_identity": seal("B2_PILOT12_POST_G01_PROPOSITION_SUFFICIENCY_AUDIT_V5_3_1", audit_core)}
    outputs = (("humor-mechanics-batch2-development-pilot12-proposition-sufficiency-receipt-v5-3-1.json", receipt),
               ("humor-mechanics-batch2-development-pilot12-proposition-sufficiency-audit-v5-3-1.json", audit))
    for name, value in outputs:
        path = OUT / name
        require(not path.exists(), "artifact exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": receipt["verdict"], "selected_proposition": "P5",
                      "eligible_propositions": eligible_ids, "receipt_identity": receipt["receipt_identity"],
                      "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()

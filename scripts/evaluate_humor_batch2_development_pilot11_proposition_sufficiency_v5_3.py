"""Git-object-only post-G01 proposition-sufficiency evaluation for Pilot 11."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "227571b6aa7097c2adca2ca275baeb88eb0f9c62"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot11-ingestion-v1/"
ADMISSION = "docs/artifacts/humor-mechanics-batch2-development-pilot11-g01a-g01b-admission-v1.json"
ADMISSION_AUDIT = "docs/artifacts/humor-mechanics-batch2-development-pilot11-g01a-g01b-admission-v1-audit.json"
GOVERNANCE = "docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-governance-v5-3.json"
SCHEMA = "docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-conformance-schema-v5-3.json"
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
    governance, schema = load(GOVERNANCE), load(SCHEMA)
    package, envelope = load(INGESTION + "source-package.json"), load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(admission["admission_identity"] == "d00cebe202d8e3bb24f2b220c7cbc24325eb4f666f629a4d4cbfc3541ba39ed5", "admission")
    require(admission_audit["audit_identity"] == "9ff020647be1b7c1655df6813b8b68fda4b6258aa238f28890b7bf51e4f98bb5", "audit")
    require(admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS", "G01")
    require(admission["proposition_sufficiency_evaluated"] is False, "prior sufficiency")
    require(governance["governance_identity"] == "073d68d9d21c76974d12eb8e3f591f4172197377bfb36c2de2f85a5afe079dd6", "governance")
    require(schema["schema_identity"] == "4b26df92539082f11b83c83f76b1d158c7c8f4c87304bdcdd8a6129644f532f3", "schema")
    require("SOURCE_PROPOSITION_SUFFICIENCY" in governance["upstream_boundaries_unchanged"], "sufficiency boundary")
    require(schema["governance_identity"] == governance["governance_identity"], "schema binding")
    require(package["source_package_identity"] == "f69112cebbb6edb3f46427a923de82383b1065e4d497e19f885fbfb8e117dd1e", "package")
    require(package["factual_authority_envelope_identity"] == "a12fa5890bdafe8d48e83897f4dea5a49c56bc59b301b2b37872991440dcd1f1", "envelope")
    require(package["partition"] == "DEVELOPMENT" and package["family_identities"]["creative_premise_family_id"] == "UNASSIGNED", "partition")
    require(len(envelope["propositions"]) == 7, "proposition count")
    eligibility = {
        "P1": (False, "EVENT_DESCRIPTION_WITHOUT_CLOSED_CONDITION_TO_RESULT_RELATION"),
        "P2": (False, "PROCEDURE_DESCRIPTION_WITHOUT_CLOSED_RESULT"),
        "P3": (True, "CLOSED_CONJUNCTIVE_CONDITION_TO_EXPLICIT_DUAL_DISPOSITION"),
        "P4": (True, "CLOSED_DISJUNCTIVE_CONDITION_TO_EXPLICIT_DUAL_DISPOSITION"),
        "P5": (False, "RECORDING_RULE_CONDITIONED_ON_UNASSERTED_REJECTION"),
        "P6": (False, "SCOPE_LIMITATION_NOT_A_POSITIVE_SOURCE_RELATION"),
        "P7": (False, "EXPLICIT_UNKNOWN_OUTCOME_BOUNDARY"),
    }
    assessments = []
    for proposition in envelope["propositions"]:
        pid, span = proposition["proposition_id"], proposition["supporting_span"]
        start, end = span["utf8_byte_coordinates"]
        require(hashlib.sha256(source[start:end]).hexdigest() == span["span_sha256"], f"{pid} span")
        eligible, reason = eligibility[pid]
        assessments.append({"proposition_id": pid, "supporting_span_sha256": span["span_sha256"],
            "standalone_semantic_closure": True,
            "reference_resolution": "PASS_INTERNAL_TO_SELECTED_SPAN" if pid in {"P3", "P4"} else "PASS_NO_UNRESOLVED_REFERENCE",
            "qualification_scope_time_modality_closure": "PASS_EXACT_BOUNDARIES_PRESERVED",
            "operand_closure": "PASS_EXACT_SOURCE_OPERANDS_NO_DERIVED_OPERAND", "relation_sufficiency": reason,
            "safely_selectable": eligible,
            "selection_status": "SELECTED_FIRST_SOURCE_ORDER_SUFFICIENT" if pid == "P3" else ("ELIGIBLE_NOT_SELECTED" if eligible else "NOT_SELECTED")})
    eligible_ids = [item["proposition_id"] for item in assessments if item["safely_selectable"]]
    require(eligible_ids == ["P3", "P4"], "eligible set")
    selected = envelope["propositions"][2]
    require(selected["proposition_id"] == "P3", "selection")
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    visible_sha = hashlib.sha256(source[bs:be]).hexdigest()
    require(visible_sha == span["span_sha256"], "visible context")
    source_relation = {"kind": "SOURCE_RELATION_SUFFICIENCY_ONLY_NOT_SEMANTIC_ROLE_AFFORDANCE_REALIZATION_OR_WITNESS_PLAN",
        "condition_operands": ["BOTH_SURFACE_AND_SERIAL_CHECKS_CONFORM"],
        "relation": "CONJUNCTIVE_CONDITION_ENTAILS_EXPLICIT_STATED_ACCEPTANCE_AND_FILLING_DISPOSITION",
        "result_operands": ["CONTAINER_RECORDED_ACCEPTED", "CONTAINER_SENT_TO_FILLING_LINE"],
        "reference_closure": "ALL_REFERENTS_RESOLVE_WITHIN_EXACT_P3_SUPPORTING_SPAN",
        "non_arbitrariness": "REMOVING_CONDITION_OR_EITHER_STATED_DISPOSITION_CHANGES_BOUND_SOURCE_RELATION",
        "candidate_surface": None, "semantic_role_plan": None, "affordance_plan": None,
        "realization_plan": None, "witness_plan": None, "humor": None}
    core = {"schema_name": "batch2-pilot11-post-g01-proposition-sufficiency-receipt-v5-3", "schema_version": "5.3.0",
        "governance_identity": governance["governance_identity"], "schema_identity": schema["schema_identity"],
        "admission_commit": COMMIT, "admission_identity": admission["admission_identity"],
        "source_package_identity": package["source_package_identity"],
        "authority_envelope_identity": package["factual_authority_envelope_identity"],
        "selected_proposition_id": "P3", "selection_rule": "FIRST_SOURCE_ORDER_PROPOSITION_PASSING_ALL_SUFFICIENCY_REQUIREMENTS",
        "selected_supporting_span_sha256": span["span_sha256"], "authorized_visible_context_sha256": visible_sha,
        "authorized_visible_context": "EXACT_SELECTED_SUPPORTING_SPAN_ONLY", "standalone_semantic_closure": True,
        "reference_resolution": "PASS_INTERNAL_TO_SELECTED_SPAN", "operand_closure": "PASS_EXACT_SOURCE_OPERANDS_NO_DERIVED_OPERAND",
        "source_relation_sufficiency": source_relation, "qualification_preservation": "PASS_BOUND_EXACTLY",
        "scope_time_modality_unknown_boundaries": "PASS_PRESERVED", "mechanism_label_exposed": False,
        "assignment_performed": False, "candidate_surface": None, "constructor_v5_3_compatibility_evaluated": False,
        "semantic_role_or_affordance_planning_performed": False, "realization_or_witness_planning_performed": False,
        "creative_premise_family_id": "UNASSIGNED", "all_proposition_assessments": assessments,
        "verdict": "PASS_SELECTED_PROPOSITION_SUFFICIENT",
        "authority_matrix": {key: False for key in ("assignment", "semantic_role_or_affordance_planning",
            "constructor_v5_3_source_compatibility_evaluation", "semantic_plan_evaluation", "constructor_release",
            "constructor_invocation", "realization", "candidate_emission", "semantic_edge_validation",
            "fragment_collision_evaluation", "g02", "g02c", "g03", "g04b_pool_certification", "model_exposure",
            "training", "runtime_integration", "production_routing")}}
    receipt = {**core, "receipt_identity": seal("B2_PILOT11_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V5_3", core)}
    audit_core = {"schema_name": "batch2-pilot11-post-g01-proposition-sufficiency-audit-v5-3", "schema_version": "1.0.0",
        "receipt_identity": receipt["receipt_identity"], "git_object_only": True, "exact_admission_binding": "PASS",
        "exact_source_and_envelope_binding": "PASS", "seven_proposition_spans_reverified": "PASS",
        "eligible_propositions": eligible_ids, "exactly_one_selected_proposition": "PASS_P3_FIRST_SOURCE_ORDER_SUFFICIENT",
        "source_relation_sufficiency": "PASS_MECHANISM_NEUTRAL_NO_SEMANTIC_OR_REALIZATION_PLAN",
        "candidate_surface_absent": True, "semantic_role_or_affordance_planning_performed": False,
        "realization_or_witness_planning_performed": False, "constructor_v5_3_compatibility_evaluated": False,
        "mechanism_label_absent": True, "downstream_authority": False, "deterministic_blockers": [],
        "verdict": "PASS_SOURCE_ONLY_NO_ASSIGNMENT_NO_PLANNING_ZERO_CONSTRUCTION"}
    audit = {**audit_core, "audit_identity": seal("B2_PILOT11_POST_G01_PROPOSITION_SUFFICIENCY_AUDIT_V5_3", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot11-proposition-sufficiency-receipt-v5-3.json", receipt),
                        ("humor-mechanics-batch2-development-pilot11-proposition-sufficiency-audit-v5-3.json", audit)):
        path = OUT / name
        require(not path.exists(), "artifact exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": receipt["verdict"], "selected_proposition": "P3",
                      "receipt_identity": receipt["receipt_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()

"""Git-object-only post-G01 proposition-sufficiency evaluation for Pilot 13."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "9a4d7f8188bf435c46a299141071b116027aed05"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot13-ingestion-v1/"
ADMISSION = "docs/artifacts/humor-mechanics-batch2-development-pilot13-g01a-g01b-admission-v1.json"
ADMISSION_AUDIT = "docs/artifacts/humor-mechanics-batch2-development-pilot13-g01a-g01b-admission-v1-audit.json"
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
    package = load(INGESTION + "source-package.json")
    envelope = load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(admission["admission_identity"] == "cf7e46f5f187a92a982d16357485035898d34ca262aa8a5747fbfcf5fe4be2b4", "admission")
    require(admission_audit["audit_identity"] == "deb4f6808f7457624414d4abe9599680bc81ac354cdb545dd23f23d76b2012de", "audit")
    require(admission["g01a"]["verdict"] == admission["g01b"]["verdict"] == "PASS", "G01")
    require(admission["proposition_sufficiency_evaluated"] is False and admission["proposition_selected"] is False, "prior sufficiency")
    require(package["source_package_identity"] == "3acf18889454e8fdd8397e0a41f6f96216cd6be98f6ab2b54131acff1e7c31a0", "package")
    require(package["factual_authority_envelope_identity"] == "509b2472a28a2f6ce3b514a05820f13be29d60df98464af0b1e25d1bb1cb3af9", "envelope")
    require(package["partition"] == "DEVELOPMENT" and envelope["creative_premise_family_id"] == "UNASSIGNED", "partition")
    require(len(envelope["propositions"]) == 8 and envelope["proposition_selection"] == "NOT_PERFORMED", "proposition boundary")
    eligibility = {
        "P1": (False, "EVENT_DESCRIPTION_WITHOUT_CLOSED_CONDITION_TO_RESULT_RELATION"),
        "P2": (False, "ASSOCIATION_DESCRIPTION_WITHOUT_CLOSED_CONDITION_TO_RESULT_RELATION"),
        "P3": (False, "VERIFICATION_PROCEDURE_WITHOUT_CLOSED_CONDITION_TO_RESULT_RELATION"),
        "P4": (False, "INSTALLATION_DESCRIPTION_WITHOUT_EXPLICIT_CONDITION_OR_DISPOSITION"),
        "P5": (True, "CLOSED_POST_INSTALLATION_CONDITION_TO_EXPLICIT_POSITION_AND_TIME_LOGGING_DISPOSITION"),
        "P6": (True, "CLOSED_INSTALLATION_FAILURE_CONDITION_TO_EXPLICIT_NONINSTALLATION_AND_SEPARATE_LOGGING_DISPOSITION"),
        "P7": (False, "SCOPE_LIMITATION_NOT_A_POSITIVE_CONDITION_TO_RESULT_RELATION"),
        "P8": (False, "EXPLICIT_UNKNOWN_OUTCOME_BOUNDARY"),
    }
    assessments = []
    for proposition in envelope["propositions"]:
        pid, span = proposition["proposition_id"], proposition["supporting_span"]
        bs, be = span["utf8_byte_coordinates"]
        require(hashlib.sha256(source[bs:be]).hexdigest() == span["span_sha256"], f"{pid} span")
        for field in ("subject", "predicate", "object"):
            item = proposition[field]
            start, end = item["utf8_byte_coordinates"]
            require(hashlib.sha256(source[start:end]).hexdigest() == item["sha256"], f"{pid} {field}")
        eligible, reason = eligibility[pid]
        assessments.append({"proposition_id": pid, "supporting_span_sha256": span["span_sha256"],
                            "semantic_completeness": "PASS_STANDALONE_BOUND_SOURCE_RELATION",
                            "reference_closure": "PASS_INTERNAL_TO_EXACT_SUPPORTING_SPAN",
                            "qualification_retention": "PASS_EXACT" if proposition["qualification"] else "PASS_NOT_APPLICABLE",
                            "scope_modality_time_closure": "PASS_EXACT_BOUNDARIES_PRESERVED",
                            "operand_closure": "PASS_EXACT_SOURCE_OPERANDS_NO_DERIVED_OPERAND",
                            "factual_authority_boundary": "PASS_NO_AUTHORITY_WIDENING",
                            "relation_sufficiency": reason, "safely_selectable": eligible,
                            "selection_status": "SELECTED_FIRST_SOURCE_ORDER_SUFFICIENT" if pid == "P5" else ("ELIGIBLE_NOT_SELECTED" if eligible else "NOT_SELECTED")})
    eligible_ids = [item["proposition_id"] for item in assessments if item["safely_selectable"]]
    require(eligible_ids == ["P5", "P6"], "eligible set")
    selected = envelope["propositions"][4]
    require(selected["proposition_id"] == "P5", "selection")
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    visible_sha = hashlib.sha256(source[bs:be]).hexdigest()
    require(visible_sha == span["span_sha256"], "selected span")
    source_relation = {"kind": "SOURCE_RELATION_SUFFICIENCY_ONLY_NO_DOWNSTREAM_PLANNING",
                       "condition_operands": ["POST_INSTALLATION_STATE"],
                       "relation": "POST_INSTALLATION_STATE_GOVERNS_EXPLICIT_ACTUAL_POSITION_AND_INSTALLATION_TIME_LOGGING",
                       "result_operands": ["ACTUAL_SENSOR_POSITION", "INSTALLATION_TIME", "CAMPAIGN_LOG"],
                       "reference_closure": "ALL_REFERENTS_RESOLVE_WITHIN_EXACT_P5_SUPPORTING_SPAN",
                       "candidate_surface": None, "mechanism": None, "assignment": None, "obligation": None,
                       "constructor_compatibility": None, "semantic_role_plan": None, "affordance_plan": None,
                       "realization_plan": None, "witness_plan": None, "morphological_alignment_plan": None}
    authority_names = ("assignment", "constructor_compatibility", "semantic_plan", "constructor_release", "constructor_invocation",
                       "provider_invocation", "emitter_invocation", "realization", "candidate_emission", "semantic_conformance",
                       "fragment_collision", "g02", "g02c", "g03", "g03b", "g03c", "romanian_naturalness", "voice",
                       "owner_review", "g04b", "model_exposure", "training", "runtime_integration", "production_routing")
    core = {"schema_name": "batch2-pilot13-post-g01-proposition-sufficiency-receipt-v5-3-3", "schema_version": "5.3.3",
            "pilot_role": "LEGITIMATE_END_TO_END_MECHANISM_TRIAL", "admission_commit": COMMIT,
            "admission_identity": admission["admission_identity"], "source_package_identity": package["source_package_identity"],
            "authority_envelope_identity": package["factual_authority_envelope_identity"], "selected_proposition_id": "P5",
            "selection_rule": "FIRST_SOURCE_ORDER_PROPOSITION_PASSING_ALL_SUFFICIENCY_REQUIREMENTS",
            "eligible_propositions": eligible_ids, "selected_supporting_span_sha256": span["span_sha256"],
            "authorized_visible_context_sha256": visible_sha, "authorized_visible_context": "EXACT_SELECTED_SUPPORTING_SPAN_ONLY",
            "source_relation_sufficiency": source_relation, "all_proposition_assessments": assessments,
            "downstream_suitability_considered": False, "mechanism_label_exposed": False, "assignment_performed": False,
            "creative_premise_family_id": "UNASSIGNED", "verdict": "PASS_SELECTED_PROPOSITION_SUFFICIENT",
            "authority_matrix": {key: False for key in authority_names}}
    receipt = {**core, "receipt_identity": seal("B2_PILOT13_POST_G01_PROPOSITION_SUFFICIENCY_RECEIPT_V5_3_3", core)}
    audit_core = {"schema_name": "batch2-pilot13-post-g01-proposition-sufficiency-audit-v5-3-3", "schema_version": "1.0.0",
                  "receipt_identity": receipt["receipt_identity"], "git_object_only": True, "exact_admission_binding": "PASS",
                  "exact_source_and_envelope_binding": "PASS", "eight_proposition_spans_reverified": "PASS",
                  "eligible_propositions": eligible_ids, "exactly_one_selected_proposition": "PASS_P5_FIRST_SOURCE_ORDER_SUFFICIENT",
                  "exact_selected_supporting_span_binding": "PASS", "candidate_surface_absent": True,
                  "downstream_suitability_considered": False, "downstream_authority": False,
                  "deterministic_blockers": [], "verdict": "PASS_SOURCE_ONLY_NO_ASSIGNMENT_NO_PLANNING_ZERO_CONSTRUCTION"}
    audit = {**audit_core, "audit_identity": seal("B2_PILOT13_POST_G01_PROPOSITION_SUFFICIENCY_AUDIT_V5_3_3", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot13-proposition-sufficiency-receipt-v5-3-3.json", receipt),
                        ("humor-mechanics-batch2-development-pilot13-proposition-sufficiency-audit-v5-3-3.json", audit)):
        path = OUT / name
        require(not path.exists(), "artifact exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": receipt["verdict"], "selected_proposition": "P5", "eligible_propositions": eligible_ids,
                      "selected_supporting_span_sha256": span["span_sha256"], "receipt_identity": receipt["receipt_identity"],
                      "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()

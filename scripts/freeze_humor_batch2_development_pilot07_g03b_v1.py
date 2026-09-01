"""Freeze the Pilot 07 G03B causal/minimal-intervention review."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"
G03_COMMIT = "2ad9fde06c6e87ec5548be578d6061c58462c981"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-v1.txt"
G03_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-g03-receipt-v1.json"
G03_RECONCILIATION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-g03-reconciliation-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{G03_COMMIT}:{path}"], cwd=ROOT)


def git_json(path: str) -> dict[str, Any]:
    return json.loads(git_bytes(path))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def write_json(name: str, value: dict[str, Any]) -> None:
    (ARTIFACTS / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == G03_COMMIT, "HEAD does not equal the authorized G03 commit")

    candidate = git_bytes(CANDIDATE_PATH)
    g03 = git_json(G03_RECEIPT_PATH)
    reconciliation = git_json(G03_RECONCILIATION_PATH)
    require(hashlib.sha256(candidate).hexdigest() == "769228fc99006e0f665360f28805f31d4480419095de1f1fba5794319cc1bfa8", "candidate hash")
    require(g03["g03_receipt_identity"] == "bc30997ba763126f8ee0eda3d0a5375dbc9f6ba514e3394ada34cc086d9b5bf9", "G03 receipt")
    require(g03["g03_validity_status"] == "VALID_BLIND_REVIEW", "G03 validity")
    require(reconciliation["reconciliation_identity"] == "6cc80a45b8dd9109a1e6901e87f237755b21419c6e11d79f3cee20f648e64061", "reconciliation")
    require(reconciliation["reconciliation_classification"] == "TARGET_RECOVERED_DOMINANT", "G03 classification")

    interventions = [
        {
            "id": "G03B-I01-REMOVE-RECURSIVE-HINGE",
            "delta_only": "Remove only the step in which analysis of the new field requires another report entry.",
            "preserved": ["P5 factual premise", "fictional marking", "first added field", "topic", "register"],
            "expected_observation": "The process stops after one added field; the self-propagating consequence and target dominance disappear.",
            "mechanism_after": "ABSENT_OR_WEAK",
            "causal_result": "MECHANISM_REMOVED",
        },
        {
            "id": "G03B-I02-REMOVE-FIRST-CREATIVE-HINGE",
            "delta_only": "Keep the factual entry for later analysis but remove the imagined rule that the entry adds a new report field.",
            "preserved": ["P5 factual premise", "fictional marking", "later-analysis purpose", "topic"],
            "expected_observation": "No new object exists to trigger the remaining dependency chain.",
            "mechanism_after": "ABSENT",
            "causal_result": "MECHANISM_REMOVED",
        },
        {
            "id": "G03B-I03-SUBSTITUTE-UNRELATED-ABSURDITY",
            "delta_only": "Keep the factual premise and fictional status but substitute an absurd event unrelated to entry and analysis.",
            "preserved": ["P5 factual premise", "fictional status", "topic", "approximate length", "absurd tone"],
            "expected_observation": "Absurdity remains, but the recoverable premise-dependent extension is absent and the classification changes.",
            "mechanism_after": "ABSENT_LABEL_CHANGES",
            "causal_result": "LABEL_CHANGE",
        },
        {
            "id": "G03B-I04-PARAPHRASE-SURFACE-CUES",
            "delta_only": "Change vocabulary, punctuation, and sentence segmentation while preserving every dependency link and the terminal comparison.",
            "preserved": ["P5 factual premise", "fictional marking", "dependency graph", "payoff", "topic"],
            "expected_observation": "The target remains dominant without reliance on a fixed word, connector, punctuation pattern, or sentence template.",
            "mechanism_after": "DOMINANT",
            "causal_result": "INVARIANT_UNDER_SURFACE_PARAPHRASE",
        },
        {
            "id": "G03B-I05-REMOVE-CREATIVE-MARKER",
            "delta_only": "Remove only the explicit fictional continuation marker.",
            "preserved": ["P5 factual premise", "dependency graph", "terminal comparison", "topic"],
            "expected_observation": "The causal operation remains legible, but the candidate becomes independently invalid at G02's factual/creative boundary.",
            "mechanism_after": "DOMINANT_BUT_AUTHORITY_INVALID",
            "causal_result": "MARKER_NOT_CAUSAL_TO_MECHANISM",
        },
        {
            "id": "G03B-I06-CAP-REPETITION",
            "delta_only": "Allow one premise-dependent added field but stop the process before the cycle repeats.",
            "preserved": ["P5 factual premise", "fictional marking", "first hinge", "topic", "register"],
            "expected_observation": "Cumulative escalation disappears; a short logical extension remains but loses much of its absurd payoff.",
            "mechanism_after": "SUPPORTING_OR_WEAK_NOT_DOMINANT",
            "causal_result": "ESCALATION_REMOVED_TARGET_WEAKENED",
        },
    ]

    authority_matrix = {
        key: False
        for key in (
            "g03c",
            "g04a_romanian_naturalness",
            "g04b_pool_certification",
            "voice_review",
            "owner_review",
            "candidate_repair",
            "candidate_rewrite",
            "candidate_regeneration",
            "training",
            "runtime_integration",
            "production_routing",
        )
    }
    review_core = {
        "schema_name": "batch2-development-pilot07-candidate01-g03b-causal-review-v1",
        "schema_version": "1.0.0",
        "candidate_identity": g03["candidate_identity"],
        "candidate_raw_sha256": g03["candidate_raw_sha256"],
        "creative_premise_family_id": g03["creative_premise_family_id"],
        "g03_commit": G03_COMMIT,
        "g03_receipt_identity": g03["g03_receipt_identity"],
        "reconciliation_identity": reconciliation["reconciliation_identity"],
        "tested_mechanism": "Absurd Logical Extension",
        "candidate_bytes_modified": False,
        "counterfactuals_materialized_as_candidates": False,
        "causal_trace": {
            "factual_premise": "An observed technical problem is entered in the verification report for later analysis.",
            "creative_marking": "Într-o continuare imaginară",
            "transformation_step_1": "The entry adds a new field to the report.",
            "transformation_step_2": "Analysis of that field requires another entry, which creates the same condition again.",
            "absurd_consequence": "The recurrence continues until the report becomes longer than the verification.",
            "local_dependency": "P5_ENTRY_FOR_ANALYSIS_TO_NEW_FIELD_TO_FIELD_ANALYSIS_TO_NEW_ENTRY_TO_RECURSIVE_GROWTH",
            "verdict": "COMPLETE_RECOVERABLE_CAUSAL_CHAIN",
        },
        "minimal_interventions": interventions,
        "controls": {
            "topic_control": "PASS",
            "factual_premise_control": "PASS",
            "delta_only_control": "PASS",
            "creative_marking_separated_from_mechanism_causality": "PASS_I05",
            "lexical_keyword_dependence": "REJECTED_BY_I04",
            "mere_absurdity_explanation": "REJECTED_BY_I03",
            "cumulative_escalation_isolation": "PASS_I06",
        },
        "causal_findings": {
            "necessary_structure": [
                "P5 factual relation",
                "first premise-dependent consequence",
                "recursive locally dependent consequence",
                "terminal absurd payoff",
            ],
            "not_necessary": ["specific vocabulary", "specific connector", "punctuation", "sentence segmentation", "surface template"],
            "removal_test": "PASS_I01_AND_I02_REMOVE_TARGET_STRUCTURE",
            "substitution_test": "PASS_I03_CHANGES_LABEL",
            "surface_paraphrase_invariance": "PASS_I04",
            "factual_boundary_separation": "PASS_I05",
            "supporting_escalation_isolation": "PASS_I06",
        },
        "g03b_verdict": "CAUSAL_MECHANISM_CONFIRMED",
        "candidate_disposition_effect": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G03C_ONLY",
        "authority_matrix": authority_matrix,
    }
    review = {
        **review_core,
        "g03b_review_identity": seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_G03B_REVIEW_V1", review_core),
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot07-candidate01-g03b-receipt-v1",
        "schema_version": "1.0.0",
        "candidate_identity": review_core["candidate_identity"],
        "candidate_raw_sha256": review_core["candidate_raw_sha256"],
        "g03_receipt_identity": review_core["g03_receipt_identity"],
        "g03b_review_identity": review["g03b_review_identity"],
        "g03b_verdict": review_core["g03b_verdict"],
        "candidate_bytes_modified": False,
        "counterfactual_candidate_created": False,
        "next_gate_eligible": "G03C_SEPARATELY_AUTHORIZED_ONLY",
        "authority_matrix": authority_matrix,
    }
    receipt = {
        **receipt_core,
        "g03b_receipt_identity": seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_G03B_RECEIPT_V1", receipt_core),
    }
    write_json("humor-mechanics-batch2-development-pilot07-candidate01-g03b-review-v1.json", review)
    write_json("humor-mechanics-batch2-development-pilot07-candidate01-g03b-receipt-v1.json", receipt)
    print(json.dumps({
        "g03b_verdict": review["g03b_verdict"],
        "g03b_review_identity": review["g03b_review_identity"],
        "g03b_receipt_identity": receipt["g03b_receipt_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

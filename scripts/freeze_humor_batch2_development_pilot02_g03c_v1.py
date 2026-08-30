"""Freeze Pilot 02 candidate/pool G03C shortcut and contamination diagnostics."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G03B_COMMIT = "01f63d7c35814dd85e0f36f6301419956cc0d3d4"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-v1.txt"
G03B_REVIEW_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g03b-review-v1.json"
G03B_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g03b-receipt-v1.json"
PILOT01_DISPOSITION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot01-candidate01-disposition-v1.json"
PILOT02_ADMISSION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-g01a-g01b-admission-v1.json"
PILOT02_ASSIGNMENT_AUDIT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-assignment-design-leakage-audit-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load_json(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def load_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    require(
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G03B_COMMIT,
        "HEAD differs from G03B freeze",
    )
    candidate = load_bytes(G03B_COMMIT, CANDIDATE_PATH)
    g03b = load_json(G03B_COMMIT, G03B_REVIEW_PATH)
    g03b_receipt = load_json(G03B_COMMIT, G03B_RECEIPT_PATH)
    pilot01 = load_json(G03B_COMMIT, PILOT01_DISPOSITION_PATH)
    admission = load_json(G03B_COMMIT, PILOT02_ADMISSION_PATH)
    assignment_audit = load_json(G03B_COMMIT, PILOT02_ASSIGNMENT_AUDIT_PATH)
    require(hashlib.sha256(candidate).hexdigest() == g03b["candidate_raw_sha256"], "candidate bytes")
    require(g03b["g03b_verdict"] == "CAUSAL_MECHANISM_CONFIRMED", "G03B verdict")
    require(
        g03b["g03b_review_identity"]
        == "cb8c00b8498b73f4c39eaa4d4da4a943fc5e6461ec3070ed844d175d6e3c6892",
        "G03B review identity",
    )
    require(
        g03b_receipt["g03b_receipt_identity"]
        == "825d2b7f58a6b7b2c12487d8c26e1c65d431138b1ea516ff6140a94f37662009",
        "G03B receipt identity",
    )
    require(admission["g01b"]["contamination_state"] == "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE", "admission contamination")
    require(assignment_audit["blind_evaluation_contamination"] == "ABSENT_NO_BLIND_ACCESS_OR_REFERENCE", "assignment contamination")
    require(pilot01["positive_m13_coverage_eligible"] is False, "Pilot 01 cannot count positive")

    diagnostic_core = {
        "schema_name": "batch2-development-pilot02-candidate01-g03c-diagnostic-v1",
        "schema_version": "1.0.0",
        "candidate_identity": g03b["candidate_identity"],
        "candidate_raw_sha256": g03b["candidate_raw_sha256"],
        "creative_premise_family_id": g03b["creative_premise_family_id"],
        "g03b_commit": G03B_COMMIT,
        "g03b_review_identity": g03b["g03b_review_identity"],
        "g03b_receipt_identity": g03b_receipt["g03b_receipt_identity"],
        "candidate_bytes_modified": False,
        "blind_holdout_content_accessed": False,
        "candidate_level": {
            "lexical": {
                "observed_cues": ["continuare explicit fictivă", "fiindcă", "apoi", "încetează"],
                "finding": "PASS_NONDEFINING_AND_G03B_PARAPHRASE_INVARIANT",
                "material": False,
            },
            "format": {
                "observed": "TWO_SENTENCES_FACTUAL_PREMISE_THEN_MARKED_CREATIVE_CONTINUATION",
                "finding": "PASS_GENERIC_AUTHORITY_SAFETY_SHAPE_NOT_TARGET_SPECIFIC",
                "material": False,
            },
            "position": {
                "observed": "PAYOFF_AT_END",
                "finding": "PASS_COMMON_HUMOR_POSITION_NOT_DISCRIMINATIVE",
                "material": False,
            },
            "length": {
                "utf8_bytes": len(candidate),
                "finding": "PASS_NO_LENGTH_RULE_OR_TARGET_THRESHOLD",
                "material": False,
            },
            "topic_entity": {
                "observed": "NEUTRAL_SYNTHETIC_TASTING_TEST_NO_NAMED_PERSON_OR_PROTECTED_ENTITY",
                "finding": "PASS_SOURCE_ACQUIRED_AND_PARTITIONED_BEFORE_ASSIGNMENT",
                "material": False,
            },
            "constructor_template": {
                "observed": "SUCCESSOR_OBLIGATION_REQUIRES_TWO_LOCALLY_DEPENDENT_CHANGES_WITHOUT_FIXED_LEXEME_OR_GRAMMAR",
                "finding": "PASS_FOR_THIS_CANDIDATE_G03B_ESTABLISHES_STRUCTURAL_NOT_TEMPLATE_DEPENDENCE",
                "material": False,
            },
            "metadata": {
                "finding": "PASS_CANDIDATE_ARTIFACT_HAS_NO_MECHANISM_ID_NAME_ORDINAL_OR_ANSWER_KEY",
                "material": False,
            },
            "weak_nonsemantic_classifier": {
                "execution": "NOT_TRAINED_NO_MODEL_OR_STATISTICAL_FIT",
                "feature_only_hypotheses": ["lexeme", "punctuation", "length", "topic", "sentence position", "packet format"],
                "diagnostic": "NO_SINGLE_FEATURE_EXPLAINS_BOTH_BLIND_RECOVERY_AND_G03B_INVARIANCE",
                "finding": "PASS_CANDIDATE_LEVEL",
            },
            "verdict": "CANDIDATE_SHORTCUT_PASS",
        },
        "pool_level": {
            "accessible_scope": "DEVELOPMENT_AND_FROZEN_NONBLIND_METADATA_ONLY",
            "blind_reserve": "NOT_ACCESSED_NOT_TUNED",
            "family_overlap": {
                "pilot02_source_family": admission["g01b"]["family_identities"]["source_family"],
                "pilot02_event_family": admission["g01b"]["family_identities"]["event_family"],
                "pilot02_topic_entity_family": admission["g01b"]["family_identities"]["topic_entity_family"],
                "pilot02_creative_premise_family": g03b["creative_premise_family_id"],
                "pilot01_candidate_identity": pilot01["candidate_identity"],
                "pilot01_candidate_role": pilot01["evidence_role"],
                "pilot01_positive_eligible": False,
                "finding": "PASS_NO_DUPLICATE_REVISION_SIBLING_SAME_EVENT_OR_CREATIVE_FAMILY_OVERLAP",
            },
            "dominant_positive_family_count": 1,
            "target_positive_candidates": [g03b["candidate_identity"]],
            "excluded_from_positive_count": [pilot01["candidate_identity"]],
            "obligation_family_confound": "UNRESOLVED_SINGLE_POSITIVE_CANDIDATE_PERFECTLY_CONFOUNDS_TARGET_WITH_SUCCESSOR_OBLIGATION_FAMILY",
            "weak_nonsemantic_classifier": {
                "status": "INSUFFICIENT_STATISTICAL_POWER",
                "reason": "A one-positive pool cannot distinguish semantic recovery from family/template correlation without leakage or overfitting.",
                "training_or_tuning_performed": False,
            },
            "required_to_close": [
                "additional independently acquired and constructed dominant-positive source families",
                "mechanism-confusable negatives with family isolation",
                "cross-obligation and cross-topic balancing",
                "pool audit before any curriculum visibility",
            ],
            "verdict": "POOL_PENDING_INSUFFICIENT_INDEPENDENT_POSITIVE_FAMILIES",
        },
        "contamination": {
            "development_partition_only": True,
            "pilot01_surface_or_construction_reuse": False,
            "cross_partition_family_overlap": False,
            "blind_family_or_metadata_access": False,
            "blind_holdout_tuning": False,
            "historical_surface_tuning": False,
            "owner_preference_tuning": False,
            "candidate_model_visibility": False,
            "training_visibility": False,
            "verdict": "PASS_CLEAN_DEVELOPMENT_DIAGNOSTIC",
        },
        "g03c_verdict": "CANDIDATE_SHORTCUT_PASS_AND_POOL_PENDING",
        "candidate_disposition_effect": "NOT_YET_ELIGIBLE_FOR_CURRICULUM_OR_OWNER_FREEZE_POOL_G03C_REMAINS_OPEN",
        "performed": {
            "romanian_naturalness_review": False,
            "voice_review": False,
            "owner_review": False,
            "candidate_repair": False,
            "candidate_rewrite": False,
            "candidate_regeneration": False,
            "training": False,
            "runtime_integration": False,
            "production_routing": False,
        },
        "authority_matrix": {
            key: False
            for key in (
                "romanian_naturalness_review",
                "voice_review",
                "owner_review",
                "candidate_repair",
                "candidate_rewrite",
                "candidate_regeneration",
                "training",
                "runtime_integration",
                "production_routing",
                "curriculum_promotion",
            )
        },
    }
    diagnostic = {
        **diagnostic_core,
        "g03c_diagnostic_identity": seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G03C_DIAGNOSTIC_V1", diagnostic_core),
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot02-candidate01-g03c-receipt-v1",
        "schema_version": "1.0.0",
        "candidate_identity": diagnostic_core["candidate_identity"],
        "candidate_raw_sha256": diagnostic_core["candidate_raw_sha256"],
        "g03b_receipt_identity": diagnostic_core["g03b_receipt_identity"],
        "g03c_diagnostic_identity": diagnostic["g03c_diagnostic_identity"],
        "g03c_verdict": diagnostic_core["g03c_verdict"],
        "candidate_level_verdict": diagnostic_core["candidate_level"]["verdict"],
        "pool_level_verdict": diagnostic_core["pool_level"]["verdict"],
        "contamination_verdict": diagnostic_core["contamination"]["verdict"],
        "candidate_bytes_modified": False,
        "blind_holdout_content_accessed": False,
        "next_action": "ACQUIRE_AND_REVIEW_ADDITIONAL_INDEPENDENT_DEVELOPMENT_FAMILIES_BEFORE_POOL_CLOSURE",
        "authority_matrix": diagnostic_core["authority_matrix"],
    }
    receipt = {
        **receipt_core,
        "g03c_receipt_identity": seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G03C_RECEIPT_V1", receipt_core),
    }
    for name, value in (
        ("humor-mechanics-batch2-development-pilot02-candidate01-g03c-diagnostic-v1.json", diagnostic),
        ("humor-mechanics-batch2-development-pilot02-candidate01-g03c-receipt-v1.json", receipt),
    ):
        (ART / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps({
        "g03c_verdict": receipt["g03c_verdict"],
        "g03c_diagnostic_identity": diagnostic["g03c_diagnostic_identity"],
        "g03c_receipt_identity": receipt["g03c_receipt_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

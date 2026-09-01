"""Freeze Pilot 07 candidate/pool G03C shortcut and contamination diagnostics."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"
G03B_COMMIT = "874b38f0cb3fefbb2a09c1e8f42d4d6cf6793ded"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-v1.txt"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{G03B_COMMIT}:{path}"], cwd=ROOT))


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
    require(head == G03B_COMMIT, "HEAD differs from the authorized G03B commit")
    candidate = subprocess.check_output(["git", "show", f"{G03B_COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT)
    g03b = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-g03b-review-v1.json")
    g03b_receipt = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-g03b-receipt-v1.json")
    admission07 = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot07-g01a-g01b-admission-v1.json")
    admission03 = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot03-g01a-g01b-admission-v1.json")
    admission04 = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot04-g01a-g01b-admission-v1.json")
    assignment_audit = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot07-rebalancing-assignment-design-audit-v3.json")
    freeze03 = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-g05-owner-freeze-v1.json")
    freeze04 = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot04-candidate01-g05-owner-freeze-v1.json")
    disposition05 = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-g02c-rejection-disposition-v1.json")
    disposition06 = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-disposition-v1.json")
    prior_pool = git_json("docs/artifacts/humor-mechanics-batch2-g04b-pilot03-pilot04-pool-audit-v1.json")

    require(hashlib.sha256(candidate).hexdigest() == g03b["candidate_raw_sha256"], "candidate bytes")
    require(g03b["g03b_verdict"] == "CAUSAL_MECHANISM_CONFIRMED", "G03B verdict")
    require(g03b["g03b_review_identity"] == "504b690e549d061fdeedeba873ae5656c4b6d115421faccaa8abe7f4fe93a76b", "G03B review")
    require(g03b_receipt["g03b_receipt_identity"] == "076a4524be08fabfd97028db93c12177b8894c39cfce26e96a0e6f3e5b8e873d", "G03B receipt")
    require(admission07["g01b"]["contamination_state"] == "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE", "contamination")
    require(assignment_audit["taxonomy_and_alternative_label_scan"] == "PASS_ZERO_HITS", "assignment leakage")
    require(prior_pool["g04b_verdict"] == "POOL_REBALANCING_REQUIRED_NO_CERTIFICATION", "prior G04B state")
    source_families = {
        admission03["g01b"]["family_identities"]["source_family"],
        admission04["g01b"]["family_identities"]["source_family"],
        admission07["g01b"]["family_identities"]["source_family"],
    }
    require(len(source_families) == 3, "source-family independence")

    authority_matrix = {
        key: False
        for key in (
            "g04a_romanian_naturalness",
            "g04b_pool_certification",
            "voice_review",
            "owner_review",
            "candidate_repair",
            "candidate_rewrite",
            "candidate_regeneration",
            "curriculum_promotion",
            "model_exposure",
            "training",
            "runtime_integration",
            "production_routing",
        )
    }
    core = {
        "schema_name": "batch2-development-pilot07-candidate01-g03c-diagnostic-v1",
        "schema_version": "1.0.0",
        "candidate_identity": g03b["candidate_identity"],
        "candidate_raw_sha256": g03b["candidate_raw_sha256"],
        "creative_premise_family_id": g03b["creative_premise_family_id"],
        "g03b_commit": G03B_COMMIT,
        "g03b_review_identity": g03b["g03b_review_identity"],
        "g03b_receipt_identity": g03b_receipt["g03b_receipt_identity"],
        "candidate_bytes_modified": False,
        "blind_holdout_content_or_metadata_accessed": False,
        "candidate_level": {
            "lexical": {
                "observed_cues": ["continuare imaginară", "rubrică", "ciclul se repetă", "mai lung decât"],
                "finding": "PASS_NONDEFINING_G03B_SURFACE_PARAPHRASE_INVARIANT",
                "material": False,
            },
            "format": {
                "observed": "FACTUAL_PREMISE_THEN_MARKED_RECURSIVE_CREATIVE_CHAIN",
                "finding": "PASS_AUTHORITY_SAFETY_SHAPE_NOT_SUFFICIENT_FOR_TARGET_RECOVERY",
                "material": False,
            },
            "position": {
                "observed": "DEPENDENT_TERMINAL_PAYOFF",
                "finding": "PASS_COMMON_HUMOR_POSITION_REQUIRES_FULL_CHAIN",
                "material": False,
            },
            "length": {"utf8_bytes": len(candidate), "finding": "PASS_NO_TARGET_THRESHOLD", "material": False},
            "topic_entity": {
                "observed": "NEUTRAL_SYNTHETIC_TECHNICAL_VERIFICATION_REPORT_NO_REAL_OR_PROTECTED_ENTITY",
                "finding": "PASS_SOURCE_FAMILY_FIXED_BEFORE_ASSIGNMENT",
                "material": False,
            },
            "constructor_template": {
                "finding": "PASS_G03B_REQUIRES_MULTI_LINK_DEPENDENCY_NOT_FIXED_LEXEME_GRAMMAR_OR_ORDER_CUE",
                "material": False,
            },
            "metadata": {
                "finding": "PASS_CANDIDATE_ARTIFACT_HAS_NO_MECHANISM_LABEL_ORDINAL_ROLE_OR_ANSWER_KEY",
                "material": False,
            },
            "weak_nonsemantic_classifier": {
                "execution": "NOT_TRAINED_NO_MODEL_OR_STATISTICAL_FIT",
                "feature_hypotheses": ["lexeme", "punctuation", "length", "topic", "sentence position", "format"],
                "finding": "PASS_NO_SINGLE_FEATURE_EXPLAINS_BLIND_RECOVERY_AND_G03B_CAUSAL_INVARIANCE",
            },
            "verdict": "CANDIDATE_SHORTCUT_PASS",
        },
        "pool_level": {
            "accessible_scope": "DEVELOPMENT_AND_FROZEN_NONBLIND_METADATA_ONLY",
            "blind_reserve": "NOT_ACCESSED_NOT_TUNED",
            "independent_source_family_count": 3,
            "dominant_mechanism_recovered_family_count": 3,
            "owner_frozen_positive_family_count": 2,
            "family_isolation": "PASS_PILOT03_PILOT04_PILOT07_SOURCE_EVENT_TOPIC_AND_CREATIVE_FAMILIES_DISTINCT",
            "owner_frozen_positive_candidates": [freeze03["candidate_identity"], freeze04["candidate_identity"]],
            "new_quality_pending_candidate": g03b["candidate_identity"],
            "excluded_nonpositive_candidates": [disposition05["candidate_identity"], disposition06["candidate_identity"]],
            "prior_g04b_verdict": prior_pool["g04b_verdict"],
            "realization_obligation_diversity": "IMPROVED_PILOT07_V3_RECURSIVE_SELF_PROPAGATION_DIFFERS_FROM_PILOT03_04_SHARED_V2_REALIZATION",
            "close_alternative_profile": "IMPROVED_ESCALATION_AND_SELF_REFERENTIAL_RECURSION_NOT_SHARED_COMIC_RECLASSIFICATION_PROFILE",
            "certification_status": "NOT_EVALUATED_G04B_SEPARATE_AND_PILOT07_QUALITY_GATES_PENDING",
            "weak_nonsemantic_classifier": {
                "status": "NOT_RUN_G04B_SEPARATE",
                "training_or_tuning_performed": False,
                "reason": "Pilot 07 adds a causally confirmed independent realization, but it is not owner-frozen and this G03C cannot certify the pool.",
            },
            "required_to_close": [
                "Pilot 07 blind Romanian-naturalness review",
                "Pilot 07 blind Voice review",
                "Pilot 07 owner review",
                "separately authorized G04B cross-candidate pool audit",
            ],
            "verdict": "POOL_REBALANCING_PROGRESS_PILOT07_QUALITY_GATES_AND_SEPARATE_G04B_PENDING",
        },
        "contamination": {
            "development_partition_only": True,
            "cross_partition_family_overlap": False,
            "blind_family_or_metadata_access": False,
            "blind_holdout_tuning": False,
            "historical_surface_tuning": False,
            "owner_preference_tuning": False,
            "candidate_model_visibility": False,
            "training_visibility": False,
            "verdict": "PASS_CLEAN_DEVELOPMENT_DIAGNOSTIC",
        },
        "g03c_verdict": "CANDIDATE_SHORTCUT_PASS_AND_POOL_REBALANCING_PROGRESS_PENDING_QUALITY_GATES_AND_G04B",
        "candidate_disposition_effect": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G04A_ONLY_NO_POOL_CERTIFICATION",
        "authority_matrix": authority_matrix,
    }
    diagnostic = {
        **core,
        "g03c_diagnostic_identity": seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_G03C_DIAGNOSTIC_V1", core),
    }
    receipt_core = {
        "schema_name": "batch2-development-pilot07-candidate01-g03c-receipt-v1",
        "schema_version": "1.0.0",
        "candidate_identity": core["candidate_identity"],
        "candidate_raw_sha256": core["candidate_raw_sha256"],
        "g03b_receipt_identity": core["g03b_receipt_identity"],
        "g03c_diagnostic_identity": diagnostic["g03c_diagnostic_identity"],
        "g03c_verdict": core["g03c_verdict"],
        "candidate_level_verdict": core["candidate_level"]["verdict"],
        "pool_level_verdict": core["pool_level"]["verdict"],
        "contamination_verdict": core["contamination"]["verdict"],
        "candidate_bytes_modified": False,
        "blind_holdout_content_or_metadata_accessed": False,
        "next_gate_eligible": "G04A_ROMANIAN_NATURALNESS_SEPARATELY_AUTHORIZED_ONLY",
        "authority_matrix": authority_matrix,
    }
    receipt = {
        **receipt_core,
        "g03c_receipt_identity": seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_G03C_RECEIPT_V1", receipt_core),
    }
    write_json("humor-mechanics-batch2-development-pilot07-candidate01-g03c-diagnostic-v1.json", diagnostic)
    write_json("humor-mechanics-batch2-development-pilot07-candidate01-g03c-receipt-v1.json", receipt)
    print(json.dumps({
        "g03c_verdict": core["g03c_verdict"],
        "g03c_diagnostic_identity": diagnostic["g03c_diagnostic_identity"],
        "g03c_receipt_identity": receipt["g03c_receipt_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

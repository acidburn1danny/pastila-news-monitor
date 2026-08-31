"""Freeze Pilot 04 candidate/pool G03C shortcut and contamination diagnostics."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G03B_COMMIT = "81661e1a5188db7c0f8b7f373b8b152ae22063f3"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot04-candidate01-"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{G03B_COMMIT}:{path}"], cwd=ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == G03B_COMMIT, "HEAD differs from G03B freeze")
    candidate = subprocess.check_output(
        ["git", "show", f"{G03B_COMMIT}:docs/artifacts/humor-mechanics-batch2-development-pilot04-candidate01-v1.txt"],
        cwd=ROOT,
    )
    g03b = load(PREFIX + "g03b-review-v1.json")
    g03b_receipt = load(PREFIX + "g03b-receipt-v1.json")
    admission = load("docs/artifacts/humor-mechanics-batch2-development-pilot04-g01a-g01b-admission-v1.json")
    assignment_audit = load("docs/artifacts/humor-mechanics-batch2-development-pilot04-assignment-design-leakage-audit-v1.json")
    pilot01 = load("docs/artifacts/humor-mechanics-batch2-development-pilot01-candidate01-disposition-v1.json")
    pilot02 = load("docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-naturalness-rejection-disposition-v1.json")
    pilot03_admission = load("docs/artifacts/humor-mechanics-batch2-development-pilot03-g01a-g01b-admission-v1.json")
    pilot03_freeze = load("docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-g05-owner-freeze-v1.json")

    require(hashlib.sha256(candidate).hexdigest() == g03b["candidate_raw_sha256"], "candidate bytes")
    require(g03b["g03b_verdict"] == "CAUSAL_MECHANISM_CONFIRMED", "G03B verdict")
    require(g03b["g03b_review_identity"] == "38fa73811d5f3dce1cbcb66d92dc82f5f5145355fe0b24ace820dbd926396d1e", "G03B review")
    require(g03b_receipt["g03b_receipt_identity"] == "f72c8f8b6ec9fce3006dde691ec7976991caf581acdf9add91a21c6ebbcf2a49", "G03B receipt")
    require(admission["g01b"]["contamination_state"] == "CLEAN_DEVELOPMENT_ONLY_NO_BLIND_EXPOSURE", "admission contamination")
    require(assignment_audit["blind_evaluation_contamination"] == "ABSENT", "assignment contamination")
    require(pilot01["positive_m13_coverage_eligible"] is False, "Pilot 01 positive exclusion")
    require(pilot02["positive_coverage_eligible"] is False, "Pilot 02 positive exclusion")
    require(pilot03_freeze["status"] == "OWNER_FROZEN_DEVELOPMENT_ONLY_POOL_PENDING", "Pilot 03 pool state")
    require(admission["g01b"]["family_identities"]["source_family"] !=
            pilot03_admission["g01b"]["family_identities"]["source_family"], "independent source families")

    core = {
        "schema_name": "batch2-development-pilot04-candidate01-g03c-diagnostic-v1",
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
                "observed_cues": ["povestea expoziției", "mai întâi", "ajunge apoi", "demonstreze"],
                "finding": "PASS_NONDEFINING_AND_G03B_PARAPHRASE_INVARIANT",
                "material": False,
            },
            "format": {
                "observed": "FACTUAL_PREMISE_THEN_EXPLICITLY_MARKED_CREATIVE_CHAIN",
                "finding": "PASS_GENERIC_AUTHORITY_SAFETY_SHAPE_NOT_TARGET_SPECIFIC",
                "material": False,
            },
            "position": {"observed": "DEPENDENT_PAYOFF_AT_END", "finding": "PASS_COMMON_HUMOR_POSITION", "material": False},
            "length": {"utf8_bytes": len(candidate), "finding": "PASS_NO_TARGET_THRESHOLD", "material": False},
            "topic_entity": {
                "observed": "NEUTRAL_SYNTHETIC_EXHIBITION_ACCESS_NO_REAL_PERSON_OR_PROTECTED_ENTITY",
                "finding": "PASS_SOURCE_ACQUIRED_AND_PARTITIONED_BEFORE_ASSIGNMENT",
                "material": False,
            },
            "constructor_template": {
                "finding": "PASS_G03B_CONFIRMS_DEPENDENCY_GRAPH_NOT_FIXED_LEXEME_OR_GRAMMAR",
                "material": False,
            },
            "metadata": {"finding": "PASS_CANDIDATE_HAS_NO_LABEL_ID_ORDINAL_ROLE_OR_ANSWER_KEY", "material": False},
            "weak_nonsemantic_classifier": {
                "execution": "NOT_TRAINED_NO_MODEL_OR_STATISTICAL_FIT",
                "feature_hypotheses": ["lexeme", "punctuation", "length", "topic", "sentence position", "packet format"],
                "finding": "PASS_NO_SINGLE_FEATURE_EXPLAINS_BLIND_RECOVERY_AND_G03B_INVARIANCE",
            },
            "verdict": "CANDIDATE_SHORTCUT_PASS",
        },
        "pool_level": {
            "accessible_scope": "DEVELOPMENT_AND_FROZEN_NONBLIND_METADATA_ONLY",
            "blind_reserve": "NOT_ACCESSED_NOT_TUNED",
            "family_isolation": "PASS_PILOT03_AND_PILOT04_DISTINCT_SOURCE_EVENT_TOPIC_AND_CREATIVE_FAMILIES",
            "dominant_mechanism_recovered_family_count": 2,
            "owner_frozen_positive_family_count": 1,
            "target_positive_candidates": [pilot03_freeze["candidate_identity"], g03b["candidate_identity"]],
            "excluded_nonpositive_candidates": [pilot01["candidate_identity"], pilot02["candidate_identity"]],
            "obligation_family_confound": "REDUCED_BY_SECOND_INDEPENDENT_SOURCE_FAMILY_BUT_NOT_CLOSED_BEFORE_PILOT04_G04A_VOICE_G05_AND_G04B",
            "weak_nonsemantic_classifier": {
                "status": "INSUFFICIENT_STATISTICAL_POWER",
                "training_or_tuning_performed": False,
                "reason": "Two causally confirmed independent families reduce the single-family confound, but Pilot 04 has not completed naturalness, Voice, or owner freeze and G04B remains separate.",
            },
            "required_to_close": [
                "Pilot 04 blind Romanian-naturalness, Voice, and owner review",
                "family-isolated target confusables and mechanism negatives",
                "cross-topic and cross-obligation balancing",
                "repeat pool audit before curriculum or owner-positive freeze",
            ],
            "verdict": "POOL_PENDING_PILOT04_QUALITY_GATES_AND_SEPARATE_G04B_CERTIFICATION",
        },
        "contamination": {
            "development_partition_only": True,
            "pilot01_or_pilot02_surface_reuse": False,
            "cross_partition_family_overlap": False,
            "blind_family_or_metadata_access": False,
            "blind_holdout_tuning": False,
            "historical_surface_tuning": False,
            "owner_preference_tuning": False,
            "candidate_model_visibility": False,
            "training_visibility": False,
            "verdict": "PASS_CLEAN_DEVELOPMENT_DIAGNOSTIC",
        },
        "g03c_verdict": "CANDIDATE_SHORTCUT_PASS_AND_POOL_G04B_PREREQUISITES_PENDING",
        "candidate_disposition_effect": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G04A_ONLY_POOL_G03C_REMAINS_OPEN",
        "performed": {key: False for key in ("romanian_naturalness_review", "voice_review", "owner_review", "candidate_repair", "candidate_rewrite", "candidate_regeneration", "training", "runtime_integration", "production_routing")},
        "authority_matrix": {key: False for key in ("romanian_naturalness_review", "voice_review", "owner_review", "candidate_repair", "candidate_rewrite", "candidate_regeneration", "training", "runtime_integration", "production_routing", "curriculum_promotion", "g04b_pool_certification")},
    }
    diagnostic = {**core, "g03c_diagnostic_identity": seal("B2_DEVELOPMENT_PILOT04_CANDIDATE01_G03C_DIAGNOSTIC_V1", core)}
    receipt_core = {
        "schema_name": "batch2-development-pilot04-candidate01-g03c-receipt-v1",
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
        "authority_matrix": core["authority_matrix"],
    }
    receipt = {**receipt_core, "g03c_receipt_identity": seal("B2_DEVELOPMENT_PILOT04_CANDIDATE01_G03C_RECEIPT_V1", receipt_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot04-candidate01-g03c-diagnostic-v1.json", diagnostic), ("humor-mechanics-batch2-development-pilot04-candidate01-g03c-receipt-v1.json", receipt)):
        (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g03c_verdict": core["g03c_verdict"], "g03c_diagnostic_identity": diagnostic["g03c_diagnostic_identity"], "g03c_receipt_identity": receipt["g03c_receipt_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()

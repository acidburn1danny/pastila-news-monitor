"""Audit the bounded Pilot 03/04 owner-frozen DEVELOPMENT pool at G04B."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
PILOT03_COMMIT = "4395f3300ca2f59ce1f76b4e7abccd3ff0a587e9"
PILOT04_COMMIT = "96f1632be005c3b85079c7bfca488fe903bc4966"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def raw(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == PILOT04_COMMIT,
            "HEAD differs from Pilot 04 owner-freeze commit")
    p3_prefix = "docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-"
    p4_prefix = "docs/artifacts/humor-mechanics-batch2-development-pilot04-candidate01-"
    p3_freeze = load(PILOT03_COMMIT, p3_prefix + "g05-owner-freeze-v1.json")
    p4_freeze = load(PILOT04_COMMIT, p4_prefix + "g05-owner-freeze-v1.json")
    p3_admission = load(PILOT03_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot03-g01a-g01b-admission-v1.json")
    p4_admission = load(PILOT04_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot04-g01a-g01b-admission-v1.json")
    p3_g03 = load(PILOT03_COMMIT, p3_prefix + "g03-receipt-v1.json")
    p4_g03 = load(PILOT04_COMMIT, p4_prefix + "g03-receipt-v1.json")
    p3_g03b = load(PILOT03_COMMIT, p3_prefix + "g03b-receipt-v1.json")
    p4_g03b = load(PILOT04_COMMIT, p4_prefix + "g03b-receipt-v1.json")
    p3 = raw(PILOT03_COMMIT, p3_prefix + "v1.txt")
    p4 = raw(PILOT04_COMMIT, p4_prefix + "v1.txt")
    require(p3_freeze["g05_owner_freeze_identity"] == "b85401270daeb2025d79bc13d1d002e3d439171de72aef77f87ad5d7395b814b", "Pilot 03 freeze")
    require(p4_freeze["g05_owner_freeze_identity"] == "9ccf9f8dc0dd4857e987cbc0dfc13a590573036d83d53d990d31566098d71cd8", "Pilot 04 freeze")
    require(p3_freeze["status"] == "OWNER_FROZEN_DEVELOPMENT_ONLY_POOL_PENDING", "Pilot 03 status")
    require(p4_freeze["status"] == "OWNER_FROZEN_DEVELOPMENT_ONLY_G04B_PENDING", "Pilot 04 status")
    require(hashlib.sha256(p3).hexdigest() == p3_freeze["candidate_raw_sha256"], "Pilot 03 bytes")
    require(hashlib.sha256(p4).hexdigest() == p4_freeze["candidate_raw_sha256"], "Pilot 04 bytes")
    require(p3_g03["reconciliation_classification"] == p4_g03["reconciliation_classification"] == "TARGET_RECOVERED_DOMINANT", "dominant recovery")
    require(p3_g03b["g03b_verdict"] == p4_g03b["g03b_verdict"] == "CAUSAL_MECHANISM_CONFIRMED", "causality")
    f3, f4 = p3_admission["g01b"]["family_identities"], p4_admission["g01b"]["family_identities"]
    for key in ("source_family", "event_family", "authority_family", "topic_entity_family", "revision_family", "family_closure"):
        require(f3[key] != f4[key], f"family collision {key}")
    require(p3_g03["creative_premise_family_id"] != p4_g03["creative_premise_family_id"], "creative-family collision")

    t3, t4 = p3.decode("utf-8").rstrip("\n"), p4.decode("utf-8").rstrip("\n")
    structural_features = {
        "two_sentence_fact_then_creative_chain": [len(re.split(r"(?<=\.)\s+", text)) == 2 for text in (t3, t4)],
        "integrated_story_marker": ["În povestea" in text for text in (t3, t4)],
        "semicolon_two_step_realization": [";" in text for text in (t3, t4)],
        "ajunge_landing_lexeme": ["ajunge" in text.lower() for text in (t3, t4)],
        "same_governance_v2_obligation_family": [True, True],
    }
    require(all(all(values) for values in structural_features.values()), "expected shared realization evidence")
    core = {
        "schema_name": "batch2-g04b-pilot03-pilot04-cross-candidate-pool-audit-v1",
        "schema_version": "1.0.0",
        "bounded_pool": [
            {"pilot": "PILOT03", "commit": PILOT03_COMMIT, "owner_freeze_identity": p3_freeze["g05_owner_freeze_identity"],
             "candidate_identity": p3_freeze["candidate_identity"], "candidate_raw_sha256": hashlib.sha256(p3).hexdigest()},
            {"pilot": "PILOT04", "commit": PILOT04_COMMIT, "owner_freeze_identity": p4_freeze["g05_owner_freeze_identity"],
             "candidate_identity": p4_freeze["candidate_identity"], "candidate_raw_sha256": hashlib.sha256(p4).hexdigest()},
        ],
        "candidate_bytes_modified": False,
        "family_source_topic_entity_payoff_diversity": {
            "verdict": "PASS",
            "source_event_authority_topic_revision_and_creative_families_distinct": True,
            "topic_contrast": "PARCEL_CONTENT_AND_INVENTORY_VS_EXHIBITION_ACCESS_CONTROL",
            "payoff_contrast": "OPENING_RECLASSIFIED_AS_INVENTORY_ITEM_VS_EXCLUSION_RECLASSIFIED_AS_RULE_DEMONSTRATION",
        },
        "structural_realization_diversity": {
            "verdict": "FAIL_INSUFFICIENT_DIVERSITY",
            "shared_features": structural_features,
            "finding": "Both positives instantiate the same obligation family with a highly similar fact-then-story, semicolon, two-step, ajunge-landing shape.",
        },
        "positive_contrast_difficulty": {
            "verdict": "FAIL_INSUFFICIENT_CROSS_FAMILY_CONTRAST",
            "shared_supporting_mechanism": "COMIC_RECLASSIFICATION",
            "finding": "Both dominant positives use comic reclassification as the supporting payoff and provide no family-isolated positive realization with a different close-alternative profile.",
        },
        "no_nonsemantic_label_predictability": {
            "verdict": "FAIL_NOT_ESTABLISHED",
            "weak_classifier_training_performed": False,
            "reason": "With two positives sharing obligation, sentence shape, story marker, semicolon chain, and landing lexeme, semantics cannot be separated from construction-family cues.",
        },
        "contamination": {
            "development_only": True, "blind_reserve_accessed": False, "cross_partition_overlap": False,
            "candidate_or_owner_preference_tuning": False, "model_or_training_visibility": False,
            "verdict": "PASS_CLEAN_BOUNDED_DEVELOPMENT_POOL",
        },
        "g04b_verdict": "POOL_REBALANCING_REQUIRED_NO_CERTIFICATION",
        "certification_granted": False,
        "required_before_reaudit": [
            "AT_LEAST_ONE_ADDITIONAL_INDEPENDENT_OWNER_FROZEN_DOMINANT_POSITIVE_FAMILY",
            "DIFFERENT_LABEL_BLIND_REALIZATION_OR_OBLIGATION_FAMILY_WITHOUT_TARGET_LEAKAGE",
            "DIFFERENT_CLOSE_ALTERNATIVE_AND_SUPPORTING_MECHANISM_PROFILE",
            "FAMILY_ISOLATED_CONFUSABLE_OR_MECHANISM_NEGATIVE_EVIDENCE",
            "REPEAT_G04B_WITHOUT_QUOTA_FILL",
        ],
        "authority_matrix": {key: False for key in (
            "candidate_repair", "candidate_rewrite", "candidate_regeneration", "source_acquisition", "construction",
            "curriculum_promotion", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    audit = {**core, "g04b_pool_audit_identity": seal("B2_G04B_PILOT03_PILOT04_POOL_AUDIT_V1", core)}
    receipt_core = {
        "schema_name": "batch2-g04b-pilot03-pilot04-pool-audit-receipt-v1", "schema_version": "1.0.0",
        "g04b_pool_audit_identity": audit["g04b_pool_audit_identity"], "g04b_verdict": core["g04b_verdict"],
        "certification_granted": False, "candidate_bytes_modified": False,
        "contamination_verdict": core["contamination"]["verdict"], "next_action_requires_separate_authority": True,
        "authority_matrix": core["authority_matrix"],
    }
    receipt = {**receipt_core, "g04b_receipt_identity": seal("B2_G04B_PILOT03_PILOT04_POOL_AUDIT_RECEIPT_V1", receipt_core)}
    for name, value in (("humor-mechanics-batch2-g04b-pilot03-pilot04-pool-audit-v1.json", audit),
                        ("humor-mechanics-batch2-g04b-pilot03-pilot04-pool-audit-receipt-v1.json", receipt)):
        (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g04b_verdict": core["g04b_verdict"], "g04b_pool_audit_identity": audit["g04b_pool_audit_identity"],
                      "g04b_receipt_identity": receipt["g04b_receipt_identity"], "certification_granted": False}, sort_keys=True))


if __name__ == "__main__":
    main()

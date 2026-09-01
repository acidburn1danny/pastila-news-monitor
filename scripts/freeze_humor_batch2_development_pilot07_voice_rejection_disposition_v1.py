"""Freeze Pilot 07 as non-positive DEVELOPMENT Voice-rejection evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"
VOICE_COMMIT = "92631597b63e7fa420b265ee0e55038108608cf2"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-v1.txt"
VOICE_REVIEW_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-voice-review-v1.json"
VOICE_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-voice-receipt-v1.json"
G03_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-g03-receipt-v1.json"
G03B_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-g03b-receipt-v1.json"
G03C_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-g03c-receipt-v1.json"
G04A_RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-g04a-naturalness-receipt-v1.json"
OUTPUT = ARTIFACTS / "humor-mechanics-batch2-development-pilot07-candidate01-voice-rejection-disposition-v1.json"


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{VOICE_COMMIT}:{path}"], cwd=ROOT)


def git_json(path: str) -> dict[str, Any]:
    return json.loads(git_bytes(path))


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    require(not OUTPUT.exists(), "disposition already exists")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == VOICE_COMMIT, "HEAD differs from the authorized Voice commit")
    candidate = git_bytes(CANDIDATE_PATH)
    candidate_blob = subprocess.check_output(
        ["git", "rev-parse", f"{VOICE_COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT, text=True
    ).strip()
    voice_review = git_json(VOICE_REVIEW_PATH)
    voice_receipt = git_json(VOICE_RECEIPT_PATH)
    g03 = git_json(G03_RECEIPT_PATH)
    g03b = git_json(G03B_RECEIPT_PATH)
    g03c = git_json(G03C_RECEIPT_PATH)
    g04a = git_json(G04A_RECEIPT_PATH)

    require(hashlib.sha256(candidate).hexdigest() == voice_receipt["candidate_raw_sha256"], "candidate hash")
    require(candidate_blob == "345829c569ae87d350a30158e026c52371e3c560", "candidate Git blob")
    require(voice_receipt["voice_verdict"] == "VOICE_REJECTED", "Voice verdict")
    require(voice_review["voice_review_identity"] == "e15a9b8168362bbc3573744592e31112a165fa60bd45e33b1fe3cba541db5168", "Voice review")
    require(voice_receipt["voice_receipt_identity"] == "3e5f4a580f95c9eab44928e3677ad9e62e50348c0eb60a542d0844b8c3e0a467", "Voice receipt")
    require(voice_review["stable_rejection_reasons"] == ["CANNED_CROSS_PILOT_CREATIVE_TRANSITION_REUSE"], "stable rejection")

    authority_matrix = {
        key: False
        for key in (
            "owner_review",
            "owner_positive_review",
            "g04b_pool_certification",
            "candidate_repair",
            "candidate_rewrite",
            "candidate_regeneration",
            "additional_construction",
            "curriculum_promotion",
            "model_exposure",
            "training",
            "runtime_integration",
            "production_routing",
        )
    }
    core = {
        "schema_name": "batch2-development-pilot07-candidate01-voice-rejection-disposition-v1",
        "schema_version": "1.0.0",
        "candidate_identity": voice_receipt["candidate_identity"],
        "candidate_raw_sha256": voice_receipt["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": candidate_blob,
        "creative_premise_family_id": g03["creative_premise_family_id"],
        "voice_commit": VOICE_COMMIT,
        "partition": "DEVELOPMENT",
        "disposition": "DEVELOPMENT_NONPOSITIVE_VOICE_REJECTION_EVIDENCE",
        "evidence_role": "NONPOSITIVE_VOICE_TEMPLATE_REJECTION",
        "visibility": "NON_MODEL_VISIBLE",
        "bound_lineage": {
            "g03_validity": g03["g03_validity_status"],
            "g03_reconciliation": g03["reconciliation_classification"],
            "g03_receipt_identity": g03["g03_receipt_identity"],
            "g03b_verdict": g03b["g03b_verdict"],
            "g03b_receipt_identity": g03b["g03b_receipt_identity"],
            "g03c_verdict": g03c["g03c_verdict"],
            "g03c_receipt_identity": g03c["g03c_receipt_identity"],
            "g04a_verdict": g04a["g04a_verdict"],
            "g04a_receipt_identity": g04a["g04a_receipt_identity"],
            "voice_verdict": voice_receipt["voice_verdict"],
            "voice_review_identity": voice_review["voice_review_identity"],
            "voice_receipt_identity": voice_receipt["voice_receipt_identity"],
        },
        "stable_rejection_reasons": voice_review["stable_rejection_reasons"],
        "preserved_voice_findings": {
            "tonal_coherence": voice_review["findings"]["tonal_coherence"]["verdict"],
            "sentence_movement": voice_review["findings"]["sentence_movement"]["verdict"],
            "payoff_economy": voice_review["findings"]["payoff_economy"]["verdict"],
            "canned_transition": voice_review["findings"]["no_canned_opening_or_transition"]["verdict"],
            "historical_wording_copy": voice_review["findings"]["no_historical_wording_copy"]["verdict"],
            "overall_voice": voice_review["findings"]["overall_voice_compatibility"]["verdict"],
        },
        "positive_coverage_eligible": False,
        "owner_review_eligible": False,
        "g04b_pool_certification_eligible": False,
        "curriculum_candidate_eligible": False,
        "training_eligible": False,
        "runtime_eligible": False,
        "production_eligible": False,
        "permitted_future_source_only_diagnostics": [
            "CROSS_PILOT_CREATIVE_MARKER_ROOT_CAUSE_ANALYSIS",
            "CONSTRUCTOR_TEMPLATE_GOVERNANCE_ANALYSIS",
            "VOICE_SHORTCUT_AND_TEMPLATE_CONTAMINATION_ANALYSIS",
            "CREATIVE_MARKING_DIVERSITY_GOVERNANCE_REMEDIATION",
        ],
        "candidate_bytes_modified": False,
        "existing_identities_modified": False,
        "frozen_findings_reinterpreted": False,
        "authority_matrix": authority_matrix,
    }
    disposition = {
        **core,
        "disposition_identity": seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_VOICE_REJECTION_DISPOSITION_V1", core),
    }
    OUTPUT.write_text(
        json.dumps(disposition, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "disposition": disposition["disposition"],
        "disposition_identity": disposition["disposition_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

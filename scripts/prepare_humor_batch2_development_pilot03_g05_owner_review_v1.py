"""Prepare the decision-ready G05 owner-review packet for Pilot 03 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
VOICE_COMMIT = "2b1c2d50ee7b578e81b934590e17b5c2e480dde2"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot03-candidate01-"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{VOICE_COMMIT}:{path}"], cwd=ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == VOICE_COMMIT, "HEAD differs from Voice freeze")
    candidate = subprocess.check_output(["git", "show", f"{VOICE_COMMIT}:{PREFIX}v1.txt"], cwd=ROOT)
    voice = load(PREFIX + "voice-receipt-v1.json")
    naturalness = load(PREFIX + "g04a-naturalness-receipt-v1.json")
    g03c = load(PREFIX + "g03c-receipt-v1.json")
    g03 = load(PREFIX + "g03-receipt-v1.json")
    require(hashlib.sha256(candidate).hexdigest() == voice["candidate_raw_sha256"], "candidate bytes")
    require(voice["voice_verdict"] == "VOICE_PASS", "Voice verdict")
    require(voice["voice_review_identity"] == "7c0436af16995fe07f1c6824ee196ce51982a758e63f0e3d9c40f9f9de971dfb", "Voice review")
    require(voice["voice_receipt_identity"] == "a87d71df2a945f46ad6acb2ed3c8eddbe16c8c6c3e9d79557716e4a402834f11", "Voice receipt")
    require(naturalness["g04a_verdict"] == "ROMANIAN_NATURALNESS_PASS", "G04A")
    require(g03c["pool_level_verdict"] == "POOL_PENDING_INSUFFICIENT_INDEPENDENT_POSITIVE_FAMILIES", "pool status")
    require(g03["reconciliation_classification"] == "TARGET_RECOVERED_DOMINANT", "G03 classification")

    core = {
        "schema_name": "batch2-development-pilot03-candidate01-g05-owner-review-request-v1",
        "schema_version": "1.0.0",
        "status": "AWAITING_EXPLICIT_OWNER_DECISION",
        "candidate_identity": voice["candidate_identity"],
        "candidate_raw_sha256": voice["candidate_raw_sha256"],
        "candidate_surface": candidate.decode("utf-8").rstrip("\n"),
        "candidate_bytes_modified": False,
        "voice_commit": VOICE_COMMIT,
        "bound_gate_results": {
            "g02": "PASS",
            "g02c": "PASS",
            "g03_validity": "VALID_BLIND_REVIEW",
            "g03_reconciliation": "TARGET_RECOVERED_DOMINANT",
            "g03b": "CAUSAL_MECHANISM_CONFIRMED",
            "g03c_candidate": g03c["candidate_level_verdict"],
            "g03c_pool": g03c["pool_level_verdict"],
            "g03c_contamination": g03c["contamination_verdict"],
            "g04a": naturalness["g04a_verdict"],
            "voice": voice["voice_verdict"],
        },
        "owner_must_explicitly_confirm_or_reject": {
            "candidate_bytes_are_the_reviewed_surface": None,
            "dominant_target_recovery_is_accepted": None,
            "causal_mechanism_finding_is_accepted": None,
            "romanian_naturalness_pass_with_minor_nonmaterial_reservation_is_accepted": None,
            "voice_pass_is_accepted": None,
            "development_only_status_is_accepted": None,
            "pool_pending_status_is_accepted": None,
            "no_curriculum_training_runtime_or_production_eligibility_is_understood": None,
        },
        "closed_owner_decisions": [
            "APPROVE PILOT03 OWNER_FROZEN DEVELOPMENT_ONLY POOL_PENDING",
            "REJECT PILOT03 OWNER_FREEZE",
        ],
        "owner_decision": None,
        "owner_decision_recorded": False,
        "g05_verdict": "AWAITING_EXPLICIT_OWNER_DECISION",
        "eligibility": {
            "partition": "DEVELOPMENT",
            "positive_candidate_status": "PROVISIONAL_PENDING_EXPLICIT_OWNER_DECISION_AND_POOL_CLOSURE",
            "pool_certified": False,
            "curriculum_eligible": False,
            "model_visible": False,
            "training_eligible": False,
            "runtime_eligible": False,
            "production_eligible": False,
        },
        "performed": {key: False for key in ("owner_approval", "owner_rejection", "candidate_repair", "candidate_rewrite", "candidate_regeneration", "training", "runtime_integration", "production_routing", "pool_certification")},
        "authority_matrix": {key: False for key in ("owner_freeze", "curriculum_promotion", "model_exposure", "training", "runtime_integration", "production_routing", "candidate_repair", "candidate_rewrite", "candidate_regeneration", "pool_certification")},
    }
    request = {**core, "g05_owner_review_request_identity": seal("B2_DEVELOPMENT_PILOT03_CANDIDATE01_G05_OWNER_REVIEW_REQUEST_V1", core)}
    audit_core = {
        "schema_name": "batch2-development-pilot03-candidate01-g05-owner-review-request-audit-v1",
        "schema_version": "1.0.0",
        "g05_owner_review_request_identity": request["g05_owner_review_request_identity"],
        "candidate_identity": core["candidate_identity"],
        "candidate_raw_sha256": core["candidate_raw_sha256"],
        "explicit_owner_decision_present": False,
        "authorization_treated_as_substantive_approval": False,
        "pool_pending_preserved": True,
        "development_only_preserved": True,
        "candidate_bytes_modified": False,
        "downstream_authority_granted": False,
        "verdict": "PASS_FAIL_CLOSED_AWAITING_EXPLICIT_OWNER_DECISION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT03_CANDIDATE01_G05_OWNER_REVIEW_REQUEST_AUDIT_V1", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot03-candidate01-g05-owner-review-request-v1.json", request), ("humor-mechanics-batch2-development-pilot03-candidate01-g05-owner-review-request-audit-v1.json", audit)):
        (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g05_verdict": core["g05_verdict"], "g05_owner_review_request_identity": request["g05_owner_review_request_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()

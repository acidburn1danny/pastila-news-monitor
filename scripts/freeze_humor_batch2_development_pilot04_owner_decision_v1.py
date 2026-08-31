"""Freeze the explicit Pilot 04 G05 owner decision."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
REQUEST_COMMIT = "c71d7ad103d382badd26782c3bb6dc87b584a193"
REQUEST_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot04-candidate01-g05-owner-review-request-v1.json"
DECISION = "APPROVE PILOT04 OWNER_FROZEN DEVELOPMENT_ONLY G04B_PENDING"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == REQUEST_COMMIT, "HEAD differs from G05 request commit")
    request = json.loads(subprocess.check_output(["git", "show", f"{REQUEST_COMMIT}:{REQUEST_PATH}"], cwd=ROOT))
    require(request["g05_owner_review_request_identity"] == "79d25cd3ec1cd25566a487f14692f91e21b7658b7165e85fea273eed3210dc31", "request identity")
    require(request["status"] == "AWAITING_EXPLICIT_OWNER_DECISION", "request status")
    require(DECISION in request["closed_owner_decisions"], "decision not allowed")
    require(request["bound_gate_results"]["g03c_pool"] == "POOL_PENDING_PILOT04_QUALITY_GATES_AND_SEPARATE_G04B_CERTIFICATION", "pool status")
    require(request["eligibility"]["partition"] == "DEVELOPMENT", "partition")

    confirmations = {key: True for key in request["owner_must_explicitly_confirm_or_reject"]}
    core = {
        "schema_name": "batch2-development-pilot04-candidate01-g05-owner-freeze-v1",
        "schema_version": "1.0.0",
        "status": "OWNER_FROZEN_DEVELOPMENT_ONLY_G04B_PENDING",
        "g05_verdict": "OWNER_APPROVED",
        "owner_decision": DECISION,
        "owner_decision_explicit": True,
        "g05_owner_review_request_identity": request["g05_owner_review_request_identity"],
        "g05_owner_review_request_commit": REQUEST_COMMIT,
        "candidate_identity": request["candidate_identity"],
        "candidate_raw_sha256": request["candidate_raw_sha256"],
        "candidate_bytes_modified": False,
        "owner_confirmations": confirmations,
        "bound_gate_results": request["bound_gate_results"],
        "evidence_role": "OWNER_FROZEN_PROVISIONAL_DOMINANT_POSITIVE_DEVELOPMENT_ONLY_G04B_PENDING",
        "eligibility": {
            "partition": "DEVELOPMENT",
            "owner_frozen": True,
            "positive_candidate_status": "PROVISIONAL_DOMINANT_POSITIVE_PENDING_G04B",
            "pool_status": "G04B_PENDING_TWO_INDEPENDENT_OWNER_FROZEN_DEVELOPMENT_FAMILIES",
            "pool_certified": False,
            "curriculum_eligible": False,
            "model_visible": False,
            "training_eligible": False,
            "runtime_eligible": False,
            "production_eligible": False,
        },
        "remaining_requirements": [
            "B2_G04B_CROSS_CANDIDATE_POOL_AUDIT",
            "SEPARATE_CURRICULUM_OR_MODEL_VISIBILITY_AUTHORITY_IF_EVER_ELIGIBLE",
        ],
        "authority_matrix": {key: False for key in ("g04b_pool_certification", "curriculum_promotion", "model_exposure", "training", "runtime_integration", "production_routing", "candidate_repair", "candidate_rewrite", "candidate_regeneration")},
    }
    freeze = {**core, "g05_owner_freeze_identity": seal("B2_DEVELOPMENT_PILOT04_CANDIDATE01_G05_OWNER_FREEZE_V1", core)}
    audit_core = {
        "schema_name": "batch2-development-pilot04-candidate01-g05-owner-freeze-audit-v1",
        "schema_version": "1.0.0",
        "g05_owner_freeze_identity": freeze["g05_owner_freeze_identity"],
        "exact_owner_decision_bound": True,
        "request_identity_verified": True,
        "candidate_identity_preserved": True,
        "candidate_bytes_modified": False,
        "development_only_preserved": True,
        "g04b_pending_preserved": True,
        "downstream_authority_granted": False,
        "verdict": "PASS_OWNER_FREEZE_WITH_FAIL_CLOSED_DOWNSTREAM_LIMITS",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT04_CANDIDATE01_G05_OWNER_FREEZE_AUDIT_V1", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot04-candidate01-g05-owner-freeze-v1.json", freeze), ("humor-mechanics-batch2-development-pilot04-candidate01-g05-owner-freeze-audit-v1.json", audit)):
        (ART / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"g05_verdict": core["g05_verdict"], "g05_owner_freeze_identity": freeze["g05_owner_freeze_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()

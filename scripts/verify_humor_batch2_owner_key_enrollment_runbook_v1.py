"""Verify the owner enrollment runbook without generating or signing."""

from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "docs/artifacts/humor-mechanics-batch2-custodial-key-enrollment-request-v1.json"
RUNBOOK = ROOT / "docs/humor-mechanics-batch2-owner-key-enrollment-runbook-v1.md"
HELPER = ROOT / "scripts/owner_humor_batch2_custodial_key_enrollment_v1.py"
ROLES = {
    "RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN", "FAMILY_CUSTODIAN",
    "PARTITION_CUSTODIAN", "BLIND_ESCROW_CUSTODIAN", "CONTAMINATION_AUDITOR",
}


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    runbook = RUNBOOK.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    ast.parse(helper)
    require(request["enrollment_request_identity"] ==
            "c5439550d6a6d86a9a88893cbeb2f88712d6fdcc5fc7b05b08b981ef275c0e04",
            "request identity mismatch")
    require({item["role"] for item in request["requests"]} == ROLES, "role set mismatch")
    for index, item in enumerate(request["requests"]):
        require(item["role"] in runbook and item["challenge"]["challenge_identity"] in runbook,
                f"{item['role']}: challenge absent")
        require(f"/requests/{index}/challenge" in runbook, f"{item['role']}: pointer absent")
    require("ED25519" in helper and "ECDSA_P256_SHA256" in helper, "algorithm support missing")
    require("outside_repository" in helper and "refusing repository-local" in helper,
            "repository path guard missing")
    require("stdout=subprocess.DEVNULL" in helper, "crypto stdout not suppressed")
    require('"private_key_path"' not in helper, "private path emitted to stdout")
    require("private_key_included" in helper, "public response marker missing")
    forbidden = list(ROOT.rglob("*.private.pem")) + list(ROOT.rglob("*.response.json"))
    require(not forbidden, f"generated key/handoff file found: {forbidden[:1]}")
    print(json.dumps({"verdict": "PASS_RUNBOOK_ONLY_NO_KEYS_OR_SIGNATURES",
                      "roles": 6, "canonical_challenges_bound": 6,
                      "private_keys_found_in_repository": 0}, sort_keys=True))


if __name__ == "__main__":
    main()

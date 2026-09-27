"""Runtime primitives for the fixture-only source-bound hybrid boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fixture_editor_core_source_bound_hybrid_feasibility_v1 import (
    execute_with_fallback,
    extractive_proposal,
    validate_ledger,
    verify_proposal,
)

ARMS = ("B0_R2_ONE_PASS", "B1_EXTRACTIVE_BASELINE", "B2_HYBRID")
SEEDS = (161803, 271828, 314159)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def flat_directory_identity(root: Path) -> str:
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode("utf-8")):
        if path.is_symlink() or not path.is_file():
            raise ValueError("adapter closure requires flat regular files")
        rows.append(path.name.encode("utf-8") + b"\0" + path.stat().st_size.to_bytes(8, "big") + bytes.fromhex(sha(path.read_bytes())))
    if not rows:
        raise ValueError("empty adapter")
    return sha(b"".join(rows))


def fixture_arm(arm: str, ledger: dict) -> dict:
    if arm not in ARMS:
        raise ValueError("unknown arm")
    validate_ledger(ledger)
    if arm == "B0_R2_ONE_PASS":
        return {
            "arm": arm,
            "case_id": ledger["case_id"],
            "mode": "REQUEST_ONLY_NO_INFERENCE",
            "source_spans": ledger["source_spans"],
            "model_loaded": False,
        }
    proposal = extractive_proposal(ledger)
    if arm == "B1_EXTRACTIVE_BASELINE":
        verified = verify_proposal(ledger, proposal)
        if not verified["accepted"]:
            raise ValueError("extractive fixture rejected")
        return {
            "arm": arm,
            "case_id": ledger["case_id"],
            "mode": "DETERMINISTIC_EXTRACTIVE",
            "text": verified["text"],
            "verified": True,
            "model_loaded": False,
        }
    result = execute_with_fallback(ledger, proposal)
    return {
        "arm": arm,
        "case_id": ledger["case_id"],
        "mode": "FIXTURE_REALIZER_THEN_VERIFY",
        "route": result["route"],
        "text": result["text"],
        "verified": True,
        "model_loaded": False,
    }

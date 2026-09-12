"""Materialize V8.1's terminal structural qualification disposition."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / ".pastila-runtime/production-core-successor-execution-v8-1-attempt1"
OUTPUT = ROOT / "docs/artifacts/production-core-v8-1-terminal-disposition.json"
AUTHORITY = "589ff2d7f8f98c071e0300a23016970517536f28e065139f5ba0422505a4ebe1"
ATTEMPT = "56193f17487b6e9a04fa977422cae0fdf960ac18ae6f974233b25b1437781627"
COMPLETION = "b5b3e87cb10914351a66762a5862053a0c77dbc3c7fc638c5f6559562f937196"
AUDIT_RECEIPT = "7caba9a9c72423c10d62949f9ce15283562e2533ef715e6b21e925c708b05950"
RUBRIC = "659339bac91cfbdf993c7b57555dfd9191e609816db76e60bc41f13d0dfba1a6"
GENERATION = "6d388a99731e3d4a08fa2a629374c37dd97994806ac54ffe49ab9fb1b41d630d"
ALIASES = {
    "CANDIDATE-A": "pastila-editor-core-v1.2-json-successor",
    "CANDIDATE-B": "pastila-editor-core-v1.1-json-successor-v2",
}


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def load(path: Path) -> tuple[dict, bytes]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"regular file required: {path}")
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or raw != canonical(value):
        raise ValueError(f"noncanonical object: {path}")
    return value, raw


def build(execution: Path = EXECUTION) -> dict[str, object]:
    attempt, attempt_raw = load(execution / "attempt.json")
    completion, completion_raw = load(execution / "completion.json")
    if (execution / "terminal-failure.json").exists():
        raise ValueError("terminal failure conflicts with completion")
    if (
        attempt.get("attempt_identity") != ATTEMPT
        or attempt.get("attempt_ordinal") != 1
        or attempt.get("execution_authority_identity") != AUTHORITY
        or completion.get("completion_identity") != COMPLETION
        or completion.get("execution_authority_identity") != AUTHORITY
        or completion.get("qualification_generation_identity") != GENERATION
        or completion.get("completed_rows") != 2400
        or completion.get("retry_or_redraw") is not False
        or completion.get("adjudication_performed") is not False
        or completion.get("promotion_effect") is not False
    ):
        raise ValueError("attempt/completion binding mismatch")

    inventory = completion.get("artifact_inventory")
    if not isinstance(inventory, list) or identity(inventory) != completion.get(
        "artifact_root"
    ):
        raise ValueError("completion inventory mismatch")
    inventory_paths = {row["path"]: row["sha256"] for row in inventory}
    if len(inventory_paths) != len(inventory):
        raise ValueError("duplicate inventory path")
    receipts = []
    for relative in sorted(
        path for path in inventory_paths if path.endswith(".receipt.json")
    ):
        receipt, raw = load(execution / Path(relative))
        if hashlib.sha256(raw).hexdigest() != inventory_paths[relative]:
            raise ValueError("receipt inventory hash mismatch")
        core = dict(receipt)
        if core.pop("receipt_identity", None) != identity(core):
            raise ValueError("receipt identity mismatch")
        receipts.append(receipt)
    if len(receipts) != 2400 or {
        row.get("global_ordinal") for row in receipts
    } != set(range(1, 2401)):
        raise ValueError("receipt closure mismatch")
    for receipt in receipts:
        if (
            receipt.get("attempt_identity") != ATTEMPT
            or receipt.get("execution_authority_identity") != AUTHORITY
            or receipt.get("qualification_generation_identity") != GENERATION
            or receipt.get("retry_or_redraw") is not False
            or receipt.get("adjudication_performed") is not False
            or receipt.get("promotion_effect") is not False
        ):
            raise ValueError("receipt authority mismatch")

    statuses = Counter(row["structural_status"] for row in receipts)
    alias_counts = Counter(row["candidate_alias"] for row in receipts)
    if statuses != {"FAIL_CLOSED_INVALID_OUTPUT": 2400} or alias_counts != {
        "CANDIDATE-A": 1200,
        "CANDIDATE-B": 1200,
    }:
        raise ValueError("terminal structural rejection not demonstrated")

    core = {
        "schema": "pastila-production-core-v8-1-terminal-qualification-disposition",
        "schema_version": 1,
        "status": "TERMINAL_STRUCTURAL_REJECTION_BOTH_CANDIDATES",
        "execution_authority_identity": AUTHORITY,
        "qualification_generation_identity": GENERATION,
        "rubric_identity": RUBRIC,
        "completion_audit_receipt_identity": AUDIT_RECEIPT,
        "attempt_identity": ATTEMPT,
        "attempt_ordinal": 1,
        "attempt_consumed_permanently": True,
        "completion_identity": COMPLETION,
        "evidence": {
            "attempt_sha256": hashlib.sha256(attempt_raw).hexdigest(),
            "completion_sha256": hashlib.sha256(completion_raw).hexdigest(),
            "artifact_root": completion["artifact_root"],
            "artifact_count": len(inventory),
            "completed_rows": 2400,
            "structural_status_counts": dict(sorted(statuses.items())),
            "candidate_alias_counts": dict(sorted(alias_counts.items())),
        },
        "candidate_dispositions": [
            {
                "candidate_alias": alias,
                "candidate": candidate,
                "disposition": "REJECTED_STRUCTURALLY",
            }
            for alias, candidate in ALIASES.items()
        ],
        "adjudication_authorized": True,
        "semantic_adjudication_required": False,
        "semantic_adjudication_performed": False,
        "semantic_adjudication_bypass_reason": (
            "STRUCTURAL_FAIL_IS_TERMINAL_BEFORE_SIGNATURE_VERIFICATION"
        ),
        "stale_custody_exports_used": False,
        "retry_or_redraw": False,
        "candidate_execution_repeated": False,
        "promotion_effect": False,
        "successor_requirement": "NEW_SUCCESSOR_LINEAGE_AND_NEW_EXECUTION_AUTHORITY",
    }
    return {**core, "disposition_identity": identity(core)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution", type=Path, default=EXECUTION)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    value = build(args.execution)
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n"
    if args.output.exists() and (
        args.output.is_symlink() or args.output.read_bytes() != raw
    ):
        raise SystemExit("published V8.1 disposition differs")
    if not args.output.exists():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    print(value["disposition_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

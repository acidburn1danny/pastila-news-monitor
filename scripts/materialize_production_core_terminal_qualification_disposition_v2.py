"""Materialize the terminal structural disposition for the consumed Core V2 attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

EXPECTED_ATTEMPT = "c4cf86d09f92d156f5a506f71e04ce9166d1061ed69a7f6460539c8243d3380a"
EXPECTED_COMPLETION = "7b7ac4fc43a8fc8b58cbdba84f4d76722ffcef130e78f977af9c352582f9ba2f"
EXPECTED_AUTHORITY = "1192708d5fb27a4d4a1da3c4fd6b4408acef72790b7db3b8b79287be9857efe4"
EXPECTED_GENERATION = "ccb426a8dd5f062794056a164fe815ab59af45db6166a1340853ead42a55e528"
CANDIDATES = (
    "pastila-editor-core-v1.1-experimental",
    "pastila-editor-core-v1.2-experimental",
)


def authority_canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def identity(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    ).hexdigest()


def authority_identity(value: object) -> str:
    return hashlib.sha256(authority_canonical(value)).hexdigest()


def load_canonical(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or raw != authority_canonical(value):
        raise SystemExit(f"noncanonical object: {path}")
    return value, raw


def verify_identity(value: dict, field: str) -> None:
    core = dict(value)
    observed = core.pop(field, None)
    if observed != authority_identity(core):
        raise SystemExit(f"identity mismatch: {field}")


def build(execution_root: Path) -> dict:
    attempt, attempt_raw = load_canonical(execution_root / "attempt.json")
    completion, completion_raw = load_canonical(execution_root / "completion.json")
    if (execution_root / "terminal-failure.json").exists():
        raise SystemExit("terminal failure conflicts with completion")
    verify_identity(attempt, "attempt_identity")
    verify_identity(completion, "completion_identity")
    if attempt.get("attempt_identity") != EXPECTED_ATTEMPT or attempt.get("attempt_ordinal") != 1:
        raise SystemExit("unexpected consumed attempt")
    if completion.get("completion_identity") != EXPECTED_COMPLETION:
        raise SystemExit("unexpected completion")
    for value in (attempt, completion):
        if value.get("execution_authority_identity") != EXPECTED_AUTHORITY:
            raise SystemExit("execution authority mismatch")
        if value.get("qualification_generation_identity") != EXPECTED_GENERATION:
            raise SystemExit("qualification generation mismatch")
        if value.get("promotion_effect") is not False:
            raise SystemExit("promotion effect is not false")
    if attempt.get("status") != "CONSUMED_BEFORE_EXECUTION":
        raise SystemExit("attempt is not permanently consumed")
    if attempt.get("retry_or_redraw_authorized") is not False:
        raise SystemExit("retry/redraw authority present")
    if completion.get("completed_rows") != 2400:
        raise SystemExit("matrix is incomplete")
    if completion.get("retry_or_redraw") is not False or completion.get("adjudication_performed") is not False:
        raise SystemExit("completion exceeds authorized boundary")

    inventory = completion.get("artifact_inventory")
    if not isinstance(inventory, list) or authority_identity(inventory) != completion.get("artifact_root"):
        raise SystemExit("completion inventory root mismatch")
    inventory_by_path = {row["path"]: row["sha256"] for row in inventory}
    if len(inventory_by_path) != len(inventory):
        raise SystemExit("duplicate inventory path")
    for relative, expected_sha in inventory_by_path.items():
        path = execution_root / Path(relative)
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"missing regular inventory object: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
            raise SystemExit(f"inventory hash mismatch: {relative}")

    receipts = []
    for relative in sorted(path for path in inventory_by_path if path.endswith(".receipt.json")):
        receipt, _ = load_canonical(execution_root / Path(relative))
        verify_identity(receipt, "receipt_identity")
        receipts.append(receipt)
    if len(receipts) != 2400:
        raise SystemExit("receipt closure mismatch")
    if {row.get("global_ordinal") for row in receipts} != set(range(1, 2401)):
        raise SystemExit("receipt ordinal closure mismatch")
    for row in receipts:
        if row.get("attempt_identity") != EXPECTED_ATTEMPT:
            raise SystemExit("receipt attempt mismatch")
        if row.get("execution_authority_identity") != EXPECTED_AUTHORITY:
            raise SystemExit("receipt authority mismatch")
        if row.get("qualification_generation_identity") != EXPECTED_GENERATION:
            raise SystemExit("receipt generation mismatch")
        if row.get("retry_or_redraw") is not False or row.get("adjudication_performed") is not False or row.get("promotion_effect") is not False:
            raise SystemExit("receipt exceeds authorized boundary")

    status = Counter(row["structural_status"] for row in receipts)
    aliases = Counter(row["candidate_alias"] for row in receipts)
    materializations = Counter(row["materialization"] for row in receipts)
    if status != {"FAIL_CLOSED_INVALID_OUTPUT": 2400}:
        raise SystemExit("structural rejection is not unanimous")
    if aliases != {"CANDIDATE-A": 1200, "CANDIDATE-B": 1200}:
        raise SystemExit("candidate alias coverage mismatch")
    if materializations != {"A": 1200, "B": 1200}:
        raise SystemExit("materialization coverage mismatch")

    core = {
        "schema": "pastila-production-core-terminal-qualification-disposition-v2",
        "schema_version": 2,
        "status": "TERMINAL_STRUCTURAL_REJECTION_BOTH_CANDIDATES",
        "execution_authority_identity": EXPECTED_AUTHORITY,
        "qualification_generation_identity": EXPECTED_GENERATION,
        "attempt_identity": EXPECTED_ATTEMPT,
        "attempt_ordinal": 1,
        "attempt_consumed_permanently": True,
        "completion_identity": EXPECTED_COMPLETION,
        "evidence": {
            "attempt_sha256": hashlib.sha256(attempt_raw).hexdigest(),
            "completion_sha256": hashlib.sha256(completion_raw).hexdigest(),
            "artifact_root": completion["artifact_root"],
            "artifact_count": len(inventory),
            "completed_rows": 2400,
            "structural_status_counts": dict(sorted(status.items())),
            "candidate_alias_counts": dict(sorted(aliases.items())),
            "materialization_counts": dict(sorted(materializations.items())),
        },
        "candidate_dispositions": [
            {"candidate": candidate, "disposition": "REJECTED_STRUCTURALLY"}
            for candidate in CANDIDATES
        ],
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
        "successor_requirement": "NEW_SUCCESSOR_LINEAGE_AND_NEW_EXECUTION_AUTHORITY",
    }
    return {**core, "disposition_identity": identity(core)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    disposition = build(args.execution_root.resolve(strict=True))
    encoded = json.dumps(disposition, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    if args.output.exists():
        if args.output.read_bytes() != encoded:
            raise SystemExit("published disposition differs")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(encoded)
    print(disposition["disposition_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

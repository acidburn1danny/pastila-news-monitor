"""Materialize the terminal failure disposition for the consumed successor V3 attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ATTEMPT = "337bb8acc130cc02f77f83c7a026b9212c781ba06d11989e64ef11b334f6a5ca"
FAILURE = "d132b5c57e8ffc7344b70ae2881655b02abb7baebf3c916c6ae2259d361f9e89"
AUTHORITY = "2a8fb059d36efad540e86c7d232643683cc48bcbf8507a94d5607d0316561cb1"
GENERATION = "7b4900523953253391e8753d39ae8253e6652055cf5c99612a007eaadba552f9"


def canonical(value: object) -> bytes:
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


def load_canonical(path: Path) -> tuple[dict[str, object], bytes]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or raw != canonical(value):
        raise SystemExit(f"noncanonical evidence: {path}")
    return value, raw


def verify(value: dict[str, object], field: str) -> None:
    core = dict(value)
    recorded = core.pop(field, None)
    if recorded != hashlib.sha256(canonical(core)).hexdigest():
        raise SystemExit(f"identity mismatch: {field}")


def build(root: Path) -> dict[str, object]:
    attempt, attempt_raw = load_canonical(root / "attempt.json")
    failure, failure_raw = load_canonical(root / "terminal-failure.json")
    if (root / "completion.json").exists():
        raise SystemExit("completion conflicts with terminal failure")
    verify(attempt, "attempt_identity")
    verify(failure, "terminal_failure_identity")
    if (
        attempt.get("attempt_identity") != ATTEMPT
        or attempt.get("attempt_ordinal") != 1
    ):
        raise SystemExit("attempt mismatch")
    if attempt.get("execution_authority_identity") != AUTHORITY:
        raise SystemExit("execution authority mismatch")
    if attempt.get("qualification_generation_identity") != GENERATION:
        raise SystemExit("generation mismatch")
    if attempt.get("status") != "CONSUMED_BEFORE_EXECUTION":
        raise SystemExit("attempt consumption mismatch")
    if failure.get("terminal_failure_identity") != FAILURE:
        raise SystemExit("terminal failure mismatch")
    expected_failure = {
        "completed_rows": 1800,
        "failure_class": "UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION",
        "failed_batch": {
            "materialization": "B",
            "repetition": 2,
            "candidate_alias": "CANDIDATE-B",
        },
        "partial_artifact_count": 5680,
        "partial_artifact_root": "a37c02a3e21a0612b20d150af9f6b0c7958ac6a344bfa3573eee15c7d39eed72",
        "retry_or_redraw_authorized": False,
        "promotion_effect": False,
    }
    if any(failure.get(key) != value for key, value in expected_failure.items()):
        raise SystemExit("terminal evidence mismatch")
    if (
        failure.get("attempt_identity") != ATTEMPT
        or failure.get("qualification_generation_identity") != GENERATION
    ):
        raise SystemExit("terminal lineage mismatch")
    partial = []
    for path in sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.name != "terminal-failure.json"
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    ):
        if path.is_symlink():
            raise SystemExit("partial artifact symlink rejected")
        partial.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    if (
        len(partial) != 5680
        or hashlib.sha256(canonical(partial)).hexdigest()
        != expected_failure["partial_artifact_root"]
    ):
        raise SystemExit("partial artifact closure mismatch")
    raw_count = sum(path.endswith(".raw") for path in (row["path"] for row in partial))
    receipt_count = sum(
        path.endswith(".receipt.json") for path in (row["path"] for row in partial)
    )
    if raw_count != 1914 or receipt_count != 1800:
        raise SystemExit("partial progress mismatch")
    core = {
        "schema": "pastila-production-core-successor-terminal-disposition-v3",
        "schema_version": 3,
        "terminal_state": "FAILURE",
        "failure_class": "UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION",
        "root_cause_determined": False,
        "execution_authority_identity": AUTHORITY,
        "qualification_generation_identity": GENERATION,
        "attempt_ordinal": 1,
        "attempt_identity": ATTEMPT,
        "terminal_failure_identity": FAILURE,
        "attempt_consumed_permanently": True,
        "attempt_relaunch_authorized": False,
        "finalized_rows": {"completed": 1800, "matrix": 2400},
        "partial_raw_outputs": {"completed": 1914, "matrix": 2400},
        "failed_batch": expected_failure["failed_batch"],
        "evidence": {
            "attempt_sha256": hashlib.sha256(attempt_raw).hexdigest(),
            "terminal_failure_sha256": hashlib.sha256(failure_raw).hexdigest(),
            "partial_artifact_count": 5680,
            "partial_artifact_root": expected_failure["partial_artifact_root"],
        },
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
    encoded = (
        json.dumps(disposition, ensure_ascii=False, indent=2, sort_keys=True).encode()
        + b"\n"
    )
    if args.output.exists() and args.output.read_bytes() != encoded:
        raise SystemExit("published disposition differs")
    if not args.output.exists():
        args.output.write_bytes(encoded)
    print(disposition["disposition_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

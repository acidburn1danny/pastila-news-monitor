"""Materialize the terminal disposition for the consumed successor V4 attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

AUTHORITY = "1e13898e54a330b99f1717f6e104e6e92a8f60ced31b0b6c80f7b03594806700"
ATTEMPT = "0d5b83d2d4437a9f534d6e813dea491ebbedc51a6ee307760ecfef2d007095e1"
FAILURE = "3f30d18ba5f65f4e26e63423c90aa154f3d1aea0ea3db8fca4e4eef11e44f632"
GENERATION = "7b4900523953253391e8753d39ae8253e6652055cf5c99612a007eaadba552f9"
FAILED = Path("materialization-A/repetition-2/CANDIDATE-B/results")


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
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"evidence path rejected: {path}")
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


def build(root: Path, authority_path: Path) -> dict[str, object]:
    authority = json.loads(authority_path.read_bytes())
    authority_core = dict(authority)
    if (
        authority_path.is_symlink()
        or authority_core.pop("execution_authority_identity", None) != AUTHORITY
        or hashlib.sha256(canonical(authority_core)).hexdigest() != AUTHORITY
        or authority.get("attempt_consumption_authorized") is not False
        or authority.get("candidate_execution_performed") is not False
    ):
        raise SystemExit("execution authority drift")
    attempt, attempt_raw = load_canonical(root / "attempt.json")
    failure, failure_raw = load_canonical(root / "terminal-failure.json")
    supervisor, supervisor_raw = load_canonical(
        root / FAILED / "supervisor-failure.json"
    )
    heartbeat, heartbeat_raw = load_canonical(root / FAILED / "heartbeat.json")
    started, started_raw = load_canonical(root / FAILED / "inference-013-started.json")
    if (root / "completion.json").exists():
        raise SystemExit("completion conflicts with terminal failure")
    verify(attempt, "attempt_identity")
    verify(failure, "terminal_failure_identity")
    if (
        attempt.get("execution_authority_identity") != AUTHORITY
        or attempt.get("attempt_identity") != ATTEMPT
        or attempt.get("attempt_ordinal") != 1
        or attempt.get("status") != "CONSUMED_BEFORE_EXECUTION"
    ):
        raise SystemExit("attempt mismatch")
    expected_failure = {
        "completed_rows": 600,
        "failure_class": "INFERENCE_WALL_TIME_EXCEEDED",
        "failed_batch": {
            "materialization": "A",
            "repetition": 2,
            "candidate_alias": "CANDIDATE-B",
        },
        "partial_artifact_count": 3071,
        "partial_artifact_root": "adc8b2823cb15ff42257a63d4d073d837fe5c218b576adb7dfc121ff998e04e8",
        "retry_or_redraw_authorized": False,
        "promotion_effect": False,
    }
    if (
        failure.get("terminal_failure_identity") != FAILURE
        or failure.get("attempt_identity") != ATTEMPT
        or failure.get("qualification_generation_identity") != GENERATION
        or any(failure.get(key) != value for key, value in expected_failure.items())
    ):
        raise SystemExit("terminal failure mismatch")
    if supervisor != {
        "schema": "pastila-production-core-supervisor-failure",
        "schema_version": 2,
        "code": "INFERENCE_WALL_TIME_EXCEEDED",
        "ceiling_ns": 600_000_000_000,
        "watchdog_exit_code": 124,
        "last_sequence": 13,
        "last_completed_count": 12,
        "last_stage": "GENERATE",
    }:
        raise SystemExit("supervisor evidence mismatch")
    if (
        heartbeat.get("stage") != "GENERATE"
        or heartbeat.get("sequence") != 13
        or heartbeat.get("completed_count") != 12
        or heartbeat.get("case_id") != "pcq-unc-018"
        or started.get("phase") != "STARTED"
        or started.get("sequence") != 13
        or started.get("completed_count") != 12
        or started.get("case_id") != "pcq-unc-018"
        or started.get("request_identity")
        != "sha256:db9e692a353383f1726786a75ec313343022f8f4b0342216f8aaf030508cedf8"
    ):
        raise SystemExit("failed inference lifecycle mismatch")
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
        len(partial) != 3071
        or hashlib.sha256(canonical(partial)).hexdigest()
        != expected_failure["partial_artifact_root"]
    ):
        raise SystemExit("partial artifact closure mismatch")
    counts = {
        "raw": sum(row["path"].endswith(".raw") for row in partial),
        "receipt": sum(row["path"].endswith(".receipt.json") for row in partial),
        "lifecycle_started": sum(
            row["path"].endswith("-started.json") for row in partial
        ),
        "lifecycle_completed": sum(
            row["path"].endswith("-completed.json") for row in partial
        ),
    }
    if counts != {
        "raw": 612,
        "receipt": 600,
        "lifecycle_started": 613,
        "lifecycle_completed": 612,
    }:
        raise SystemExit("partial progress mismatch")
    core = {
        "schema": "pastila-production-core-successor-terminal-disposition-v4",
        "schema_version": 4,
        "terminal_state": "FAILURE",
        "failure_class": "INFERENCE_WALL_TIME_EXCEEDED",
        "execution_boundary_cause_determined": True,
        "internal_generate_stall_cause": "UNDETERMINED",
        "execution_authority_identity": AUTHORITY,
        "qualification_generation_identity": GENERATION,
        "attempt_ordinal": 1,
        "attempt_identity": ATTEMPT,
        "terminal_failure_identity": FAILURE,
        "attempt_consumed_permanently": True,
        "attempt_relaunch_authorized": False,
        "finalized_rows": {"completed": 600, "matrix": 2400},
        "partial_raw_outputs": {"completed": 612, "matrix": 2400},
        "failed_batch": expected_failure["failed_batch"],
        "failed_inference": {
            "sequence": 13,
            "completed_before_inference": 12,
            "case_id": "pcq-unc-018",
            "request_identity": "sha256:db9e692a353383f1726786a75ec313343022f8f4b0342216f8aaf030508cedf8",
            "input_tokens": 1639,
            "raw_output_absent": True,
            "observation_absent": True,
        },
        "watchdog_exit_code": 124,
        "evidence": {
            "authority_sha256": hashlib.sha256(authority_path.read_bytes()).hexdigest(),
            "attempt_sha256": hashlib.sha256(attempt_raw).hexdigest(),
            "terminal_failure_sha256": hashlib.sha256(failure_raw).hexdigest(),
            "supervisor_failure_sha256": hashlib.sha256(supervisor_raw).hexdigest(),
            "last_heartbeat_sha256": hashlib.sha256(heartbeat_raw).hexdigest(),
            "failed_inference_started_sha256": hashlib.sha256(started_raw).hexdigest(),
            "partial_artifact_count": 3071,
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
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = build(
        args.execution_root.resolve(strict=True), args.authority.resolve(strict=True)
    )
    encoded = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    )
    if args.output.exists() and args.output.read_bytes() != encoded:
        raise SystemExit("published disposition differs")
    if not args.output.exists():
        args.output.write_bytes(encoded)
    print(value["disposition_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

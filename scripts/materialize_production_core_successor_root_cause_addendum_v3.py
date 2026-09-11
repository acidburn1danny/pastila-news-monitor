"""Materialize the forensic root-cause addendum for consumed successor attempt V3."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ATTEMPT = "337bb8acc130cc02f77f83c7a026b9212c781ba06d11989e64ef11b334f6a5ca"
TERMINAL_FAILURE = "d132b5c57e8ffc7344b70ae2881655b02abb7baebf3c916c6ae2259d361f9e89"
DISPOSITION = "4a95de2298db2cd618cafd8b9e17797097fcc93af901f386fccb474c4e9e052a"
DISPOSITION_SHA256 = "2589d7fadd42cc4cae3dbae27fbc969f8bc87af796d5a01cd401db385d0169cb"
TERMINAL_FAILURE_SHA256 = "59c311f73ad90d6ad3342b06c83d70693c5a744188e6182dd331be1613b7896c"
SUPERVISOR_SHA256 = "ea83c3c04bf2f72b6e98f5dfd6710061a06765d5e97cf622a48d09c4133d179f"
HEARTBEAT_SHA256 = "62ab14477d2d4e597734528d00c4495977f904765ea2480fffb458f431abaa7a"
FAILED_DIRECTORY = Path("materialization-B/repetition-2/CANDIDATE-B")


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


def load_object(path: Path, *, canonical_required: bool = True) -> tuple[dict, bytes]:
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"evidence path rejected: {path}")
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or (canonical_required and raw != canonical(value)):
        raise SystemExit(f"evidence encoding rejected: {path}")
    return value, raw


def build(execution_root: Path, disposition_path: Path) -> dict[str, object]:
    disposition, disposition_raw = load_object(
        disposition_path, canonical_required=False
    )
    failure, failure_raw = load_object(execution_root / "terminal-failure.json")
    failed = execution_root / FAILED_DIRECTORY
    supervisor, supervisor_raw = load_object(failed / "results/supervisor-failure.json")
    heartbeat, heartbeat_raw = load_object(failed / "results/heartbeat.json")
    batch_raw = (failed / "batch.json").read_bytes()
    batch = json.loads(batch_raw)
    if (
        hashlib.sha256(disposition_raw).hexdigest() != DISPOSITION_SHA256
        or disposition.get("disposition_identity") != DISPOSITION
        or disposition.get("root_cause_determined") is not False
    ):
        raise SystemExit("historical disposition drift")
    if (
        hashlib.sha256(failure_raw).hexdigest() != TERMINAL_FAILURE_SHA256
        or failure.get("terminal_failure_identity") != TERMINAL_FAILURE
        or failure.get("attempt_identity") != ATTEMPT
        or failure.get("failure_class") != "UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION"
    ):
        raise SystemExit("terminal failure drift")
    if hashlib.sha256(supervisor_raw).hexdigest() != SUPERVISOR_SHA256 or supervisor != {
        "schema": "pastila-production-core-supervisor-failure",
        "schema_version": 1,
        "code": "INFERENCE_WALL_TIME_EXCEEDED",
        "ceiling_ns": 600_000_000_000,
    }:
        raise SystemExit("supervisor evidence drift")
    if hashlib.sha256(heartbeat_raw).hexdigest() != HEARTBEAT_SHA256 or heartbeat != {
        "stage": "GENERATE",
        "sequence": 115,
        "completed_count": 114,
        "case_id": "pcq-unc-025",
        "deadline_boottime_ns": 39_819_100_000_000,
    }:
        raise SystemExit("heartbeat evidence drift")
    if not isinstance(batch, list) or len(batch) != 200 or batch[114].get(
        "case_id"
    ) != "pcq-unc-025":
        raise SystemExit("failed case binding drift")
    stem = "pcq-unc-025.edcb67dadf41d5d3211823d05cc2ab53119cf279dfdaa47c321dcd4134ec0492"
    if any((failed / "results" / f"{stem}.{suffix}").exists() for suffix in ("raw", "observation.json")):
        raise SystemExit("failed inference unexpectedly has terminal output")
    core = {
        "schema": "pastila-production-core-successor-root-cause-addendum-v3",
        "schema_version": 3,
        "historical_disposition_identity": DISPOSITION,
        "historical_disposition_reinterpreted": False,
        "attempt_ordinal": 1,
        "attempt_identity": ATTEMPT,
        "terminal_failure_identity": TERMINAL_FAILURE,
        "attempt_consumed_permanently": True,
        "attempt_relaunch_authorized": False,
        "execution_boundary_cause": "INFERENCE_WALL_TIME_EXCEEDED",
        "internal_generate_stall_cause": "UNDETERMINED",
        "failed_inference": {
            "materialization": "B",
            "repetition": 2,
            "candidate_alias": "CANDIDATE-B",
            "sequence": 115,
            "completed_before_inference": 114,
            "case_id": "pcq-unc-025",
            "request_identity": "sha256:edcb67dadf41d5d3211823d05cc2ab53119cf279dfdaa47c321dcd4134ec0492",
            "raw_output_absent": True,
            "observation_absent": True,
        },
        "evidence_chain": [
            "GENERATE_HEARTBEAT_SEQUENCE_115_COMPLETED_114",
            "NO_CASE_COMPLETE_OR_DURABLE_OUTPUT_FOR_SEQUENCE_115",
            "SUPERVISOR_INFERENCE_WALL_TIME_EXCEEDED_600000000000_NS",
            "WATCHDOG_KILL_AND_EXIT_124",
            "OUTER_SUBPROCESS_CALLED_PROCESS_ERROR",
            "TERMINAL_FAILURE_UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION",
        ],
        "watchdog_exit_code": 124,
        "evidence": {
            "historical_disposition_sha256": DISPOSITION_SHA256,
            "terminal_failure_sha256": TERMINAL_FAILURE_SHA256,
            "supervisor_failure_sha256": SUPERVISOR_SHA256,
            "last_heartbeat_sha256": HEARTBEAT_SHA256,
            "failed_batch_sha256": hashlib.sha256(batch_raw).hexdigest(),
        },
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return {**core, "addendum_identity": identity(core)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-root", type=Path, required=True)
    parser.add_argument("--disposition", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = build(
        args.execution_root.resolve(strict=True),
        args.disposition.resolve(strict=True),
    )
    encoded = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    if args.output.exists() and args.output.read_bytes() != encoded:
        raise SystemExit("published addendum differs")
    if not args.output.exists():
        args.output.write_bytes(encoded)
    print(value["addendum_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

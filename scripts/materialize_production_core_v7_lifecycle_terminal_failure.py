"""Terminalize the consumed V7 attempt after its post-matrix schema mismatch."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

AUTHORITY = "c3cd54548938cbf8da161279a77152fdefe98a28e59a5ae502b198e24a61cd20"
ATTEMPT = "48a971983f78a4395dc03e40ba26b1e98e62bb7c452bb43ce0caf662b0d5d72d"
GENERATION = "6d388a99731e3d4a08fa2a629374c37dd97994806ac54ffe49ab9fb1b41d630d"
FAILURE_CLASS = "INFERENCE_LIFECYCLE_EVIDENCE_MISMATCH_AFTER_ATTEMPT_CONSUMPTION"
MATRIX_ROWS = 2400
ARTIFACT_COUNT = 12073

COMPLETED_KEYS = (
    "schema",
    "schema_version",
    "phase",
    "sequence",
    "completed_count",
    "case_id",
    "request_identity",
    "started_event_identity",
    "generation_wall_ns",
    "output_tokens",
    "terminal_eos",
    "termination_reason",
    "event_identity",
)
STALE_VALIDATOR_KEYS = COMPLETED_KEYS[:-2] + ("event_identity",)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def identity(value: object, *, sorted_keys: bool = False) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=sorted_keys,
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


def verify_identity(value: dict[str, object], field: str) -> None:
    core = dict(value)
    recorded = core.pop(field, None)
    if recorded != identity(core):
        raise SystemExit(f"identity mismatch: {field}")


def inventory(root: Path) -> list[dict[str, str]]:
    result = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if not path.is_file():
            continue
        if path == root / "terminal-failure.json":
            continue
        if path.is_symlink():
            raise SystemExit(f"artifact symlink rejected: {path}")
        result.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return result


def inspect_lifecycle(root: Path) -> dict[str, object]:
    completed_paths = sorted(root.rglob("inference-*-completed.json"))
    started_paths = sorted(root.rglob("inference-*-started.json"))
    observation_paths = sorted(root.rglob("*.observation.json"))
    if not (
        len(completed_paths) == len(started_paths) == len(observation_paths) == MATRIX_ROWS
    ):
        raise SystemExit("lifecycle cardinality mismatch")
    reasons: dict[str, int] = {}
    first = None
    for path in completed_paths:
        completed, _ = load_canonical(path)
        if tuple(completed) != COMPLETED_KEYS:
            raise SystemExit(f"unexpected completed schema: {path}")
        verify_identity(completed, "event_identity")
        reason = completed.get("termination_reason")
        if reason not in ("TERMINAL_EOS", "OUTPUT_BYTE_CEILING_EXCEEDED"):
            raise SystemExit(f"unexpected termination reason: {path}")
        reasons[str(reason)] = reasons.get(str(reason), 0) + 1
        if first is None:
            first = {
                "path": path.relative_to(root).as_posix(),
                "case_id": completed["case_id"],
                "request_identity": completed["request_identity"],
                "event_identity": completed["event_identity"],
                "termination_reason": reason,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    if reasons != {"OUTPUT_BYTE_CEILING_EXCEEDED": 6, "TERMINAL_EOS": 2394}:
        raise SystemExit("termination reason distribution mismatch")
    return {
        "started_events": len(started_paths),
        "completed_events": len(completed_paths),
        "observations": len(observation_paths),
        "executor_completed_keys": list(COMPLETED_KEYS),
        "stale_final_validator_completed_keys": list(STALE_VALIDATOR_KEYS),
        "field_rejected_only_by_stale_validator": "termination_reason",
        "termination_reason_counts": reasons,
        "first_demonstrating_event": first,
    }


def load_authority_module(path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("v7_execution_authority", path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise SystemExit("authority module loader absent")
    spec.loader.exec_module(module)
    return module


def atomic(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink():
        if path.is_file() and not path.is_symlink() and path.read_bytes() == raw:
            return
        raise SystemExit(f"published artifact differs: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def materialize(root: Path, repository: Path, addendum_path: Path) -> tuple[str, str]:
    if (root / "completion.json").exists():
        raise SystemExit("completion conflicts with terminal failure")
    attempt, attempt_raw = load_canonical(root / "attempt.json")
    verify_identity(attempt, "attempt_identity")
    if (
        attempt.get("attempt_identity") != ATTEMPT
        or attempt.get("execution_authority_identity") != AUTHORITY
        or attempt.get("qualification_generation_identity") != GENERATION
        or attempt.get("attempt_ordinal") != 1
        or attempt.get("status") != "CONSUMED_BEFORE_EXECUTION"
    ):
        raise SystemExit("attempt drift")
    lifecycle = inspect_lifecycle(root)
    partial = inventory(root)
    if len(partial) != ARTIFACT_COUNT:
        raise SystemExit("pre-terminal artifact cardinality mismatch")
    paths = {row["path"] for row in partial}
    if sum(path.startswith("checkpoint-") for path in paths) != 12:
        raise SystemExit("checkpoint cardinality mismatch")
    authority_source = repository / "src/pastila_scout/production_core_candidate_execution_authority_v3.py"
    executor_source = repository / "scripts/execute_production_core_candidate_qualification_v3.py"
    authority_module = load_authority_module(authority_source)
    failure = authority_module.build_terminal_failure(
        attempt,
        MATRIX_ROWS,
        FAILURE_CLASS,
        failed_batch=None,
        partial_artifacts=partial,
    )
    authority_module.validate_terminal_failure(failure, attempt, partial)
    failure_raw = canonical(failure)
    atomic(root / "terminal-failure.json", failure_raw)

    core = {
        "schema": "pastila-production-core-successor-v7-root-cause-addendum",
        "schema_version": 1,
        "execution_authority_identity": AUTHORITY,
        "qualification_generation_identity": GENERATION,
        "attempt_ordinal": 1,
        "attempt_identity": ATTEMPT,
        "attempt_consumed_permanently": True,
        "attempt_relaunch_authorized": False,
        "terminal_failure_identity": failure["terminal_failure_identity"],
        "failure_class": FAILURE_CLASS,
        "completed_rows": MATRIX_ROWS,
        "checkpoint_count": 12,
        "failed_batch": None,
        "mismatch": {
            "classification": "FROZEN_FINAL_VALIDATOR_SCHEMA_STALE",
            "executor_completed_schema_includes": "termination_reason",
            "final_validator_completed_schema_omits": "termination_reason",
            "attempt_outputs_reinterpreted": False,
            "attempt_outputs_modified": False,
        },
        "lifecycle_evidence": lifecycle,
        "evidence": {
            "attempt_sha256": hashlib.sha256(attempt_raw).hexdigest(),
            "terminal_failure_sha256": hashlib.sha256(failure_raw).hexdigest(),
            "partial_artifact_count": ARTIFACT_COUNT,
            "partial_artifact_root": identity(partial),
            "executor_source_sha256": hashlib.sha256(executor_source.read_bytes()).hexdigest(),
            "final_validator_source_sha256": hashlib.sha256(authority_source.read_bytes()).hexdigest(),
        },
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
        "successor_requirement": "NEW_SUCCESSOR_LINEAGE_AND_NEW_EXECUTION_AUTHORITY",
    }
    addendum = {**core, "addendum_identity": identity(core, sorted_keys=True)}
    addendum_raw = (
        json.dumps(addendum, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    )
    atomic(addendum_path, addendum_raw)
    return str(failure["terminal_failure_identity"]), str(addendum["addendum_identity"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-root", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--addendum", type=Path, required=True)
    args = parser.parse_args()
    failure, addendum = materialize(
        args.execution_root.resolve(strict=True),
        args.repository.resolve(strict=True),
        args.addendum.absolute(),
    )
    print(json.dumps({"terminal_failure_identity": failure, "addendum_identity": addendum}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

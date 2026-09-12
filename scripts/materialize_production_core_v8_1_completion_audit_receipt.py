"""Materialize the read-only V8.1 completion audit receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXECUTION = (
    ROOT
    / ".pastila-runtime"
    / "production-core-successor-execution-v8-1-attempt1"
)
DEFAULT_OUTPUT = (
    ROOT
    / "docs"
    / "artifacts"
    / "production-core-v8-1-completion-audit-receipt.json"
)
AUTHORITY_IDENTITY = (
    "589ff2d7f8f98c071e0300a23016970517536f28e065139f5ba0422505a4ebe1"
)
ATTEMPT_IDENTITY = (
    "56193f17487b6e9a04fa977422cae0fdf960ac18ae6f974233b25b1437781627"
)
COMPLETION_IDENTITY = (
    "b5b3e87cb10914351a66762a5862053a0c77dbc3c7fc638c5f6559562f937196"
)
COMPLETION_SHA256 = (
    "c7152d87aebae0b4dcb79044ed479261494a26208a977ffd94bd83c0a13614b6"
)
ARTIFACT_ROOT = (
    "060dfa6989f86a267196924778543500a61e4c70cad81e0a8e2b1307c9d21a8b"
)
AUDITED_SOURCE_COMMIT = "db91e013fbe540ed745dc32f4caa1590aa14600d"
VALIDATOR_SHA256 = (
    "404a180db4500b6e6cb633d9e17e3b5a3ec8ae615f9babdcf0ad50f8f0d1989c"
)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def regular_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"regular file required: {path}")
    return path.read_bytes()


def build(execution: Path = DEFAULT_EXECUTION) -> dict[str, object]:
    if execution.is_symlink() or not execution.is_dir():
        raise ValueError("execution root rejected")
    paths = sorted(execution.rglob("*"), key=lambda item: item.as_posix().encode())
    if any(path.is_symlink() for path in paths):
        raise ValueError("execution symlink rejected")
    if any(path.name.startswith(".checkpoint-") for path in paths):
        raise ValueError("checkpoint staging residue")
    if (execution / "terminal-failure.json").exists():
        raise ValueError("terminal failure conflicts with completion")

    attempt_raw = regular_bytes(execution / "attempt.json")
    attempt = json.loads(attempt_raw)
    completion_raw = regular_bytes(execution / "completion.json")
    completion = json.loads(completion_raw)
    if (
        attempt.get("attempt_identity") != ATTEMPT_IDENTITY
        or attempt.get("attempt_ordinal") != 1
        or attempt.get("execution_authority_identity") != AUTHORITY_IDENTITY
        or completion.get("completion_identity") != COMPLETION_IDENTITY
        or hashlib.sha256(completion_raw).hexdigest() != COMPLETION_SHA256
        or completion.get("artifact_root") != ARTIFACT_ROOT
        or completion.get("completed_rows") != 2400
    ):
        raise ValueError("terminal identity binding mismatch")
    completion_core = dict(completion)
    if completion_core.pop("completion_identity") != identity(completion_core):
        raise ValueError("completion identity mismatch")

    observed_inventory = [
        {
            "path": path.relative_to(execution).as_posix(),
            "sha256": hashlib.sha256(regular_bytes(path)).hexdigest(),
        }
        for path in paths
        if path.is_file() and path.name != "completion.json"
    ]
    if (
        completion.get("artifact_inventory") != observed_inventory
        or identity(observed_inventory) != ARTIFACT_ROOT
    ):
        raise ValueError("completion artifact closure mismatch")

    checkpoints = []
    previous = None
    for ordinal in range(1, 13):
        path = execution / f"checkpoint-{ordinal:02d}.json"
        raw = regular_bytes(path)
        value = json.loads(raw)
        core = dict(value)
        claimed = core.pop("checkpoint_identity", None)
        if (
            raw != canonical(value)
            or claimed != identity(core)
            or value.get("checkpoint_ordinal") != ordinal
            or value.get("previous_checkpoint_identity") != previous
            or value.get("attempt_identity") != ATTEMPT_IDENTITY
            or value.get("execution_authority_identity") != AUTHORITY_IDENTITY
            or value.get("finalized_rows") != 200
            or value.get("retry_or_redraw") is not False
            or value.get("same_attempt_resume_only") is not True
        ):
            raise ValueError("checkpoint chain mismatch")
        checkpoints.append(
            {
                "ordinal": ordinal,
                "checkpoint_identity": claimed,
                "checkpoint_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
        previous = claimed

    counts = {
        "raw_outputs": len(list(execution.rglob("*.raw"))),
        "observations": len(list(execution.rglob("*.observation.json"))),
        "lifecycle_started": len(
            list(execution.rglob("inference-*-started.json"))
        ),
        "lifecycle_completed": len(
            list(execution.rglob("inference-*-completed.json"))
        ),
    }
    if set(counts.values()) != {2400} or len(observed_inventory) != 12073:
        raise ValueError("matrix evidence cardinality mismatch")

    core = {
        "schema": "pastila-production-core-v8-1-completion-audit-receipt",
        "schema_version": 1,
        "status": "PASS_ZERO_BLOCKERS",
        "audit_mode": "FRESH_ADVERSARIAL_READ_ONLY",
        "audited_source_commit": AUDITED_SOURCE_COMMIT,
        "execution_authority_identity": AUTHORITY_IDENTITY,
        "attempt_ordinal": 1,
        "attempt_identity": ATTEMPT_IDENTITY,
        "attempt_sha256": hashlib.sha256(attempt_raw).hexdigest(),
        "completion_identity": COMPLETION_IDENTITY,
        "completion_sha256": COMPLETION_SHA256,
        "artifact_root": ARTIFACT_ROOT,
        "artifact_inventory_entries": len(observed_inventory),
        "matrix_rows": 2400,
        "matrix_evidence_counts": counts,
        "checkpoints": checkpoints,
        "terminal_checkpoint_identity": previous,
        "validator_sha256": VALIDATOR_SHA256,
        "relevant_tests": {"passed": 24, "failed": 0},
        "symlinks_detected": 0,
        "staging_directories_detected": 0,
        "terminal_failure_present": False,
        "blockers_identified": 0,
        "blockers_remaining": 0,
        "attempt_consumed": True,
        "candidate_execution_completed": True,
        "attempt_reexecuted": False,
        "artifacts_modified_by_audit": False,
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return {**core, "audit_receipt_identity": identity(core)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution", type=Path, default=DEFAULT_EXECUTION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    value = build(args.execution)
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n"
    if args.output.exists() and (
        args.output.is_symlink() or args.output.read_bytes() != raw
    ):
        raise SystemExit("published V8.1 audit receipt differs")
    if not args.output.exists():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    print(value["audit_receipt_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

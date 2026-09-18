"""V15 consumption entry: signed source closure before any attempt creation.

This module is never called by the fixture smoke. Its only consuming route is
explicit --consume-attempt, followed by V15 preflight and pinned mechanics.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
import sys
from pathlib import Path

import execute_production_core_candidate_qualification_v14 as predecessor
import preflight_production_core_candidate_qualification_v15 as gate
from pastila_scout import production_core_candidate_execution_authority_v15 as validator
from pastila_scout import production_core_checkpoint_resume_v6 as checkpoint
from pastila_scout import production_core_semantic_authority_v2 as semantic

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path("/root/pf9-v15-wsl-drivers-snapshot")
DRIVER_HELPER = ROOT / "src/pastila_scout/production_core_wsl_driver_snapshot_v15.py"
RUNNER = ROOT / "src/pastila_scout/production_core_candidate_qualification_runner_v14.py"
LAUNCHER = ROOT / "scripts/run_production_core_candidate_qualification_v15.sh"


def projected_mechanics() -> str:
    source = predecessor.projected_mechanics()
    old_key = '"scripts/execute_production_core_candidate_qualification_v14.py"'
    if source.count(old_key) != 1:
        raise ValueError("V15 executor source-key projection mismatch")
    source = source.replace(old_key, '"scripts/execute_production_core_candidate_qualification_v15.py"')
    old_args = "            wsl(RUNNER),\n        ]"
    new_args = (
        "            wsl(RUNNER),\n"
        "            str(SNAPSHOT),\n"
        "            str(DRIVER_HELPER),\n"
        "            hashlib.sha256(read(DRIVER_HELPER)).hexdigest(),\n"
        "        ]"
    )
    if source.count(old_args) != 1:
        raise ValueError("V15 16-argument driver projection mismatch")
    return source.replace(old_args, new_args)


def lock_directory(path: Path) -> int:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError):
        os.close(descriptor)
        raise SystemExit("V15 attempt output already owned") from None
    return descriptor


def atomic_no_replace(path: Path, data: bytes) -> None:
    """Durable no-clobber publication; especially protects attempt.json."""
    if path.exists() or path.is_symlink():
        raise SystemExit("V15 output collision")
    temporary = path.with_name("." + path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path, follow_symlinks=False)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except FileExistsError:
        raise SystemExit("V15 output collision") from None
    finally:
        temporary.unlink(missing_ok=True)


def build_namespace(boundary: dict) -> dict:
    if (LAUNCHER != ROOT / "scripts/run_production_core_candidate_qualification_v15.sh"
            or SNAPSHOT != Path("/root/pf9-v15-wsl-drivers-snapshot")
            or DRIVER_HELPER != ROOT / "src/pastila_scout/production_core_wsl_driver_snapshot_v15.py"):
        raise ValueError("V14 launcher or V15 driver path substitution")
    sources = boundary["source_sha256"]
    source_keys = (
        "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
        "scripts/execute_production_core_candidate_qualification_v15.py",
        "scripts/launch_production_core_candidate_qualification_v15.py",
        "scripts/preflight_production_core_candidate_qualification_v15.py",
        "scripts/resolve_production_core_object_authority_v2.sh",
        "scripts/run_production_core_candidate_qualification_v15.sh",
        "scripts/smoke_production_core_checkpoint_resume_v6.py",
        "src/pastila_scout/production_core_candidate_execution_authority_v15.py",
        "src/pastila_scout/production_core_candidate_qualification_runner_v14.py",
        "src/pastila_scout/production_core_checkpoint_resume_v6.py",
        "src/pastila_scout/production_core_semantic_authority_v2.py",
    )
    if any(name not in sources for name in source_keys):
        raise ValueError("V15 attempt executable source closure incomplete")
    namespace = {
        "__builtins__": __builtins__, "__file__": str(Path(__file__).resolve()),
        "__name__": "v15_pinned_mechanics",
        "PINNED_ENTRY_EXECUTOR_SHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "PINNED_TERMINAL_VALIDATOR": predecessor.terminal_validator,
        "PINNED_EXECUTION_MECHANISM": {
            "execution_authority_identity": boundary["boundary_identity"],
            "source_sha256": {name: sources[name] for name in source_keys},
        },
        "PINNED_ROOTFS_SHA256": validator.EXPECTED_OBJECTS[0][2],
        "PINNED_UNICODE_AUTHORITY_SHA256": validator.UNICODE_AUTHORITY_SHA256,
        "Unicode16SentenceAuthority": semantic.Unicode16SentenceAuthority,
        "validate_response_v2": semantic.validate_response_v2,
        "build_checkpoint_receipt": checkpoint.build_receipt,
        "validate_checkpoint_chain": checkpoint.validate_chain,
        "write_checkpoint_receipt": checkpoint.write_receipt,
    }
    for name in (
        "GENERATION_IDENTITY", "QUALIFICATION_IDENTITY", "MATRIX_ROWS", "build_attempt",
        "build_terminal_failure", "canonical", "identity", "materialize_batches",
        "result_status", "validate_attempt", "validate_boundary_logs", "validate_case_receipt",
        "validate_completion", "validate_observation", "validate_preflight", "validate_terminal_failure",
    ):
        namespace[name] = getattr(validator, name)
    exec(compile(projected_mechanics(), str(predecessor.MECHANICS), "exec"), namespace, namespace)  # noqa: S102
    namespace.update({
        "RUNNER": RUNNER, "LAUNCHER": LAUNCHER, "SNAPSHOT": SNAPSHOT, "DRIVER_HELPER": DRIVER_HELPER,
        "NAMES": predecessor.NAMES, "PROMPTS": predecessor.PROMPTS,
        "PROMPT_SHA256": predecessor.PROMPT_SHA256,
        "object_authority": predecessor.object_authority, "wsl": predecessor.linux_path,
        "validate_preflight": predecessor.validate_and_map,
        "lock_directory": lock_directory, "atomic": atomic_no_replace,
    })
    return namespace


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot", "unicode-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--consume-attempt", action="store_true", required=True)
    args = parser.parse_args()
    if args.snapshot != SNAPSHOT:
        raise SystemExit("V15 snapshot path mismatch")
    import audit_production_core_v15_attempt_execution_boundary as signed

    boundary = signed.audit(args.recovery, args.private, args.backup, args.v13_terminal,
                            args.terminal, args.rootfs, args.snapshot, args.output)["boundary"]
    gate.preflight(args.recovery, args.private, args.backup, args.v13_terminal,
                   args.terminal, args.rootfs, args.snapshot, args.unicode_root, args.output)
    previous = sys.argv
    try:
        sys.argv = [str(Path(__file__)), "--resolution", str(args.recovery / "v12-executor-resolution.json"),
                    "--secret", str(args.private / "candidate-alias-secret-v13.json"),
                    "--unicode-authority-root", str(args.unicode_root), "--output", str(args.output)]
        return build_namespace(boundary)["main"]()
    finally:
        sys.argv = previous


if __name__ == "__main__":
    raise SystemExit(main())

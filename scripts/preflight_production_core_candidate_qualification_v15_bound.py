"""Execution-bound V15 receipt; never invokes a candidate or creates an attempt."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import audit_production_core_v15_execution_bound_preflight as signed
import execute_production_core_candidate_qualification_v15 as mechanics
import materialize_production_core_v15_execution_bound_preflight as issuer
import preflight_production_core_candidate_qualification_v15 as legacy

ROOT = issuer.ROOT
SCHEMA = "pastila-production-core-v15-execution-bound-preflight-receipt"
LIFETIME_NS = 900_000_000_000


def current_publication(authority: dict) -> tuple[str, str]:
    ref = f"refs/heads/{issuer.BRANCH}"
    remote = issuer.git("ls-remote", "--heads", "origin", ref).split()
    if len(remote) != 2 or remote[1] != ref or remote[0] != issuer.git("rev-parse", "HEAD"):
        raise ValueError("execution-bound publication/ref drift")
    commit = remote[0]
    if subprocess.run(["git", "merge-base", "--is-ancestor", issuer.BASE_COMMIT, commit],
                      cwd=ROOT, capture_output=True).returncode:
        raise ValueError("execution-bound checkpoint ancestry drift")
    if issuer.git("show", "-s", "--format=%P", commit) != issuer.BASE_COMMIT:
        raise ValueError("execution-bound publication parent drift")
    published_files = set(issuer.git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
    required_files = set(issuer.NEW_SOURCES) | {
        f"docs/artifacts/production-core-v15-execution-bound-preflight/{name}"
        for name in ("authority.json", "binding.json", "binding.sig", "builder-source.py")
    }
    if published_files != required_files:
        raise ValueError("execution-bound publication scope drift")
    for name, expected in authority["source_sha256"].items():
        path = ROOT / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"execution-bound source drift: {name}")
        raw = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=ROOT)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"execution-bound unpublished source: {name}")
    for name in ("authority.json", "binding.json", "binding.sig", "builder-source.py"):
        relative = f"docs/artifacts/production-core-v15-execution-bound-preflight/{name}"
        path = ROOT / relative
        if path.read_bytes() != subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=ROOT):
            raise ValueError("execution-bound unpublished artifact")
    return commit, issuer.git("show", "-s", "--format=%T", commit)


def frozen_mechanics(authority: dict) -> None:
    if any(authority.get(key) != value for key, value in {
        "input_token_cap": 1924, "max_new_tokens": 6268,
        "decoded_response_byte_cap": 6268, "runner_wall_ns": 600_000_000_000,
        "runner_max_rss_bytes": 16_106_127_360, "matrix_rows": 2400,
        "batch_count": 12, "rows_per_batch": 200,
    }.items()):
        raise ValueError("frozen V15 qualification/resource limits drift")
    source = mechanics.projected_mechanics()
    assignments = [node.value for node in ast.walk(ast.parse(source))
                   if isinstance(node, ast.Assign) and isinstance(node.value, ast.List)
                   and any(isinstance(target, ast.Name) and target.id == "command" for target in node.targets)]
    if len(assignments) != 1:
        raise ValueError("V15 shell command projection missing")
    args = assignments[0].elts
    marker = next((i for i, node in enumerate(args) if isinstance(node, ast.Constant) and node.value == "--"), None)
    if marker is None or len(args[marker + 1:]) != 16 or authority["shell_argument_count"] != 16:
        raise ValueError("V15 16-argument projection drift")
    if (mechanics.LAUNCHER.name != "run_production_core_candidate_qualification_v15.sh"
            or mechanics.RUNNER.name != "production_core_candidate_qualification_runner_v14.py"):
        raise ValueError("V14 shell/executor substitution")
    runner = (ROOT / "src/pastila_scout/production_core_candidate_qualification_runner_v14.py").read_bytes()
    runner_source = runner.decode()
    for witness in ("MAX_INPUT = 1924", "MAX_OUTPUT = 6268", "size > 6268",
                    "len(output) <= 6268", "MAX_WALL_NS = 600_000_000_000",
                    "MAX_RSS = 16_106_127_360", "torch.use_deterministic_algorithms(True)"):
        if witness not in runner_source:
            raise ValueError("frozen runner/resource limit drift")
    if hashlib.sha256(runner).hexdigest() != authority["runner_sha256"]:
        raise ValueError("frozen runner identity drift")


def core_for(authority: dict, signed_report: dict, old_receipt: dict, commit: str,
             tree: str, output_state: dict, issued: int) -> dict:
    return {
        "schema": SCHEMA, "schema_version": 1, "verdict": "PASS + 0 BLOCKERS",
        "published_commit": commit, "published_tree": tree,
        "published_base_commit": issuer.BASE_COMMIT, "published_base_tree": issuer.BASE_TREE,
        "authority_identity": signed_report["authority_identity"],
        "binding_identity": signed_report["binding_identity"],
        "signature_identity": signed_report["signature_identity"],
        "base_authority_identity": issuer.BASE_AUTHORITY,
        "legacy_preflight_identity": old_receipt["preflight_identity"],
        "bound_executor_sha256": authority["bound_executor_sha256"],
        "mechanics_executor_sha256": authority["mechanics_executor_sha256"],
        "validator_sha256": authority["validator_sha256"],
        "shell_sha256": authority["shell_sha256"],
        "v13_secret_sha256": authority["alias_secret_commitment"],
        "qualification_generation_identity": authority["qualification_generation_identity"],
        "qualification_identity": authority["qualification_identity"],
        "schedule_sha256": authority["schedule_sha256"],
        "driver_snapshot": authority["driver_snapshot"],
        "runtime_object_authority_identity": authority["runtime_object_authority_identity"],
        "rootfs_sha256": authority["rootfs_sha256"],
        "v14_terminal_failure_sha256": authority["v14_terminal_evidence"]["terminal_failure_sha256"],
        "matrix_rows": 2400, "batch_count": 12, "rows_per_batch": 200,
        "request_count": 200, "candidate_count": 2, "materialization_count": 2, "repetition_count": 3,
        "input_token_cap": 1924, "max_new_tokens": 6268, "decoded_response_byte_cap": 6268,
        "runner_wall_ns": authority["runner_wall_ns"],
        "runner_max_rss_bytes": authority["runner_max_rss_bytes"],
        "shell_argument_count": 16, "output": output_state, "attempt_json": "ABSENT",
        "issued_at_ns": issued, "expires_at_ns": issued + LIFETIME_NS,
        "issuer_pid": os.getpid(), "candidate_execution": 0, "attempt_consumption": 0,
        "adjudication": False, "promotion": False,
    }


def issue(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path, unicode_root: Path, output: Path) -> dict:
    if not output.is_absolute() or output != output.resolve(strict=True):
        raise ValueError("execution-bound output path must be canonical")
    report = signed.audit(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot, output)
    authority = report["authority"]
    commit, tree = current_publication(authority)
    frozen_mechanics(authority)
    old = legacy.preflight(recovery, private, backup, v13_terminal, terminal, rootfs,
                           snapshot, unicode_root, output)
    if old["preflight_identity"] != authority["legacy_preflight_receipt_identity"]:
        raise ValueError("old V15 preflight receipt drift")
    secret = private / "candidate-alias-secret-v13.json"
    if secret.is_symlink() or hashlib.sha256(secret.read_bytes()).hexdigest() != authority["alias_secret_commitment"]:
        raise ValueError("V13 secret commitment mismatch")
    output_state = legacy.empty_output(output, (ROOT, recovery, private, backup, v13_terminal,
                                                 terminal, rootfs, snapshot, unicode_root))
    if output_state != authority["output"] or (output / "attempt.json").exists():
        raise ValueError("execution-bound output identity/state drift")
    issued = time.time_ns()
    core = core_for(authority, report, old, commit, tree, output_state, issued)
    return {**core, "receipt_identity": issuer.digest(issuer.canonical(core))}


def verify_receipt(receipt: dict, authority: dict, expected: dict,
                   private: Path, output: Path, protected: tuple[Path, ...]) -> None:
    if not isinstance(receipt, dict) or receipt != expected:
        raise ValueError("execution-bound receipt substitution")
    core = dict(receipt)
    claimed = core.pop("receipt_identity", None)
    if (claimed != issuer.digest(issuer.canonical(core)) or receipt.get("schema") != SCHEMA
            or receipt.get("authority_identity") != authority["authority_identity"]
            or receipt.get("legacy_preflight_identity") != authority["legacy_preflight_receipt_identity"]
            or receipt.get("issuer_pid") != os.getpid()):
        raise ValueError("execution-bound receipt identity rejected")
    now = time.time_ns()
    if not receipt["issued_at_ns"] <= now <= receipt["expires_at_ns"]:
        raise ValueError("execution-bound receipt stale")
    if current_publication(authority) != (receipt["published_commit"], receipt["published_tree"]):
        raise ValueError("execution-bound publication changed")
    if legacy.empty_output(output, protected) != receipt["output"] or (output / "attempt.json").exists():
        raise ValueError("execution-bound output changed")
    secret = private / "candidate-alias-secret-v13.json"
    if secret.is_symlink() or hashlib.sha256(secret.read_bytes()).hexdigest() != receipt["v13_secret_sha256"]:
        raise ValueError("execution-bound V13 secret changed")


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot", "unicode-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    print(json.dumps(issue(a.recovery, a.private, a.backup, a.v13_terminal, a.terminal,
                           a.rootfs, a.snapshot, a.unicode_root, a.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

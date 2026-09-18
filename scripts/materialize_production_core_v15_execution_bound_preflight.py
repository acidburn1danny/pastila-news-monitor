"""Sign the successor V15 execution-bound preflight without an attempt."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import audit_production_core_v15_attempt_execution_boundary as predecessor
import materialize_production_core_successor_execution_authority_v12 as signing

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v15-execution-bound-preflight"
BASE_COMMIT = "f1cf2967705d29e53fb2e5eccc7459aecc2b43fc"
BASE_TREE = "bb8f4e878adbda7482f78dae2d42eb9804278f2a"
BASE_AUTHORITY = "ece20fab771e4e1ce4d93df897e2b68b87d8ccc210b12f020b33d9a0b4066db1"
BASE_BINDING = "90d63629d7251c661ed9f1dd608f3c0e306d8516459ba548122257bc596d2b0c"
BASE_SIGNATURE = "d5585c33fdb35a9dd0971733509f961c7ed35dc86428468a9b773c28eb8fed7b"
BRANCH = "successor/core-v2-v12-runner-binding-remediation"
NEW_SOURCES = (
    "docs/production-core-v15-execution-bound-preflight.md",
    "scripts/audit_production_core_v15_execution_bound_preflight.py",
    "scripts/execute_production_core_candidate_qualification_v15_bound.py",
    "scripts/launch_production_core_candidate_qualification_v15_bound.py",
    "scripts/materialize_production_core_v15_execution_bound_preflight.py",
    "scripts/preflight_production_core_candidate_qualification_v15_bound.py",
    "tests/test_production_core_v15_execution_bound_preflight.py",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def published_base() -> tuple[str, ...]:
    if git("rev-parse", f"{BASE_COMMIT}^{{tree}}") != BASE_TREE:
        raise ValueError("V15 execution checkpoint tree drift")
    if subprocess.run(["git", "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD"],
                      cwd=ROOT, capture_output=True).returncode:
        raise ValueError("V15 execution checkpoint HEAD ancestry drift")
    remote = git("ls-remote", "--heads", "origin", f"refs/heads/{BRANCH}").split()
    if (len(remote) != 2 or remote[1] != f"refs/heads/{BRANCH}"
            or subprocess.run(["git", "merge-base", "--is-ancestor", BASE_COMMIT, remote[0]],
                              cwd=ROOT, capture_output=True).returncode):
        raise ValueError("V15 execution checkpoint remote drift")
    names = tuple(git("diff-tree", "--no-commit-id", "--name-only", "-r", BASE_COMMIT).splitlines())
    if len(names) != 12 or not all(name.startswith(("docs/", "scripts/", "src/", "tests/")) for name in names):
        raise ValueError("V15 execution checkpoint file scope drift")
    for name in names:
        path = ROOT / name
        if path.is_symlink() or path.read_bytes() != subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{name}"], cwd=ROOT):
            raise ValueError(f"V15 published blob drift: {name}")
    return names


def source_closure() -> dict[str, str]:
    names = published_base()
    rows = {}
    for name in (*names, *NEW_SOURCES):
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"V15 bound source missing: {name}")
        rows[name] = digest(path.read_bytes())
    return rows


def build(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path, output: Path) -> dict:
    sources = source_closure()
    old = predecessor.audit(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot, output)
    if any(old.get(k) != v for k, v in {
        "verdict": "PASS + 0 BLOCKERS", "boundary_identity": BASE_AUTHORITY,
        "binding_identity": BASE_BINDING, "signature_identity": BASE_SIGNATURE,
        "ed25519_verification": "PASS", "source_closure": "PASS",
        "runtime_object_closure": "PASS", "snapshot_closure": "PASS",
        "v14_terminal_closure": "PASS", "output": "EMPTY_NATIVE_EXT4",
        "candidate_execution": "0", "attempt_consumption": "0",
    }.items()):
        raise ValueError("published V15 attempt boundary rejected")
    base = old["boundary"]
    if source_closure() != sources:
        raise ValueError("source changed during bound preflight construction")
    core = {
        "schema": "pastila-production-core-v15-execution-bound-preflight-authority",
        "schema_version": 1, "status": "NO_CANDIDATE_NO_ATTEMPT",
        "published_base_commit": BASE_COMMIT, "published_base_tree": BASE_TREE,
        "published_base_blobs": {name: sources[name] for name in published_base()},
        "base_authority_identity": BASE_AUTHORITY, "base_binding_identity": BASE_BINDING,
        "base_signature_identity": BASE_SIGNATURE,
        "v15_authority_identity": base["v15_authority_identity"],
        "v15_binding_identity": base["v15_binding_identity"],
        "v15_signature_identity": base["v15_signature_identity"],
        "published_preflight_commit": base["published_v15_preflight_commit"],
        "published_preflight_source_sha256": base["preflight_source_sha256"],
        "legacy_preflight_receipt_identity": base["preflight_receipt_identity"],
        "qualification_generation_identity": base["qualification_generation_identity"],
        "qualification_identity": base["qualification_identity"],
        "schedule_sha256": base["schedule_sha256"],
        "alias_secret_commitment": base["alias_secret_commitment"],
        "runtime_object_authority_identity": base["runtime_object_authority_identity"],
        "rootfs_sha256": base["rootfs_sha256"],
        "driver_snapshot": base["driver_snapshot"], "output": base["output"],
        "v14_terminal_evidence": base["v14_terminal_evidence"],
        "runner_sha256": base["runner_sha256"], "shell_sha256": base["launcher_sha256"],
        "mechanics_executor_sha256": base["executor_sha256"],
        "validator_sha256": base["validator_sha256"],
        "bound_executor_sha256": sources["scripts/execute_production_core_candidate_qualification_v15_bound.py"],
        "bound_preflight_sha256": sources["scripts/preflight_production_core_candidate_qualification_v15_bound.py"],
        "shell_argument_count": 16, "matrix_rows": 2400, "batch_count": 12,
        "rows_per_batch": 200, "input_token_cap": 1924,
        "max_new_tokens": 6268, "decoded_response_byte_cap": 6268,
        "runner_wall_ns": 600_000_000_000, "runner_max_rss_bytes": 16_106_127_360,
        "attempt_claim": base["attempt_claim"], "resume_policy": base["resume_policy"],
        "source_sha256": sources, "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "candidate_execution": 0, "attempt_consumption": 0,
        "adjudication": False, "promotion": False,
    }
    return {**core, "authority_identity": digest(canonical(core))}


def binding_for(authority: dict, raw: bytes) -> dict:
    return {
        "schema": "pastila-production-core-v15-execution-bound-preflight-binding",
        "schema_version": 1, "algorithm": "Ed25519",
        "authority_identity": authority["authority_identity"], "authority_sha256": digest(raw),
        "published_base_commit": BASE_COMMIT, "base_authority_identity": BASE_AUTHORITY,
        "bound_executor_sha256": authority["bound_executor_sha256"],
        "bound_preflight_sha256": authority["bound_preflight_sha256"],
        "validator_sha256": authority["validator_sha256"],
        "shell_sha256": authority["shell_sha256"], "driver_snapshot": authority["driver_snapshot"],
        "output": authority["output"], "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "candidate_execution": 0, "attempt_consumption": 0,
    }


def materialize(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
                terminal: Path, rootfs: Path, snapshot: Path, output: Path, key: Path) -> dict:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise ValueError("bound preflight authority already exists")
    signing.verify_key(key)
    authority = build(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot, output)
    raw = json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    bound = canonical(binding_for(authority, raw))
    with tempfile.TemporaryDirectory(prefix=".v15-bound-", dir=OUTPUT.parent) as temporary:
        staging = Path(temporary) / "payload"
        staging.mkdir()
        (staging / "authority.json").write_bytes(raw)
        (staging / "binding.json").write_bytes(bound)
        (staging / "builder-source.py").write_bytes(Path(__file__).read_bytes())
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(key), "-rawin",
                        "-in", str(staging / "binding.json"), "-out", str(staging / "binding.sig")],
                       check=True, capture_output=True)
        subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY),
                        "-rawin", "-in", str(staging / "binding.json"),
                        "-sigfile", str(staging / "binding.sig")], check=True, capture_output=True)
        result = {"authority_identity": authority["authority_identity"],
                  "binding_identity": digest(bound),
                  "signature_identity": digest((staging / "binding.sig").read_bytes())}
        os.replace(staging, OUTPUT)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot", "output", "private-key"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    print(json.dumps(materialize(a.recovery, a.private, a.backup, a.v13_terminal,
                                 a.terminal, a.rootfs, a.snapshot, a.output, a.private_key), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

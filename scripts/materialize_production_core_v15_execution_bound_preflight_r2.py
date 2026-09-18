"""Sign the successor V15 execution-bound preflight without an attempt."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import audit_production_core_v15_execution_bound_preflight as predecessor
import materialize_production_core_successor_execution_authority_v12 as signing

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v15-execution-bound-preflight-r2"
BASE_COMMIT = "c060df236c416dd9ef7d62c987205973da7767a9"
BASE_TREE = "9f2bd9a0fbddb954ed04f951988adfdf7021180f"
BASE_AUTHORITY = "41114ad21042d406bbed292dc24b04fa4e01e22aa8f2bf0ff4a4434d566ed2f6"
BASE_BINDING = "057714cee9cc3cf5ec4b43ea670990fcc6dd5b53f025c7004e949001428b2d07"
BASE_SIGNATURE = "aac2c3654dc28beba3076d6afe0e034704e208c60565dd15d5f342790fe30957"
BRANCH = "successor/core-v2-v12-runner-binding-remediation"
NEW_SOURCES = (
    "docs/production-core-v15-execution-bound-preflight-r2.md",
    "scripts/audit_production_core_v15_execution_bound_preflight_r2.py",
    "scripts/execute_production_core_candidate_qualification_v15_bound_r2.py",
    "scripts/launch_production_core_candidate_qualification_v15_bound_r2.py",
    "scripts/materialize_production_core_v15_execution_bound_preflight_r2.py",
    "scripts/preflight_production_core_candidate_qualification_v15_bound_r2.py",
    "tests/test_production_core_v15_execution_bound_preflight_r2.py",
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
    if len(names) != 11 or not all(name.startswith(("docs/", "scripts/", "src/", "tests/")) for name in names):
        raise ValueError("V15 execution checkpoint file scope drift")
    for name in names:
        path = ROOT / name
        if path.is_symlink() or path.read_bytes() != subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{name}"], cwd=ROOT):
            raise ValueError(f"V15 published blob drift: {name}")
    return names


def execution_source_keys() -> tuple[str, ...]:
    """Derive the consuming executor's required map from its pinned source."""
    path = ROOT / "scripts/execute_production_core_candidate_qualification_v15.py"
    module = ast.parse(path.read_bytes())
    functions = [node for node in module.body if isinstance(node, ast.FunctionDef)
                 and node.name == "build_namespace"]
    if len(functions) != 1:
        raise ValueError("V15 consuming source declaration missing")
    declarations = [node.value for node in functions[0].body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "source_keys"
                            for target in node.targets)]
    if len(declarations) != 1:
        raise ValueError("V15 consuming source list missing")
    keys = ast.literal_eval(declarations[0])
    if not isinstance(keys, tuple) or len(keys) != len(set(keys)):
        raise ValueError("V15 consuming source list invalid")
    return keys


def inherited_maps() -> tuple[dict[str, str], dict[str, str]]:
    a1 = json.loads((ROOT / "docs/artifacts/production-core-v15-attempt-execution-boundary/boundary.json").read_bytes())
    a2 = json.loads((ROOT / "docs/artifacts/production-core-v15-execution-bound-preflight/authority.json").read_bytes())
    if (a1.get("boundary_identity") != a2.get("base_authority_identity")
            or a2.get("authority_identity") != BASE_AUTHORITY):
        raise ValueError("predecessor source authority identity drift")
    return a1["source_sha256"], a2["source_sha256"]


def source_closure() -> dict[str, str]:
    published_base()
    inherited = inherited_maps()
    rows: dict[str, str] = {}
    for manifest in inherited:
        for name, expected in manifest.items():
            if name in rows and rows[name] != expected:
                raise ValueError(f"inherited source conflict: {name}")
            rows[name] = expected
    for name in NEW_SOURCES:
        if name in rows:
            raise ValueError(f"successor source overlaps predecessor: {name}")
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"successor source missing: {name}")
        rows[name] = digest(path.read_bytes())
    expected_names = set(inherited[0]) | set(inherited[1]) | set(NEW_SOURCES)
    if set(rows) != expected_names or not set(execution_source_keys()).issubset(rows):
        raise ValueError("V15 consuming source closure incomplete or expanded")
    for name, expected in rows.items():
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError(f"V15 execution-critical source drift: {name}")
    return dict(sorted(rows.items()))


def build(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path, output: Path) -> dict:
    sources = source_closure()
    old = predecessor.audit(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot, output)
    if any(old.get(k) != v for k, v in {
        "verdict": "PASS + 0 BLOCKERS", "authority_identity": BASE_AUTHORITY,
        "binding_identity": BASE_BINDING, "signature_identity": BASE_SIGNATURE,
        "ed25519_verification": "PASS", "source_closure": "PASS",
        "runtime_object_closure": "PASS", "snapshot_closure": "PASS",
        "output": "EMPTY_NATIVE_EXT4",
    }.items()):
        raise ValueError("published V15 attempt boundary rejected")
    base = old["authority"]
    if source_closure() != sources:
        raise ValueError("source changed during bound preflight construction")
    core = {
        "schema": "pastila-production-core-v15-execution-bound-preflight-r2-authority",
        "schema_version": 1, "status": "NO_CANDIDATE_NO_ATTEMPT",
        "published_base_commit": BASE_COMMIT, "published_base_tree": BASE_TREE,
        "published_base_blobs": {name: digest(subprocess.check_output(
            ["git", "show", f"{BASE_COMMIT}:{name}"], cwd=ROOT)) for name in published_base()},
        "base_authority_identity": BASE_AUTHORITY, "base_binding_identity": BASE_BINDING,
        "base_signature_identity": BASE_SIGNATURE,
        "v15_authority_identity": base["v15_authority_identity"],
        "v15_binding_identity": base["v15_binding_identity"],
        "v15_signature_identity": base["v15_signature_identity"],
        "published_preflight_commit": base["published_preflight_commit"],
        "published_preflight_source_sha256": base["published_preflight_source_sha256"],
        "legacy_preflight_receipt_identity": base["legacy_preflight_receipt_identity"],
        "qualification_generation_identity": base["qualification_generation_identity"],
        "qualification_identity": base["qualification_identity"],
        "schedule_sha256": base["schedule_sha256"],
        "alias_secret_commitment": base["alias_secret_commitment"],
        "runtime_object_authority_identity": base["runtime_object_authority_identity"],
        "rootfs_sha256": base["rootfs_sha256"],
        "driver_snapshot": base["driver_snapshot"], "output": base["output"],
        "v14_terminal_evidence": base["v14_terminal_evidence"],
        "runner_sha256": base["runner_sha256"], "shell_sha256": base["shell_sha256"],
        "mechanics_executor_sha256": base["mechanics_executor_sha256"],
        "validator_sha256": base["validator_sha256"],
        "bound_executor_sha256": sources["scripts/execute_production_core_candidate_qualification_v15_bound_r2.py"],
        "bound_preflight_sha256": sources["scripts/preflight_production_core_candidate_qualification_v15_bound_r2.py"],
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
        "schema": "pastila-production-core-v15-execution-bound-preflight-r2-binding",
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

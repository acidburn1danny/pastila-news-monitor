"""Build and verify a zero-attempt V12 authority from the published recovery."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import stat
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

import materialize_production_core_v12_recovery_runtime as recovery_runtime

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "5a94ab6601d7f37a5b50f345592aacd404d3f621"
TREE = "5527fbd0f36018f5687d6abc7f77574073c6a987"
RUNNER = "b7073a3b75036e5be26aa4b1d9546aa9f012370168a74df552b648708e399e29"
RESOLUTION = "7623e67ceeeb42fc42f18a329d825311ddc723046595201060b6d0f638f81e77"
PUBLIC_KEY = ROOT / "docs/artifacts/production-core-v8-1-signing-public.pem"
PUBLIC_PEM_SHA256 = "093b000881cc8e5a3d6167932d352d4cac3d7b4c448d0536f49cff9628d7d3a2"
SOURCES = (
    "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json",
    "scripts/audit_production_core_v12_recovery_runtime.py",
    "scripts/execute_production_core_candidate_qualification_v11.py",
    "scripts/launch_production_core_candidate_qualification_v11.py",
    "scripts/materialize_production_core_v12_recovery_runtime.py",
    "scripts/resolve_production_core_object_authority_v2.sh",
    "src/pastila_scout/production_core_candidate_execution_authority_v11.py",
    "src/pastila_scout/production_core_candidate_qualification_runner_v12.py",
)
EXPECTED_ENTRIES = {
    "adapters", "models", "rootfs", "tokenizers",
    "v12-executor-resolution.json", "v12-recovery-runtime-resolution.json",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT).strip()


def source_closure() -> dict[str, str]:
    if git("rev-parse", "HEAD").decode() != COMMIT or git("rev-parse", f"{COMMIT}^{{tree}}").decode() != TREE:
        raise ValueError("published source commit or tree mismatch")
    if git("rev-parse", "refs/remotes/origin/successor/core-v2-v12-runner-binding-remediation").decode() != COMMIT:
        raise ValueError("published recovery branch mismatch")
    observed = {}
    for name in SOURCES:
        committed = subprocess.check_output(["git", "show", f"{COMMIT}:{name}"], cwd=ROOT)
        path = ROOT / name
        if path.is_symlink() or path.read_bytes() != committed:
            raise ValueError(f"source closure mismatch: {name}")
        observed[name] = digest(committed)
    if observed["src/pastila_scout/production_core_candidate_qualification_runner_v12.py"] != RUNNER:
        raise ValueError("V12 runner identity mismatch")
    if recovery_runtime.sha256_file(PUBLIC_KEY) != PUBLIC_PEM_SHA256:
        raise ValueError("signing public key identity mismatch")
    return observed


def runtime_closure(root: Path) -> tuple[dict, dict, dict]:
    if os.name == "nt" or root.is_symlink() or not root.is_dir() or str(root).startswith("/mnt/"):
        raise ValueError("authority requires an isolated native ext4 recovery root")
    if {item.name for item in root.iterdir()} != EXPECTED_ENTRIES:
        raise ValueError("recovery root contains hidden or missing state")
    recovery_path = root / "v12-recovery-runtime-resolution.json"
    projection_path = root / "v12-executor-resolution.json"
    if recovery_path.is_symlink() or projection_path.is_symlink():
        raise ValueError("symlink recovery artifact")
    recovery_raw = recovery_path.read_bytes()
    projection_raw = projection_path.read_bytes()
    recovery = json.loads(recovery_raw)
    projection = json.loads(projection_raw)
    if recovery.get("resolution_identity") != RESOLUTION or recovery.get("runner_identity") != RUNNER:
        raise ValueError("canonical V12 recovery identity mismatch")
    recovery_runtime.audit_recovery_resolution(recovery, projection)
    if type(recovery["candidate_execution"]) is not int or recovery["candidate_execution"] != 0 or type(recovery["successor_attempt_consumption"]) is not int or recovery["successor_attempt_consumption"] != 0 or recovery["adjudication"] is not False or recovery["promotion"] is not False:
        raise ValueError("recovery execution state mismatch")
    helper = (ROOT / "scripts/resolve_production_core_object_authority_v2.sh").read_bytes()
    all_paths = [path for local in projection["materializations"].values() for path in (local["rootfs_tar"], local["model"], *local["adapters"].values())]
    common = PurePosixPath(posixpath.commonpath(all_paths))
    if common != PurePosixPath(str(root.resolve())):
        raise ValueError("runtime projection root substitution")
    observed: dict[str, dict] = {}
    physical_seen: set[str] = set()
    for label, local in projection["materializations"].items():
        checks = [
            ("rootfs", local["rootfs_tar"], "file", recovery_runtime.EXPECTED_ROOTFS),
            ("model", local["model"], "flat-dir", recovery_runtime.EXPECTED_BASE),
            *((name, path, "flat-dir", recovery_runtime.EXPECTED_ADAPTERS[name]) for name, path in local["adapters"].items()),
        ]
        observed[label] = {}
        for role, path, kind, expected in checks:
            current = PurePosixPath(path)
            while True:
                item = Path(current)
                if item.is_symlink() or item.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
                    raise ValueError(f"writable or substituted runtime path: {label}/{role}")
                if current == common:
                    break
                current = current.parent
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-s", "--", path, kind],
                input=helper, capture_output=True, check=True,
            )
            value = json.loads(result.stdout)
            if tuple(value) != ("physical_identity", "content_identity") or value["content_identity"] != expected:
                raise ValueError(f"executor object authority mismatch: {label}/{role}")
            if role != "rootfs":
                if value["physical_identity"] in physical_seen:
                    raise ValueError("A/B physical materialization overlap")
                physical_seen.add(value["physical_identity"])
            observed[label][role] = {"path": path, "kind": kind, **value}
    return recovery, projection, {
        "recovery_resolution_sha256": digest(recovery_raw),
        "executor_projection_sha256": digest(projection_raw),
        "objects": observed,
    }


def build(root: Path) -> dict:
    sources = source_closure()
    recovery, projection, runtime = runtime_closure(root)
    core = {
        "schema": "pastila-production-core-successor-execution-authority-v12",
        "schema_version": 1,
        "status": "FROZEN_V12_RECOVERY_BOUND_ZERO_ATTEMPTS",
        "bound_source_commit": COMMIT,
        "bound_source_tree": TREE,
        "runner_v12_identity": RUNNER,
        "recovery_resolution_identity": RESOLUTION,
        "recovery_manifest_identity": recovery["source_recovery_manifest_identity"],
        "source_sha256": sources,
        "builder_sha256": recovery_runtime.sha256_file(Path(__file__)),
        "runtime_object_resolution": projection,
        "runtime_object_closure": runtime,
        "public_key_pem_sha256": PUBLIC_PEM_SHA256,
        "candidate_execution": 0,
        "successor_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
        "candidate_execution_authorized": False,
        "attempt_consumption_authorized": False,
    }
    return {**core, "authority_identity": digest(canonical(core))}


def binding_for(authority: dict, raw: bytes) -> dict:
    return {
        "schema": "pastila-production-core-v12-recovery-detached-authority-binding",
        "schema_version": 1,
        "algorithm": "Ed25519",
        "authority_identity": authority["authority_identity"],
        "authority_sha256": digest(raw),
        "bound_source_commit": COMMIT,
        "bound_source_tree": TREE,
        "runner_v12_identity": RUNNER,
        "recovery_resolution_identity": RESOLUTION,
        "executor_projection_sha256": authority["runtime_object_closure"]["executor_projection_sha256"],
        "builder_sha256": authority["builder_sha256"],
        "public_key_pem_sha256": PUBLIC_PEM_SHA256,
        "candidate_execution": 0,
        "successor_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
    }


def verify_key(private_key: Path) -> None:
    if private_key.is_symlink() or not private_key.is_file():
        raise ValueError("private signing key unavailable")
    derived = subprocess.check_output(["openssl", "pkey", "-in", str(private_key), "-pubout", "-outform", "DER"])
    public = subprocess.check_output(["openssl", "pkey", "-pubin", "-in", str(PUBLIC_KEY), "-outform", "DER"])
    if derived != public:
        raise ValueError("private key does not match canonical public key")


def materialize(root: Path, output: Path, private_key: Path) -> dict[str, str]:
    if output.exists() or output.is_symlink():
        raise ValueError("authority output root must be new")
    verify_key(private_key)
    authority = build(root)
    raw = json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    binding_raw = canonical(binding_for(authority, raw))
    with tempfile.TemporaryDirectory(prefix=".v12-authority-", dir=output.parent) as temporary:
        staging = Path(temporary) / "payload"
        staging.mkdir()
        (staging / "authority.json").write_bytes(raw)
        (staging / "binding.json").write_bytes(binding_raw)
        (staging / "builder-source.py").write_bytes(Path(__file__).read_bytes())
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private_key), "-rawin", "-in", str(staging / "binding.json"), "-out", str(staging / "binding.sig")], check=True)
        subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(PUBLIC_KEY), "-rawin", "-in", str(staging / "binding.json"), "-sigfile", str(staging / "binding.sig")], check=True, capture_output=True)
        signature = (staging / "binding.sig").read_bytes()
        if len(signature) != 64:
            raise ValueError("Ed25519 signature length mismatch")
        result = {
            "authority_identity": authority["authority_identity"],
            "binding_identity": digest(binding_raw),
            "signature_identity": digest(signature),
        }
        os.replace(staging, output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.recovery_root, args.output_root, args.private_key), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

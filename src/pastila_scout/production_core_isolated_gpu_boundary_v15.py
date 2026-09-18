"""Read-only successor design gate for the V14 isolated-GPU failure.

This module has no attempt creation or candidate execution path. A passing probe
is evidence for boundary design only, never an execution authorization.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from pastila_scout import production_core_candidate_execution_authority_v14 as validator

ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "157319d408066b78501ba505773e492cd1c260cc"
SOURCE_TREE = "d18f4c872095e5fec9e45c4e43af4d1f296e2e53"
AUTHORITY = "27955b01b3254a08679b200a3f20d4c5d382f582834b98119f701f37cc86b5ec"
ATTEMPT = "178c4bab01fcd9b259251930f45a3311506ba15689ba700492a103a2185ebd98"
FAILURE = "f015000e13c2a3035b77a5c68cced755617407d1d4d0f84b67a3f9085e0c07b4"
ROOTFS = "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
SHELL = ROOT / "scripts/probe_production_core_isolated_gpu_v15.sh"
HOST_DRIVERS = Path("/usr/lib/wsl/drivers")
V14_FILES = (
    "src/pastila_scout/production_core_candidate_qualification_runner_v14.py",
    "scripts/run_production_core_candidate_qualification_v14.sh",
    "scripts/preflight_production_core_candidate_qualification_v14.py",
    "scripts/launch_production_core_candidate_qualification_v14.py",
    "src/pastila_scout/production_core_qualification_supervisor_v14.py",
    "docs/artifacts/production-core-v14-successor-attempt-authority/authority.json",
    "docs/artifacts/production-core-v14-successor-attempt-authority/binding.json",
    "docs/artifacts/production-core-v14-successor-attempt-authority/binding.sig",
    "docs/artifacts/production-core-v14-preconsumption-launcher-boundary/boundary.json",
    "docs/artifacts/production-core-v14-preconsumption-launcher-boundary/binding.json",
    "docs/artifacts/production-core-v14-preconsumption-launcher-boundary/binding.sig",
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def driver_manifest() -> dict[str, object]:
    if HOST_DRIVERS.is_symlink() or not HOST_DRIVERS.is_dir():
        raise ValueError("host WSL driver directory rejected")
    rows = []
    for path in sorted(HOST_DRIVERS.rglob("*"), key=lambda p: p.relative_to(HOST_DRIVERS).as_posix()):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError("host WSL driver entry substitution")
        if path.is_file():
            rows.append([path.relative_to(HOST_DRIVERS).as_posix(), path.stat().st_size, sha_file(path)])
    if not rows:
        raise ValueError("host WSL driver directory empty")
    return {"file_count": len(rows), "manifest_identity": sha(canonical(rows))}


def source_closure() -> dict[str, str]:
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", *args], cwd=ROOT).strip()

    if git("rev-parse", f"{SOURCE_COMMIT}^{{tree}}").decode() != SOURCE_TREE:
        raise ValueError("V14 published tree mismatch")
    for revision in ("HEAD", "refs/remotes/origin/successor/core-v2-v12-runner-binding-remediation"):
        if subprocess.run(["git", "merge-base", "--is-ancestor", SOURCE_COMMIT, revision], cwd=ROOT).returncode:
            raise ValueError("V14 published commit is not in source ancestry")
    hashes = {}
    for name in V14_FILES:
        path = ROOT / name
        committed = subprocess.check_output(["git", "show", f"{SOURCE_COMMIT}:{name}"], cwd=ROOT)
        if path.is_symlink() or not path.is_file() or path.read_bytes() != committed:
            raise ValueError(f"V14 published source drift: {name}")
        hashes[name] = sha(committed)
    return hashes


def terminal_closure(root: Path) -> dict[str, object]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("V14 terminal root rejected")
    paths = tuple(root.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("V14 terminal symlink rejected")
    attempt_path, failure_path = root / "attempt.json", root / "terminal-failure.json"
    attempt_raw, failure_raw = attempt_path.read_bytes(), failure_path.read_bytes()
    attempt, failure = json.loads(attempt_raw), json.loads(failure_raw)
    validator.validate_attempt(attempt, AUTHORITY)
    partial = sorted((
        {"path": p.relative_to(root).as_posix(), "sha256": sha(p.read_bytes())}
        for p in paths if p.is_file() and p != failure_path
    ), key=lambda row: row["path"])
    validator.validate_terminal_failure(failure, attempt, partial)
    if (attempt.get("attempt_identity") != ATTEMPT
            or failure.get("terminal_failure_identity") != FAILURE
            or failure.get("failure_class") != "UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION"
            or failure.get("failed_batch") != {"materialization": "A", "repetition": 1, "candidate_alias": "CANDIDATE-A"}
            or failure.get("completed_rows") != 0
            or failure.get("partial_artifact_count") != 5
            or (root / "completion.json").exists()
            or list(root.glob("checkpoint-*.json"))):
        raise ValueError("V14 terminal state mismatch")
    return {
        "attempt_identity": ATTEMPT,
        "attempt_sha256": sha(attempt_raw),
        "terminal_failure_identity": FAILURE,
        "terminal_failure_sha256": sha(failure_raw),
        "partial_artifact_root": failure["partial_artifact_root"],
        "accepted_rows": 0,
        "accepted_checkpoints": 0,
    }


def probe(rootfs: Path, mode: str = "canonical") -> dict[str, object]:
    if mode not in ("canonical", "diagnostic-host-wsl-drivers"):
        raise ValueError("unapproved GPU probe mode")
    if rootfs.is_symlink() or not rootfs.is_file() or sha_file(rootfs) != ROOTFS:
        raise ValueError("V14 rootfs content mismatch")
    if SHELL.is_symlink() or not SHELL.is_file():
        raise ValueError("successor probe source missing")
    completed = subprocess.run(["bash", str(SHELL), str(rootfs), mode], capture_output=True, text=True)
    if completed.returncode != 0:
        raise ValueError(f"isolated GPU probe failed before receipt: exit {completed.returncode}; {completed.stderr.strip()[-500:]}")
    receipt = json.loads(completed.stdout)
    if (set(receipt) != {"schema", "wsl_lib_source", "rootfs_sha256", "versions", "cuda_available", "network_isolated", "pid_isolated", "device_dxg", "libcuda_load", "cu_init_result", "cu_device_count", "torch_cuda_init_error"}
            or receipt["schema"] != "pastila-production-core-v15-isolated-gpu-probe"
            or receipt["wsl_lib_source"] != mode
            or receipt["rootfs_sha256"] != ROOTFS
            or receipt["versions"] != {
                "bitsandbytes": "0.50.1", "peft": "0.20.0",
                "torch": "2.13.0+cu130", "transformers": "5.15.0",
            }
            or type(receipt["cuda_available"]) is not bool
            or type(receipt["device_dxg"]) is not bool
            or receipt["libcuda_load"] not in ("PASS", "FAIL")
            or (receipt["cu_init_result"] is not None and type(receipt["cu_init_result"]) is not int)
            or (receipt["cu_device_count"] is not None and type(receipt["cu_device_count"]) is not int)
            or (receipt["torch_cuda_init_error"] is not None and type(receipt["torch_cuda_init_error"]) is not str)
            or receipt["network_isolated"] is not True
            or receipt["pid_isolated"] is not True):
        raise ValueError("isolated GPU probe receipt mismatch")
    return receipt


def audit(terminal_root: Path, rootfs: Path) -> dict[str, object]:
    sources = source_closure()
    terminal = terminal_closure(terminal_root)
    if SHELL.is_symlink() or not SHELL.is_file():
        raise ValueError("successor probe source missing")
    probe_source_identity = sha_file(SHELL)
    drivers = driver_manifest()
    receipt = probe(rootfs)
    diagnostic = probe(rootfs, "diagnostic-host-wsl-drivers")
    if sha_file(SHELL) != probe_source_identity or driver_manifest() != drivers:
        raise ValueError("GPU probe source or diagnostic driver changed during audit")
    if (receipt["device_dxg"] is not True or receipt["libcuda_load"] != "PASS"
            or receipt["cu_init_result"] != 100 or receipt["cuda_available"] is not False
            or diagnostic["device_dxg"] is not True or diagnostic["libcuda_load"] != "PASS"
            or diagnostic["cu_init_result"] != 0
            or type(diagnostic["cu_device_count"]) is not int or diagnostic["cu_device_count"] < 1
            or diagnostic["cuda_available"] is not True):
        raise ValueError("V14 GPU failure or diagnostic driver witness changed")
    core = {
        "schema": "pastila-production-core-v15-successor-gpu-boundary-design",
        "bound_published_v14_commit": SOURCE_COMMIT,
        "bound_published_v14_tree": SOURCE_TREE,
        "bound_v14_authority_identity": AUTHORITY,
        "bound_v14_terminal": terminal,
        "bound_rootfs_sha256": ROOTFS,
        "v14_source_sha256": sources,
        "probe_source_sha256": probe_source_identity,
        "probe_receipt": receipt,
        "diagnostic_driver_receipt": diagnostic,
        "diagnostic_host_driver_manifest": drivers,
        "v15_candidate_execution": 0,
        "new_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
    }
    return {
        **core,
        "boundary_design_identity": sha(canonical(core)),
        "verdict": "DESIGN_AUDIT_PASS; EXECUTION_READINESS_BLOCKED",
        "execution_authorized": False,
    }

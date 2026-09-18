"""Sign a V15 driver-bound successor execution authority with zero attempts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import audit_production_core_successor_attempt_authority_v14 as audit_v14
import materialize_production_core_successor_execution_authority_v12 as signing
from pastila_scout import production_core_isolated_gpu_boundary_v15 as design
from pastila_scout import production_core_wsl_driver_snapshot_v15 as drivers

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v15-successor-execution-authority"
V14_AUTHORITY = design.AUTHORITY
SOURCE_FILES = (
    "docs/production-core-v15-isolated-gpu-successor-design.md",
    "scripts/audit_production_core_successor_gpu_boundary_v15.py",
    "scripts/audit_production_core_successor_execution_authority_v15.py",
    "scripts/probe_production_core_isolated_gpu_v15.sh",
    "scripts/run_production_core_candidate_qualification_v15.sh",
    "src/pastila_scout/production_core_isolated_gpu_boundary_v15.py",
    "src/pastila_scout/production_core_wsl_driver_snapshot_v15.py",
    "tests/test_production_core_successor_gpu_boundary_v15.py",
    "tests/test_production_core_successor_execution_authority_v15.py",
    "src/pastila_scout/production_core_candidate_qualification_runner_v14.py",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def source_closure() -> dict[str, str]:
    design.source_closure()
    hashes = {}
    for name in SOURCE_FILES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"V15 source missing: {name}")
        hashes[name] = digest(path.read_bytes())
    shell = (ROOT / "scripts/run_production_core_candidate_qualification_v15.sh").read_text("utf-8")
    if ("mount --bind \"$DRIVER_ROOT\" \"$ROOTFS/usr/lib/wsl/drivers\"" not in shell
            or "mount -o remount,bind,ro \"$ROOTFS/usr/lib/wsl/drivers\"" not in shell
            or "python3 -B \"$WORK/manifest.py\" --root \"$ROOTFS/usr/lib/wsl/drivers\"" not in shell
            or "/root/pf9-v15-wsl-drivers-snapshot" not in shell
            or "2096:21113" not in shell
            or "nvidia-smi" in shell):
        raise ValueError("V15 production driver mount witness mismatch")
    return hashes


def gpu_probe(rootfs: Path, snapshot: Path, helper_sha: str) -> dict:
    if design.sha_file(rootfs) != design.ROOTFS:
        raise ValueError("canonical rootfs changed")
    helper = ROOT / "src/pastila_scout/production_core_wsl_driver_snapshot_v15.py"
    result = subprocess.run(
        ["bash", str(design.SHELL), str(rootfs), "production-snapshot", str(snapshot), str(helper), helper_sha],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode:
        raise ValueError(f"isolated production GPU probe failed: {result.returncode}; {result.stderr.strip()[-500:]}")
    receipt = json.loads(result.stdout)
    if (receipt.get("schema") != "pastila-production-core-v15-isolated-gpu-probe"
            or receipt.get("wsl_lib_source") != "production-snapshot"
            or receipt.get("rootfs_sha256") != design.ROOTFS
            or receipt.get("network_isolated") is not True
            or receipt.get("pid_isolated") is not True
            or receipt.get("device_dxg") is not True
            or receipt.get("libcuda_load") != "PASS"
            or receipt.get("cu_init_result") != 0
            or type(receipt.get("cu_device_count")) is not int or receipt["cu_device_count"] < 1
            or receipt.get("cuda_available") is not True
            or receipt.get("torch_cuda_init_error") is not None
            or receipt.get("versions") != {
                "bitsandbytes": "0.50.1", "peft": "0.20.0",
                "torch": "2.13.0+cu130", "transformers": "5.15.0",
            }):
        raise ValueError("isolated production GPU receipt rejected")
    return receipt


def build(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
          terminal: Path, rootfs: Path, snapshot: Path) -> dict:
    sources = source_closure()
    predecessor = design.terminal_closure(terminal)
    snapshot_before = drivers.manifest(snapshot)
    report = audit_v14.audit(recovery, private, backup, v13_terminal)
    if (report.get("authority_identity") != V14_AUTHORITY
            or report.get("verdict") != "PASS + 0 BLOCKERS"
            or report.get("ed25519_verification") != "PASS"):
        raise ValueError("signed V14 predecessor authority rejected")
    authority_v14 = json.loads((ROOT / "docs/artifacts/production-core-v14-successor-attempt-authority/authority.json").read_bytes())
    if (authority_v14["runner_binding"]["qualification_generation_identity"] != "65d5b2502c0ff3a30367cceccda2a2e5c772844cb70500445a186deebf1d4567"
            or authority_v14["runner_binding"]["qualification_identity"] != "309facaf268c79cdf3e6c635bec47c46c68121b7b5eb543f07c801048386da13"):
        raise ValueError("V14 qualification generation drift")
    receipt = gpu_probe(rootfs, snapshot, sources["src/pastila_scout/production_core_wsl_driver_snapshot_v15.py"])
    if drivers.manifest(snapshot) != snapshot_before or source_closure() != sources:
        raise ValueError("snapshot or V15 source changed during materialization")
    core = {
        "schema": "pastila-production-core-v15-successor-execution-authority",
        "schema_version": 1,
        "status": "SIGNED_DRIVER_BOUND_SUCCESSOR_NO_ATTEMPT",
        "bound_published_v14_commit": design.SOURCE_COMMIT,
        "bound_published_v14_tree": design.SOURCE_TREE,
        "predecessor_v14_authority_identity": V14_AUTHORITY,
        "predecessor_v14_terminal_evidence": predecessor,
        "predecessor_v14_attempt_consumption": 1,
        "recovery_resolution_identity": authority_v14["recovery_resolution_identity"],
        "runtime_object_authority_identity": authority_v14["runtime_object_authority_identity"],
        "qualification_generation_identity": authority_v14["runner_binding"]["qualification_generation_identity"],
        "qualification_identity": authority_v14["runner_binding"]["qualification_identity"],
        "alias_secret_commitment": authority_v14["alias_secret_commitment"],
        "schedule_sha256": authority_v14["schedule_sha256"],
        "rootfs_sha256": design.ROOTFS,
        "driver_snapshot": snapshot_before,
        "isolated_gpu_probe": receipt,
        "source_sha256": sources,
        "builder_sha256": digest(Path(__file__).read_bytes()),
        "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "new_candidate_execution": 0,
        "new_attempt_consumption": 0,
        "candidate_execution_authorized": False,
        "new_attempt_consumption_authorized": False,
        "adjudication": False,
        "promotion": False,
    }
    return {**core, "authority_identity": digest(canonical(core))}


def binding_for(authority: dict, raw: bytes) -> dict:
    return {
        "schema": "pastila-production-core-v15-detached-execution-binding",
        "schema_version": 1,
        "algorithm": "Ed25519",
        "authority_identity": authority["authority_identity"],
        "authority_sha256": digest(raw),
        "bound_published_v14_commit": design.SOURCE_COMMIT,
        "bound_published_v14_tree": design.SOURCE_TREE,
        "predecessor_v14_attempt_identity": design.ATTEMPT,
        "predecessor_v14_terminal_failure_identity": design.FAILURE,
        "predecessor_v14_authority_identity": V14_AUTHORITY,
        "driver_snapshot": authority["driver_snapshot"],
        "isolated_gpu_probe": authority["isolated_gpu_probe"],
        "rootfs_sha256": design.ROOTFS,
        "source_sha256": authority["source_sha256"],
        "builder_sha256": authority["builder_sha256"],
        "public_key_pem_sha256": signing.PUBLIC_PEM_SHA256,
        "new_candidate_execution": 0,
        "new_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
    }


def materialize(recovery: Path, private: Path, backup: Path, v13_terminal: Path, terminal: Path,
                rootfs: Path, snapshot: Path, private_key: Path) -> dict[str, str]:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise ValueError("V15 authority output already exists")
    signing.verify_key(private_key)
    authority = build(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot)
    raw = json.dumps(authority, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    binding_raw = canonical(binding_for(authority, raw))
    with tempfile.TemporaryDirectory(prefix=".v15-authority-", dir=OUTPUT.parent) as temporary:
        staging = Path(temporary) / "payload"
        staging.mkdir()
        (staging / "authority.json").write_bytes(raw)
        (staging / "binding.json").write_bytes(binding_raw)
        (staging / "builder-source.py").write_bytes(Path(__file__).read_bytes())
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(private_key), "-rawin", "-in", str(staging / "binding.json"), "-out", str(staging / "binding.sig")], check=True)
        subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(signing.PUBLIC_KEY), "-rawin", "-in", str(staging / "binding.json"), "-sigfile", str(staging / "binding.sig")], check=True, capture_output=True)
        signature = (staging / "binding.sig").read_bytes()
        if len(signature) != 64:
            raise ValueError("V15 Ed25519 signature length mismatch")
        result = {"authority_identity": authority["authority_identity"],
                  "binding_identity": digest(binding_raw), "signature_identity": digest(signature)}
        os.replace(staging, OUTPUT)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot", "private-key"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.recovery, args.private, args.backup, args.v13_terminal, args.terminal,
                                 args.rootfs, args.snapshot, args.private_key), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

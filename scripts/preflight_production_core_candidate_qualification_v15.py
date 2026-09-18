"""Executable, read-only V15 gate. This module cannot create an attempt."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import audit_production_core_successor_execution_authority_v15 as signed
import preflight_production_core_candidate_qualification_v14 as predecessor_gate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pastila_scout.production_core_semantic_authority_v2 import Unicode16SentenceAuthority  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "bba5e76dbe6408fd3c917830785c3a19300181ae"
TREE = "a47a61ae140179e9f9ff1c112dbdbf5d94137461"
BRANCH = "successor/core-v2-v12-runner-binding-remediation"
AUTHORITY = "6bcd6d782b8096c394f0dabd5f3bb4f25f32222edd712b2da587ae843e35d472"
BINDING = "a2ff014a25efa2f835caa93d4d0cd1d845d9a08f0fab2d45afbbbb439538ac46"
SIGNATURE = "13fd25a32542e7773af5e5acf054d47554905fe41b33947f91d81ce1ed559aa0"
MANIFEST = "f2074e618ba99a03e327ef2462a814b5a9503bbe5994692805ff8c4f11375126"
V14_TERMINAL_SHA256 = "fabc58e6a886e310d6f6473f0e25b181dbc293fe78adab06ba5db4976bea45fa"
SNAPSHOT = Path("/root/pf9-v15-wsl-drivers-snapshot")
SNAPSHOT_DEVICE, SNAPSHOT_INODE = 2096, 21113
MIN_FREE_BYTES = 68_719_476_736
PUBLIC_FILES = (
    "docs/artifacts/production-core-v15-successor-execution-authority/authority.json",
    "docs/artifacts/production-core-v15-successor-execution-authority/binding.json",
    "docs/artifacts/production-core-v15-successor-execution-authority/binding.sig",
    "docs/artifacts/production-core-v15-successor-execution-authority/builder-source.py",
    "docs/production-core-v15-isolated-gpu-successor-design.md",
    "scripts/audit_production_core_successor_execution_authority_v15.py",
    "scripts/audit_production_core_successor_gpu_boundary_v15.py",
    "scripts/materialize_production_core_successor_execution_authority_v15.py",
    "scripts/probe_production_core_isolated_gpu_v15.sh",
    "scripts/run_production_core_candidate_qualification_v15.sh",
    "src/pastila_scout/production_core_isolated_gpu_boundary_v15.py",
    "src/pastila_scout/production_core_wsl_driver_snapshot_v15.py",
    "tests/test_production_core_successor_execution_authority_v15.py",
    "tests/test_production_core_successor_gpu_boundary_v15.py",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def published_source_closure() -> None:
    if git("rev-parse", f"{COMMIT}^{{tree}}") != TREE:
        raise ValueError("V15 checkpoint tree mismatch")
    committed = git("diff-tree", "--no-commit-id", "--name-only", "-r", COMMIT).splitlines()
    if committed != list(PUBLIC_FILES):
        raise ValueError("V15 checkpoint file scope mismatch")
    for revision in ("HEAD", f"refs/remotes/origin/{BRANCH}"):
        if subprocess.run(["git", "merge-base", "--is-ancestor", COMMIT, revision],
                          cwd=ROOT, capture_output=True).returncode:
            raise ValueError("V15 checkpoint not published in source ancestry")
    for name in PUBLIC_FILES:
        path = ROOT / name
        raw = subprocess.check_output(["git", "show", f"{COMMIT}:{name}"], cwd=ROOT)
        if path.is_symlink() or not path.is_file() or path.read_bytes() != raw:
            raise ValueError(f"published V15 source drift: {name}")


def empty_output(path: Path, protected: tuple[Path, ...]) -> dict[str, object]:
    if os.name == "nt" or os.geteuid() != 0 or not path.is_absolute() or str(path).startswith("/mnt/"):
        raise ValueError("V15 output requires native WSL root")
    current = path
    while True:
        if current.is_symlink() or not current.is_dir():
            raise ValueError("V15 output path substitution")
        if current == current.parent:
            break
        current = current.parent
    resolved = path.resolve(strict=True)
    for item in protected:
        target = item.resolve(strict=True)
        if resolved == target or resolved.is_relative_to(target) or target.is_relative_to(resolved):
            raise ValueError("V15 output overlaps protected input")
    metadata = path.stat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
        raise ValueError("V15 output ownership or permissions rejected")
    if any(path.iterdir()):
        raise ValueError("V15 output is not empty")
    filesystem = subprocess.check_output(["findmnt", "-n", "-o", "FSTYPE", "--target", str(path)], text=True).strip()
    if filesystem != "ext4" or shutil.disk_usage(path).free < MIN_FREE_BYTES:
        raise ValueError("V15 output ext4 or free capacity rejected")
    return {"path": str(resolved), "device": metadata.st_dev, "inode": metadata.st_ino,
            "filesystem": filesystem, "entries": 0}


def preflight(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
              terminal: Path, rootfs: Path, snapshot: Path, unicode_root: Path,
              output: Path) -> dict[str, object]:
    published_source_closure()
    if snapshot != SNAPSHOT:
        raise ValueError("V15 snapshot path mismatch")
    output_before = empty_output(output, (ROOT, recovery, private, backup, v13_terminal, terminal, rootfs,
                                         snapshot, unicode_root))
    report = signed.audit(recovery, private, backup, v13_terminal, terminal, rootfs, snapshot)
    expected = {"authority_identity": AUTHORITY, "binding_identity": BINDING,
                "signature_identity": SIGNATURE, "verdict": "PASS + 0 BLOCKERS",
                "ed25519_verification": "PASS", "source_closure": "PASS",
                "runtime_object_closure": "PASS", "driver_snapshot_closure": "PASS",
                "isolated_cuda": "PASS", "v14_terminal_closure": "PASS",
                "new_candidate_execution": "0", "new_attempt_consumption": "0",
                "adjudication": "false", "promotion": "false"}
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError("V15 signed authority audit rejected")
    authority = json.loads((ROOT / PUBLIC_FILES[0]).read_bytes())
    driver = authority.get("driver_snapshot", {})
    terminal_evidence = authority.get("predecessor_v14_terminal_evidence", {})
    if (driver.get("root") != str(SNAPSHOT) or driver.get("device") != SNAPSHOT_DEVICE
            or driver.get("inode") != SNAPSHOT_INODE or driver.get("manifest_identity") != MANIFEST
            or driver.get("filesystem") != "ext4" or driver.get("readonly_entries") is not True
            or terminal_evidence.get("terminal_failure_sha256") != V14_TERMINAL_SHA256
            or authority.get("new_attempt_consumption") != 0
            or authority.get("new_candidate_execution") != 0):
        raise ValueError("V15 frozen snapshot, terminal, or zero-attempt binding mismatch")
    predecessor_gate.validate_matrix()
    if unicode_root.is_symlink() or str(unicode_root).startswith("/mnt/"):
        raise ValueError("V15 Unicode authority requires native ext4")
    Unicode16SentenceAuthority.load(unicode_root)
    for capability in ("bash", "unshare", "mount", "chroot"):
        if shutil.which(capability) is None:
            raise ValueError(f"V15 executable capability unavailable: {capability}")
    subprocess.run(["unshare", "--mount", "--net", "--pid", "--ipc", "--uts", "--fork", "true"],
                   check=True, capture_output=True)
    output_after = empty_output(output, (ROOT, recovery, private, backup, v13_terminal, terminal, rootfs,
                                        snapshot, unicode_root))
    published_source_closure()
    if output_after != output_before:
        raise ValueError("V15 output or source changed during preflight")
    core: dict[str, object] = {
        "schema": "pastila-production-core-v15-preconsumption-preflight", "schema_version": 1,
        "verdict": "PASS + 0 BLOCKERS", "bound_commit": COMMIT, "bound_tree": TREE,
        "authority_identity": AUTHORITY, "binding_identity": BINDING, "signature_identity": SIGNATURE,
        "driver_snapshot": driver, "v14_terminal_failure_sha256": V14_TERMINAL_SHA256,
        "ed25519_verification": "PASS", "source_closure": "PASS", "runtime_object_closure": "PASS",
        "isolated_cuda": "PASS", "qualification_matrix": "PASS", "unicode_authority": "PASS",
        "executable_capabilities": "PASS", "output": output_after, "candidate_execution": 0,
        "attempt_consumption": 0, "adjudication": False, "promotion": False,
    }
    raw = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {**core, "preflight_identity": hashlib.sha256(raw).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot", "unicode-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(preflight(args.recovery, args.private, args.backup, args.v13_terminal,
                               args.terminal, args.rootfs, args.snapshot, args.unicode_root, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

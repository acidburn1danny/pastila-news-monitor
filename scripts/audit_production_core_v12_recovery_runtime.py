"""Read-only audit of a materialized V12 recovery resolution."""
from __future__ import annotations

import argparse
import json
import os
import posixpath
import subprocess
from pathlib import Path, PurePosixPath

import materialize_production_core_v12_recovery_runtime as runtime


def audit_boundary(projection: dict[str, object]) -> None:
    helper = (runtime.ROOT / "scripts/resolve_production_core_object_authority_v2.sh").read_bytes()
    linux = ["wsl.exe", "-d", "Ubuntu-24.04", "--"] if os.name == "nt" else []
    seen: set[str] = set()
    all_paths = [path for local in projection["materializations"].values() for path in (local["rootfs_tar"], local["model"], *local["adapters"].values())]
    common_root = PurePosixPath(posixpath.commonpath(all_paths))
    for label, local in projection["materializations"].items():
        checks = [
            ("rootfs", local["rootfs_tar"], "file", runtime.EXPECTED_ROOTFS),
            ("model", local["model"], "flat-dir", runtime.EXPECTED_BASE),
            *((name, path, "flat-dir", runtime.EXPECTED_ADAPTERS[name]) for name, path in local["adapters"].items()),
        ]
        for role, path, kind, expected in checks:
            check_path = PurePosixPath(path)
            while True:
                permissions = subprocess.run(
                    [*linux, "stat", "-c", "%a", "--", str(check_path)],
                    capture_output=True,
                    check=True,
                )
                if int(permissions.stdout.strip(), 8) & 0o222:
                    raise ValueError(f"executor runtime object or ancestor is writable: {label}/{role}: {check_path}")
                if check_path == common_root:
                    break
                check_path = check_path.parent
            result = subprocess.run(
                [*linux, "bash", "--noprofile", "--norc", "-s", "--", path, kind],
                input=helper,
                check=True,
                capture_output=True,
            )
            observed = json.loads(result.stdout)
            if tuple(observed) != ("physical_identity", "content_identity") or observed["content_identity"] != expected:
                raise ValueError(f"executor object authority mismatch: {label}/{role}")
            if role != "rootfs":
                if observed["physical_identity"] in seen:
                    raise ValueError(f"executor physical materialization overlap: {label}/{role}")
                seen.add(observed["physical_identity"])
            print(f"{label}/{role}: PASS", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery", type=Path, required=True)
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--wsl-boundary", action="store_true")
    options = parser.parse_args()
    if options.recovery.is_symlink() or options.projection.is_symlink():
        raise ValueError("symlink recovery artifact rejected")
    recovery = json.loads(options.recovery.read_bytes())
    projection = json.loads(options.projection.read_bytes())
    if options.recovery.parent != options.projection.parent:
        raise ValueError("recovery artifacts must share one isolated root")
    expected_entries = {
        "models", "adapters", "tokenizers", "rootfs",
        options.recovery.name, options.projection.name,
    }
    observed_entries = {item.name for item in options.recovery.parent.iterdir()}
    if observed_entries != expected_entries:
        raise ValueError(f"unexpected recovery root entries: {sorted(observed_entries ^ expected_entries)}")
    runtime.audit_recovery_resolution(recovery, projection)
    print(f"recovery: PASS {recovery['resolution_identity']}", flush=True)
    if options.wsl_boundary:
        audit_boundary(projection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

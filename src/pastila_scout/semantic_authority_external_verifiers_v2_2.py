"""Hash-pinned, zero-network executable boundaries for Rekor and drand."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_pin(path: Path, expected_sha256: str) -> None:
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise ValueError(f"executable or component identity mismatch: {path.name}")


def tree_sha256(root: Path) -> str:
    """Commit every regular file by UTF-8 relative name, length, and bytes."""
    if not root.is_dir():
        raise ValueError("component tree missing")
    h = hashlib.sha256()
    entries = list(root.rglob("*"))
    for path in entries:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        if path.is_symlink() or attributes & 0x400:
            raise ValueError("component tree link or reparse point prohibited")
    files = sorted(
        (path for path in entries if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix().encode(),
    )
    if not files:
        raise ValueError("component tree empty")
    for path in files:
        name = path.relative_to(root).as_posix().encode()
        data = path.read_bytes()
        h.update(len(name).to_bytes(8, "big") + name + len(data).to_bytes(8, "big") + data)
    return h.hexdigest()


def qualify_rekor_executable(executable: Path, *, expected_sha256: str) -> str:
    """Qualify the installed Rekor CLI without contacting a Rekor service."""
    require_pin(executable, expected_sha256)
    run = subprocess.run(
        [str(executable), "version"], capture_output=True, timeout=30, check=False
    )
    output = (run.stdout + run.stderr).decode("utf-8", "replace")
    if run.returncode or "GitVersion:    v1.5.1" not in output or "Platform:      windows/amd64" not in output:
        raise ValueError("Rekor executable version/build mismatch")
    return "v1.5.1/windows-amd64"


def verify_quicknet_offline(
    *,
    node: Path,
    node_sha256: str,
    node_tree_sha256: str,
    launcher: Path,
    launcher_sha256: str,
    client_root: Path,
    client_lock: Path,
    client_lock_sha256: str,
    client_tree_sha256: str,
    chain_info: Mapping[str, Any],
    beacon: Mapping[str, Any],
    expected_round: int,
) -> None:
    """Verify a supplied Quicknet beacon using only local, pinned components."""
    for path, pin in ((node, node_sha256), (launcher, launcher_sha256), (client_lock, client_lock_sha256)):
        require_pin(path, pin)
    if tree_sha256(node.parent) != node_tree_sha256:
        raise ValueError("Node runtime tree mismatch")
    package = json.loads((client_root / "package.json").read_text(encoding="utf-8"))
    if package.get("name") != "drand-client" or package.get("version") != "1.4.1":
        raise ValueError("drand-client package mismatch")
    if tree_sha256(client_root.parent) != client_tree_sha256:
        raise ValueError("installed drand dependency tree mismatch")
    request = json.dumps(
        {"chain_info": chain_info, "beacon": beacon, "expected_round": expected_round},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    # Prevent caller-controlled Node preload/search hooks from running before the
    # pinned launcher. The verifier needs no inherited network configuration.
    env = {
        "SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
        "WINDIR": os.environ.get("WINDIR", r"C:\Windows"),
        "TEMP": os.environ.get("TEMP", str(client_root.parent)),
        "TMP": os.environ.get("TMP", str(client_root.parent)),
        "NODE_OPTIONS": "",
        "NODE_PATH": "",
        "PASTILA_DRAND_CLIENT_ROOT": str(client_root),
    }
    run = subprocess.run(
        [str(node), str(launcher)], input=request, capture_output=True,
        timeout=30, check=False, env=env, cwd=node.parent,
    )
    if run.returncode or run.stdout != b"PASS_QUICKNET_BLS\n" or run.stderr:
        raise ValueError("drand Quicknet BLS verification failed")

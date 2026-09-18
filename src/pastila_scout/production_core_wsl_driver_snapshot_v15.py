"""Content and permission closure for the V15 ext4 WSL driver snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import subprocess
from pathlib import Path

EXPECTED_MANIFEST = "f2074e618ba99a03e327ef2462a814b5a9503bbe5994692805ff8c4f11375126"
EXPECTED_FILES = 2310


def sha_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def manifest(root: Path) -> dict[str, object]:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir() or str(root).startswith("/mnt/"):
        raise ValueError("driver snapshot must be a native directory")
    if subprocess.check_output(["findmnt", "-n", "-o", "FSTYPE", "--target", str(root)], text=True).strip() != "ext4":
        raise ValueError("driver snapshot requires ext4")
    if root.stat().st_mode & 0o222:
        raise ValueError("driver snapshot root is writable")
    current = root
    while current != current.parent:
        if current.is_symlink() or not current.is_dir():
            raise ValueError("driver snapshot ancestor substitution")
        current = current.parent
    rows = []
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        mode = path.lstat().st_mode
        if path.is_symlink() or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)) or mode & 0o222:
            raise ValueError("driver snapshot writable or substituted entry")
        if path.is_file():
            rows.append([path.relative_to(root).as_posix(), path.stat().st_size, sha_file(path)])
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    identity = hashlib.sha256(raw).hexdigest()
    if len(rows) != EXPECTED_FILES or identity != EXPECTED_MANIFEST:
        raise ValueError("driver snapshot manifest mismatch")
    return {
        "root": str(root.resolve(strict=True)),
        "device": root.stat().st_dev,
        "inode": root.stat().st_ino,
        "file_count": len(rows),
        "manifest_identity": identity,
        "readonly_entries": True,
        "filesystem": "ext4",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(manifest(args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

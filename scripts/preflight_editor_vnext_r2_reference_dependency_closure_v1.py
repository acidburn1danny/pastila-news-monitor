"""Verify a restored VNext R2 closure using only its root and lock."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path, PurePosixPath


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify(root: Path) -> dict:
    lock_path = root / "dependency-lock.json"
    raw = lock_path.read_text(encoding="utf-8")
    lock = json.loads(raw)
    identity = lock.pop("lock_identity")
    if hashlib.sha256(canonical(lock)).hexdigest() != identity:
        raise ValueError("lock identity mismatch")
    expected_paths = set()
    total = 0
    for item in lock["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts or str(relative) != item["path"]:
            raise ValueError(f"non-canonical dependency path: {item['path']}")
        path = root.joinpath(*relative.parts)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or linked dependency: {relative}")
        if path.stat().st_size != item["size"] or digest(path) != item["sha256"]:
            raise ValueError(f"content mismatch: {relative}")
        expected_paths.add(relative.as_posix())
        total += item["size"]
    actual_paths = {
        path.relative_to(root).as_posix() for path in root.rglob("*")
        if path.is_file() and path != lock_path
    }
    if actual_paths != expected_paths:
        raise ValueError("unlocked dependency present or locked dependency absent")
    return {"status": "PASS_DEPENDENCY_ONLY", "lock_identity": identity, "files": len(expected_paths), "bytes": total}


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1]).resolve()), sort_keys=True))

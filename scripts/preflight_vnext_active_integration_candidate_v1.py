#!/usr/bin/env python3
"""Dependency-only preflight for a materialized VNext product candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

LEGACY_MARKERS = ("/"+"root/pf9-", "/mnt"+"/f/pt", "F:"+chr(92)+chr(92)+"pt", "/root/"+"pastila-news-monitor")

def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_identity(root: Path) -> str:
    entries: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            entries.append({"path": relative, "type": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            entries.append({
                "path": relative, "type": "file",
                "sha256": file_hash(path), "size": path.stat().st_size,
            })
    return identity(entries)


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"object required: {path}")
    return value


def verify_lock_identity(value: dict[str, object], key: str) -> None:
    claimed = value.get(key)
    actual = identity({name: item for name, item in value.items() if name != key})
    if claimed != actual:
        raise RuntimeError(f"identity mismatch: {key}")


def verify(root: Path, *, full_platform_hash: bool = True) -> dict[str, object]:
    root = root.resolve(strict=True)
    lock = load_json(root / "manifest/product-lock.json")
    verify_lock_identity(lock, "product_lock_identity")
    if lock.get("product_root") != "/root/pastila-vnext/v1":
        raise RuntimeError("candidate product-root authority mismatch")
    if lock.get("legacy_dependency_count") != 0:
        raise RuntimeError("legacy dependency count is not zero")
    if lock.get("active_integration_state") != "CANDIDATE_NOT_ACTIVATED":
        raise RuntimeError("candidate unexpectedly claims active integration")

    for item in lock["application_files"]:
        path = root / item["path"]
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"application file missing or linked: {item['path']}")
        if path.stat().st_size != item["size"] or file_hash(path) != item["sha256"]:
            raise RuntimeError(f"application file mismatch: {item['path']}")

    r2_root = root / "components/editor-r2"
    r2_lock = load_json(r2_root / "dependency-lock.json")
    verify_lock_identity(r2_lock, "lock_identity")
    if r2_lock["lock_identity"] != lock["components"]["R2_REFERENCE"]["lock_identity"]:
        raise RuntimeError("R2 lock mismatch")
    for item in r2_lock["files"]:
        path = r2_root / item["path"]
        if not path.is_file() or path.stat().st_size != item["size"] or file_hash(path) != item["sha256"]:
            raise RuntimeError(f"R2 byte mismatch: {item['path']}")

    platform_root = root / "platform/python-ml"
    platform_python = platform_root / "bin/python"
    if not platform_python.exists():
        raise RuntimeError("platform python missing")
    if full_platform_hash:
        actual_tree = tree_identity(platform_root)
        if actual_tree != lock["components"]["PYTHON_ML_PLATFORM"]["tree_identity"]:
            raise RuntimeError("platform tree mismatch")

    db = root / "state/product.sqlite3"
    if not db.is_file():
        raise RuntimeError("product SQLite missing")

    legacy: list[dict[str, str]] = []
    for relative in ("app", "config", "contracts", "foundation", "manifest"):
        base = root / relative
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_symlink():
                target = os.readlink(path)
                if any(marker.casefold() in target.casefold() for marker in LEGACY_MARKERS):
                    legacy.append({"path": path.relative_to(root).as_posix(), "binding": target})
            elif path.is_file() and path.stat().st_size <= 2_000_000:
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                for marker in LEGACY_MARKERS:
                    if marker.casefold() in text.casefold():
                        legacy.append({"path": path.relative_to(root).as_posix(), "binding": marker})
    if legacy:
        raise RuntimeError(f"legacy bindings: {legacy}")

    return {
        "status": "PASS",
        "product_lock_identity": lock["product_lock_identity"],
        "application_files": len(lock["application_files"]),
        "r2_files": len(r2_lock["files"]),
        "platform_tree_verified": full_platform_hash,
        "legacy_dependency_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--skip-platform-hash", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.root, full_platform_hash=not args.skip_platform_hash), sort_keys=True))


if __name__ == "__main__":
    main()

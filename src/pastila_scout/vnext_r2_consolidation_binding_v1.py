"""Read-only proof that the frozen R2 closure can bind to the consolidated layout."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path

from .vnext_foundation_v1 import BoundaryError, object_identity

EXPECTED_LOCK_IDENTITY = "53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f"
EXPECTED_LOCK_SHA256 = "bb6817428f0663a00d7acafb5fcd5abd5f03615002380276a28502e280b28a3e"
EXPECTED_PLATFORM_TREE_IDENTITY = "ef5318bfa36af16350ec96d16ef84eb8b55c527894c3c5045f08d4b9ba1bc498"
EXPECTED_TOTAL_BYTES = 28_185_570_253
EXPECTED_FILE_COUNT = 25
SOURCE_COMPONENT = "components/r2-reference-v1"
TARGET_COMPONENT = "components/editor-r2"
_SHA256 = re.compile(r"[0-9a-f]{64}")


class R2BindingError(BoundaryError):
    """The R2 dependency closure cannot be proven byte-identical."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_validate_lock(root: Path) -> dict[str, object]:
    root = root.resolve(strict=True)
    lock_path = root / "dependency-lock.json"
    if not lock_path.is_file() or lock_path.is_symlink():
        raise R2BindingError("regular dependency lock required")
    raw = lock_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_LOCK_SHA256:
        raise R2BindingError("dependency lock byte identity mismatch")
    lock = json.loads(raw)
    if not isinstance(lock, dict):
        raise R2BindingError("dependency lock must be an object")
    semantic = {key: value for key, value in lock.items() if key != "lock_identity"}
    if object_identity(semantic) != lock.get("lock_identity") or lock.get("lock_identity") != EXPECTED_LOCK_IDENTITY:
        raise R2BindingError("dependency lock semantic identity mismatch")
    if lock.get("schema") != "editor-vnext-r2-reference-dependency-lock" or lock.get("schema_version") != 1:
        raise R2BindingError("dependency lock schema mismatch")
    if lock.get("status") != "MATERIALIZED_SELF_CONTAINED" or lock.get("component") != "R2_STEP_9_REFERENCE_REALIZER":
        raise R2BindingError("R2 component/status mismatch")
    if lock.get("file_count") != EXPECTED_FILE_COUNT or lock.get("total_bytes") != EXPECTED_TOTAL_BYTES:
        raise R2BindingError("R2 file/byte totals mismatch")
    identities = lock.get("identities")
    if not isinstance(identities, Mapping):
        raise R2BindingError("R2 identities missing")
    required = {
        "adapter_flat_identity": "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02",
        "base_model_flat_identity": "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39",
        "checkpoint_identity": "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be",
        "tokenizer_flat_identity": "026c7803af845d166451a8845defbc359cfda96d2d33c56d9648dcc8c117d1b2",
        "tokenizer_json_sha256": "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135",
    }
    if dict(identities) != required:
        raise R2BindingError("R2 authoritative identities mismatch")
    if lock.get("layout") != {"adapter": "objects/adapter", "base_model": "objects/base-model", "dependency_preflight": "tooling/preflight.py", "tokenizer": "objects/tokenizer"}:
        raise R2BindingError("R2 layout mismatch")
    if lock.get("runtime") != {"adapter_loader": "PeftModel", "fix_mistral_regex": True, "loader": "AutoModelForImageTextToText", "local_files_only": True}:
        raise R2BindingError("R2 runtime binding mismatch")
    return lock


def verify_closure(root: Path, *, verify_bytes: bool = True) -> dict[str, object]:
    """Verify the existing closure without loading a model or writing to it."""
    root = root.resolve(strict=True)
    if any(path.is_symlink() for path in root.rglob("*")):
        raise R2BindingError("R2 closure contains a symlink")
    lock = load_and_validate_lock(root)
    rows = lock.get("files")
    if not isinstance(rows, list) or len(rows) != EXPECTED_FILE_COUNT:
        raise R2BindingError("R2 file manifest mismatch")
    expected_paths: set[str] = set()
    total = 0
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256", "size"}:
            raise R2BindingError("invalid R2 file row")
        relative = row["path"]
        digest = row["sha256"]
        size = row["size"]
        if not isinstance(relative, str) or not relative or relative.startswith(("/", "../")) or "\\" in relative:
            raise R2BindingError("unsafe R2 relative path")
        if relative in expected_paths or not isinstance(digest, str) or _SHA256.fullmatch(digest) is None or not isinstance(size, int) or size < 0:
            raise R2BindingError("invalid or duplicate R2 file row")
        expected_paths.add(relative)
        path = (root / relative).resolve(strict=True)
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise R2BindingError("R2 path escapes closure") from exc
        if not path.is_file() or path.is_symlink() or path.stat().st_nlink != 1:
            raise R2BindingError("R2 object is not an independent regular file")
        if path.stat().st_size != size or verify_bytes and _sha256(path) != digest:
            raise R2BindingError(f"R2 object identity mismatch: {relative}")
        total += size
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name != "dependency-lock.json"}
    if actual != expected_paths or total != EXPECTED_TOTAL_BYTES:
        raise R2BindingError("R2 closure inventory mismatch")
    return {"status": "PASS_BYTE_IDENTICAL" if verify_bytes else "PASS_MANIFEST_ONLY", "lock_identity": lock["lock_identity"], "files": len(rows), "bytes": total}


def binding_manifest(lock: Mapping[str, object], *, platform_tree_identity: str = EXPECTED_PLATFORM_TREE_IDENTITY) -> dict[str, object]:
    """Describe the future relocation without copying or changing the closure."""
    if lock.get("lock_identity") != EXPECTED_LOCK_IDENTITY or platform_tree_identity != EXPECTED_PLATFORM_TREE_IDENTITY:
        raise R2BindingError("binding dependency identity mismatch")
    manifest: dict[str, object] = {
        "schema": "vnext-r2-byte-identical-consolidation-binding",
        "schema_version": 1,
        "status": "ISOLATED_NOT_ACTIVE",
        "source_component": SOURCE_COMPONENT,
        "target_component": TARGET_COMPONENT,
        "relocation_strategy": "COPY_THEN_VERIFY_BEFORE_LATER_ACTIVATION",
        "relocation_authorized": False,
        "r2_lock_identity": EXPECTED_LOCK_IDENTITY,
        "r2_lock_sha256": EXPECTED_LOCK_SHA256,
        "platform_tree_identity": platform_tree_identity,
        "file_count": EXPECTED_FILE_COUNT,
        "total_bytes": EXPECTED_TOTAL_BYTES,
        "relative_layout_preserved": True,
        "bytes_modified": False,
        "model_loaded": False,
        "inference_performed": False,
        "editor_rebuilt": False,
        "active_integration": False,
        "product_lock_replaced": False,
        "legacy_dependency_count": 0,
    }
    manifest["binding_identity"] = object_identity(manifest)
    return manifest

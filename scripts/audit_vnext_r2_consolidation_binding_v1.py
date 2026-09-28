from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_r2_consolidation_binding_v1 import (
    EXPECTED_LOCK_IDENTITY,
    binding_manifest,
    verify_closure,
)

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "src/pastila_scout/vnext_r2_consolidation_binding_v1.py",
    "docs/artifacts/vnext-r2-byte-identical-consolidation-binding-closure-v1.json",
    "docs/vnext-r2-byte-identical-consolidation-binding-closure-v1.md",
    "tests/test_vnext_r2_consolidation_binding_v1.py",
    "scripts/audit_vnext_r2_consolidation_binding_v1.py",
]
AUTHORITIES = {
    "docs/artifacts/vnext-active-product-component-migration-matrix-v1.json": "e72cb07e4c674e4b3a0fc02756d0bba96c46963e881414f0cc8ed86f03816b12",
    "docs/artifacts/vnext-active-product-consolidation-acceptance-gates-v1.json": "5bff2bdadaf60b130fc59e0b318422031d514176774f28d945ea21689e519b11",
    "src/pastila_scout/vnext_foundation_v1.py": "e9d857e5910fffd76dfd9aed1891e86ad68cf31602150ef0445455f6b4bc8615",
}
ALLOWED_IMPORTS = {"__future__", "collections", "hashlib", "json", "pathlib", "re", "vnext_foundation_v1"}


def published_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8")); result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): result.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module: result.add(node.module.split(".")[-1] if node.level else node.module.split(".")[0])
    return result


def scope(commit: str) -> list[str]:
    output = subprocess.check_output(["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit, "--"], cwd=ROOT, text=True)
    return sorted(item for item in output.splitlines() if item)


def audit(commit: str | None, closure_root: Path | None, verify_bytes: bool) -> dict[str, object]:
    for name in FILES: assert (ROOT / name).is_file(), name
    for name, expected in AUTHORITIES.items(): assert published_sha(ROOT / name) == expected, name
    closure = json.loads((ROOT / FILES[1]).read_text(encoding="utf-8"))
    assert object_identity({key: value for key, value in closure.items() if key != "closure_identity"}) == closure["closure_identity"]
    manifest = binding_manifest({"lock_identity": EXPECTED_LOCK_IDENTITY})
    assert manifest == closure["binding"]
    assert closure["r2_identities"] == {
        "adapter_flat_identity": "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02",
        "base_model_flat_identity": "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39",
        "checkpoint_identity": "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be",
        "tokenizer_flat_identity": "026c7803af845d166451a8845defbc359cfda96d2d33c56d9648dcc8c117d1b2",
        "tokenizer_json_sha256": "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135",
    }
    assert closure["status"] == "ISOLATED_NOT_ACTIVE" and not closure["product_root_modified"] and not closure["product_lock_modified"]
    assert closure["legacy_dependency_count"] == 0 and closure["stop_all_candidates"] and closure["voice"] == "DISABLED_UNTIL_PROMOTION"
    runtime_imports = imports(ROOT / FILES[0]); assert runtime_imports <= ALLOWED_IMPORTS, sorted(runtime_imports - ALLOWED_IMPORTS)
    exact_scope = scope(commit) if commit else sorted(FILES)
    if commit: assert exact_scope == sorted(FILES)
    live = None if closure_root is None else verify_closure(closure_root, verify_bytes=verify_bytes)
    return {
        "verdict": "PASS", "blockers": 0, "scope": exact_scope,
        "blob_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES},
        "closure_identity": closure["closure_identity"], "binding_identity": manifest["binding_identity"],
        "r2_lock_identity": EXPECTED_LOCK_IDENTITY, "live_closure": live,
        "bytes_modified": False, "model_loaded": False, "inference_performed": False,
        "editor_rebuilt": False, "active_integration": False, "product_lock_replaced": False,
        "legacy_dependency_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--commit"); parser.add_argument("--closure-root", type=Path); parser.add_argument("--verify-bytes", action="store_true")
    args = parser.parse_args(); print(json.dumps(audit(args.commit, args.closure_root, args.verify_bytes), indent=2, sort_keys=True))


if __name__ == "__main__": main()

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "src/pastila_scout/vnext_foundation_v1.py",
    "src/pastila_scout/vnext_workflow_v1.py",
    "docs/artifacts/vnext-shared-foundation-workflow-boundary-v1-contract.json",
    "docs/artifacts/vnext-shared-foundation-workflow-boundary-v1-fixtures.json",
    "docs/vnext-shared-foundation-workflow-boundary-v1.md",
    "tests/test_vnext_shared_foundation_workflow_boundary_v1.py",
    "scripts/audit_vnext_shared_foundation_workflow_boundary_v1.py",
]
ALLOWED_IMPORT_ROOTS = {"__future__", "argparse", "ast", "collections", "dataclasses", "hashlib", "json", "os", "pathlib", "re", "stat", "subprocess", "typing", "uuid", "pastila_scout", "pytest", "vnext_foundation_v1"}
FORBIDDEN_TERMS = ("vnext_scout", "r2", "sqlite3", "requests", "httpx", "urllib", "transformers", "torch", "evaluation", "archive")


def identity(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module.split(".")[0])
    return result


def commit_scope(commit: str) -> list[str]:
    output = subprocess.check_output(["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit], cwd=ROOT, text=True)
    return sorted(line for line in output.splitlines() if line)


def audit(commit: str | None = None) -> dict[str, object]:
    assert len(FILES) == 7 and len(set(FILES)) == 7
    for name in FILES:
        assert (ROOT / name).is_file(), name
    contract = json.loads((ROOT / FILES[2]).read_text(encoding="utf-8"))
    fixtures = json.loads((ROOT / FILES[3]).read_text(encoding="utf-8"))
    assert contract["status"] == "ISOLATED_NOT_ACTIVE"
    assert contract["authority_commit"] == "4bd80d1aebede3737292cf97640e5d63ca07786e"
    assert contract["architecture"] == "MODULAR_MONOLITH"
    assert contract["product_root"] == "/root/pastila-vnext/v1"
    assert contract["active_integration"] is False
    assert contract["product_lock_modified"] is False
    assert contract["product_root_modified"] is False
    assert contract["voice"] == "DISABLED_UNTIL_PROMOTION"
    assert contract["stop_all_candidates"] is True
    assert contract["legacy_dependency_count"] == 0
    assert len(fixtures["cases"]) == 19
    source_files = [ROOT / FILES[0], ROOT / FILES[1]]
    imported = set().union(*(imports(path) for path in source_files))
    assert imported <= ALLOWED_IMPORT_ROOTS, sorted(imported - ALLOWED_IMPORT_ROOTS)
    combined = "\n".join(path.read_text(encoding="utf-8").casefold() for path in source_files)
    for term in FORBIDDEN_TERMS:
        assert term not in combined, term
    scope = commit_scope(commit) if commit else sorted(FILES)
    if commit:
        assert scope == sorted(FILES), {"expected": sorted(FILES), "actual": scope}
    return {
        "verdict": "PASS",
        "blockers": 0,
        "scope": scope,
        "blob_sha256": {name: identity(ROOT / name) for name in FILES},
        "contract_identity": hashlib.sha256(json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "fixture_identity": hashlib.sha256(json.dumps(fixtures, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "external_runtime_dependencies": [],
        "legacy_dependency_count": 0,
        "product_root_dependency": False,
        "network": False,
        "inference": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit")
    args = parser.parse_args()
    print(json.dumps(audit(args.commit), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

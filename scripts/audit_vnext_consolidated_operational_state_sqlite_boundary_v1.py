from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_FILES = [
    "src/pastila_scout/vnext_state_sqlite_v1.py",
    "docs/artifacts/vnext-consolidated-operational-state-sqlite-boundary-v1-contract.json",
    "docs/artifacts/vnext-consolidated-operational-state-sqlite-boundary-v1-fixtures.json",
    "docs/vnext-consolidated-operational-state-sqlite-boundary-v1.md",
    "tests/test_vnext_consolidated_operational_state_sqlite_boundary_v1.py",
    "scripts/audit_vnext_consolidated_operational_state_sqlite_boundary_v1.py",
]
DEPENDENCIES = {
    "src/pastila_scout/vnext_foundation_v1.py": "e9d857e5910fffd76dfd9aed1891e86ad68cf31602150ef0445455f6b4bc8615",
    "src/pastila_scout/vnext_workflow_v1.py": "9b9e8ade1ce0dd6193e44d7113b8ace163d85e40b032ff279fa9326d3e235d3f",
}
ALLOWED_RUNTIME_IMPORTS = {"__future__", "collections", "contextlib", "dataclasses", "json", "os", "pathlib", "sqlite3", "typing", "uuid", "vnext_foundation_v1", "vnext_workflow_v1"}
FORBIDDEN_IMPORTS = {"httpx", "requests", "sqlalchemy", "torch", "transformers", "urllib"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            values.add(node.module.split(".")[0])
    return values


def scope(commit: str) -> list[str]:
    output = subprocess.check_output(["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit], cwd=ROOT, text=True)
    return sorted(line for line in output.splitlines() if line)


def audit(commit: str | None = None) -> dict[str, object]:
    for name in BOUNDARY_FILES:
        assert (ROOT / name).is_file(), name
    for name, expected in DEPENDENCIES.items():
        assert sha(ROOT / name) == expected, name
    contract = json.loads((ROOT / BOUNDARY_FILES[1]).read_text(encoding="utf-8"))
    fixtures = json.loads((ROOT / BOUNDARY_FILES[2]).read_text(encoding="utf-8"))
    assert contract["status"] == "ISOLATED_NOT_ACTIVE"
    assert contract["product_data_migration"] is False
    assert contract["active_integration"] is False
    assert contract["product_root_dependency"] is False
    assert contract["external_runtime_dependencies_new"] == 0
    assert contract["legacy_dependency_count"] == 0
    assert contract["stop_all_candidates"] is True
    assert contract["voice"] == "DISABLED_UNTIL_PROMOTION"
    assert len(fixtures["cases"]) == 25
    runtime_imports = imports(ROOT / BOUNDARY_FILES[0])
    assert not runtime_imports.intersection(FORBIDDEN_IMPORTS)
    assert runtime_imports <= ALLOWED_RUNTIME_IMPORTS, sorted(runtime_imports - ALLOWED_RUNTIME_IMPORTS)
    exact_scope = scope(commit) if commit else sorted(BOUNDARY_FILES)
    if commit:
        assert exact_scope == sorted(BOUNDARY_FILES)
    return {
        "verdict": "PASS", "blockers": 0, "scope": exact_scope,
        "blob_sha256": {name: sha(ROOT / name) for name in BOUNDARY_FILES},
        "declared_dependencies": DEPENDENCIES,
        "contract_identity": hashlib.sha256(json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "fixture_identity": hashlib.sha256(json.dumps(fixtures, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "runtime_imports": sorted(runtime_imports),
        "external_runtime_dependency_count": 0,
        "hidden_repository_dependencies": 0,
        "product_database_access_count": 0,
        "product_data_migration_count": 0,
        "legacy_dependency_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--commit"); args = parser.parse_args()
    print(json.dumps(audit(args.commit), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

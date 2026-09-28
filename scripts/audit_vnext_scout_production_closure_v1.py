from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_FILES = [
    "src/pastila_scout/vnext_scout_production_v1.py",
    "docs/artifacts/vnext-scout-production-closure-v1-contract.json",
    "docs/artifacts/vnext-scout-production-closure-v1-fixtures.json",
    "docs/artifacts/vnext-scout-production-closure-v1-source-diagnostic.json",
    "docs/vnext-scout-production-closure-v1.md",
    "tests/test_vnext_scout_production_closure_v1.py",
    "scripts/audit_vnext_scout_production_closure_v1.py",
]
DEPENDENCIES = {
    "src/pastila_scout/vnext_foundation_v1.py": "e9d857e5910fffd76dfd9aed1891e86ad68cf31602150ef0445455f6b4bc8615",
    "src/pastila_scout/vnext_workflow_v1.py": "9b9e8ade1ce0dd6193e44d7113b8ace163d85e40b032ff279fa9326d3e235d3f",
    "src/pastila_scout/vnext_state_sqlite_v1.py": "16983a09d3a7821674790dc19c6befe386ee894404dca322e68f15d517d0a5d5",
    "docs/artifacts/editor-vnext-minimal-scout-sources-v1.json": "d727bd2febd2990878d411b45b3cb8c84c17f342e3b490eb17b2f1ec5efbbc1a",
    "docs/artifacts/editor-vnext-minimal-scout-sourcepacket-contract-v1.json": "2a1cfbd8f0f3bc3a17de096a97ef2437a1f88a40589ee9b5b3c6238ccb98f639",
}
ALLOWED_IMPORTS = {
    "__future__", "collections", "concurrent", "dataclasses", "datetime", "email", "gzip", "html", "json", "pathlib",
    "re", "typing", "urllib", "xml", "vnext_foundation_v1", "vnext_state_sqlite_v1", "vnext_workflow_v1",
}
FORBIDDEN_IMPORTS = {"bs4", "feedparser", "httpx", "pydantic", "requests", "sqlalchemy", "torch", "transformers"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def published_text_sha(path: Path) -> str:
    """Hash Git-canonical text bytes while tolerating a Windows checkout."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def object_identity(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module.split(".")[0])
    return result


def commit_scope(commit: str) -> list[str]:
    output = subprocess.check_output(
        ["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit],
        cwd=ROOT,
        text=True,
    )
    return sorted(line for line in output.splitlines() if line)


def audit(commit: str | None = None) -> dict[str, object]:
    for name in BOUNDARY_FILES:
        assert (ROOT / name).is_file(), name
    for name, expected in DEPENDENCIES.items():
        assert published_text_sha(ROOT / name) == expected, name
    contract = json.loads((ROOT / BOUNDARY_FILES[1]).read_text(encoding="utf-8"))
    fixtures = json.loads((ROOT / BOUNDARY_FILES[2]).read_text(encoding="utf-8"))
    diagnostic = json.loads((ROOT / BOUNDARY_FILES[3]).read_text(encoding="utf-8"))
    assert contract["status"] == "ISOLATED_NOT_ACTIVE"
    assert contract["product_data_migration"] is False and contract["active_integration"] is False
    assert contract["external_runtime_dependencies_new"] == 0
    assert contract["legacy_dependency_count"] == 0
    assert contract["stop_all_candidates"] is True and contract["voice"] == "DISABLED_UNTIL_PROMOTION"
    assert diagnostic["observations"] == 56 and diagnostic["observations"] <= 100
    assert diagnostic["mandatory_checkpoint"] == "CONTINUE"
    assert diagnostic["configured_sources"] == diagnostic["post_repair_expected_source_support"] == 54
    assert diagnostic["finding"]["post_repair_fixture"] == "PASS"
    assert len(fixtures["grouping_cases"]) == 8
    runtime_imports = imports(ROOT / BOUNDARY_FILES[0])
    assert not runtime_imports.intersection(FORBIDDEN_IMPORTS)
    assert runtime_imports <= ALLOWED_IMPORTS, sorted(runtime_imports - ALLOWED_IMPORTS)
    exact_scope = commit_scope(commit) if commit else sorted(BOUNDARY_FILES)
    if commit:
        assert exact_scope == sorted(BOUNDARY_FILES)
    return {
        "verdict": "PASS",
        "blockers": 0,
        "scope": exact_scope,
        "blob_sha256": {name: sha(ROOT / name) for name in BOUNDARY_FILES},
        "declared_dependencies": DEPENDENCIES,
        "contract_identity": object_identity(contract),
        "fixture_identity": object_identity(fixtures),
        "source_diagnostic_identity": object_identity(diagnostic),
        "source_observations": diagnostic["observations"],
        "configured_sources": diagnostic["configured_sources"],
        "runtime_imports": sorted(runtime_imports),
        "external_runtime_dependency_count": 0,
        "hidden_repository_dependencies": 0,
        "product_database_access_count": 0,
        "product_data_migration_count": 0,
        "legacy_dependency_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit")
    arguments = parser.parse_args()
    print(json.dumps(audit(arguments.commit), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

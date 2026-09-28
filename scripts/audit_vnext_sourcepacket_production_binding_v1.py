from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_sourcepacket_binding_v1 import (
    bind_source_packet,
    validate_bound_source_packet,
)

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_FILES = [
    "src/pastila_scout/vnext_sourcepacket_binding_v1.py",
    "docs/artifacts/vnext-sourcepacket-production-binding-closure-v1.json",
    "docs/artifacts/vnext-sourcepacket-production-binding-v1-fixture.json",
    "docs/vnext-sourcepacket-production-binding-closure-v1.md",
    "tests/test_vnext_sourcepacket_production_binding_v1.py",
    "scripts/audit_vnext_sourcepacket_production_binding_v1.py",
]
DEPENDENCIES = {
    "src/pastila_scout/vnext_scout_production_v1.py": "c1f57af99e9f453df773465df6d25cac328a164947ffcc9f760887cb9a187503",
    "src/pastila_scout/vnext_foundation_v1.py": "e9d857e5910fffd76dfd9aed1891e86ad68cf31602150ef0445455f6b4bc8615",
    "src/pastila_scout/vnext_workflow_v1.py": "9b9e8ade1ce0dd6193e44d7113b8ace163d85e40b032ff279fa9326d3e235d3f",
    "src/pastila_scout/vnext_state_sqlite_v1.py": "16983a09d3a7821674790dc19c6befe386ee894404dca322e68f15d517d0a5d5",
    "docs/artifacts/editor-vnext-minimal-scout-sourcepacket-contract-v1.json": "2a1cfbd8f0f3bc3a17de096a97ef2437a1f88a40589ee9b5b3c6238ccb98f639",
    "docs/artifacts/vnext-scout-production-closure-v1-contract.json": "f9991404015206ff2e2792624e9d6508e1fa12c33bd718faa8b3e8ed22670b73",
}
ALLOWED_IMPORTS = {"__future__", "collections", "re", "vnext_foundation_v1"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def published_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module.split(".")[-1] if node.level else node.module.split(".")[0])
    return result


def commit_scope(commit: str) -> list[str]:
    output = subprocess.check_output(["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit, "--"], cwd=ROOT, text=True)
    return sorted(line for line in output.splitlines() if line)


def audit(commit: str | None = None) -> dict[str, object]:
    for name in BOUNDARY_FILES:
        assert (ROOT / name).is_file(), name
    for name, expected in DEPENDENCIES.items():
        assert published_sha(ROOT / name) == expected, name
    closure = json.loads((ROOT / BOUNDARY_FILES[1]).read_text(encoding="utf-8"))
    fixture = json.loads((ROOT / BOUNDARY_FILES[2]).read_text(encoding="utf-8"))
    frozen = json.loads((ROOT / "docs/artifacts/editor-vnext-minimal-scout-sourcepacket-contract-v1.json").read_text(encoding="utf-8"))
    assert object_identity({key: value for key, value in closure.items() if key != "closure_identity"}) == closure["closure_identity"]
    assert object_identity({key: value for key, value in fixture.items() if key != "fixture_identity"}) == fixture["fixture_identity"]
    assert object_identity({key: value for key, value in frozen.items() if key != "contract_identity"}) == frozen["contract_identity"]
    reproduced = bind_source_packet(fixture["source_packet"])
    assert reproduced == fixture["expected_bound_packet"]
    validate_bound_source_packet(reproduced)
    assert reproduced["schema"] == frozen["source_packet"]["schema"]
    assert reproduced["selection_authority"] == frozen["handoff"]["selection_authority"]
    assert reproduced["completeness"] == frozen["handoff"]["source_packet_completeness"]
    assert [span["text"].encode() for span in reproduced["spans"]] == [span["text"].encode() for span in fixture["source_packet"]["spans"]]
    assert closure["status"] == "ISOLATED_NOT_ACTIVE"
    assert not closure["historical_database_migrated"] and not closure["product_data_migration"] and not closure["active_integration"]
    assert not closure["product_root_dependency"] and closure["legacy_dependency_count"] == 0
    assert closure["stop_all_candidates"] and closure["voice"] == "DISABLED_UNTIL_PROMOTION"
    runtime_imports = imports(ROOT / BOUNDARY_FILES[0])
    assert runtime_imports <= ALLOWED_IMPORTS, sorted(runtime_imports - ALLOWED_IMPORTS)
    scope = commit_scope(commit) if commit else sorted(BOUNDARY_FILES)
    if commit:
        assert scope == sorted(BOUNDARY_FILES)
    return {
        "verdict": "PASS", "blockers": 0, "scope": scope,
        "blob_sha256": {name: sha(ROOT / name) for name in BOUNDARY_FILES},
        "declared_dependencies": DEPENDENCIES,
        "closure_identity": closure["closure_identity"],
        "fixture_identity": fixture["fixture_identity"],
        "bound_packet_identity": reproduced["packet_identity"],
        "frozen_contract_identity": frozen["contract_identity"],
        "source_text_bytes_preserved": True,
        "historical_database_migrated": False,
        "product_data_migration": False,
        "active_integration": False,
        "product_root_dependency": False,
        "legacy_dependency_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--commit")
    print(json.dumps(audit(parser.parse_args().commit), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

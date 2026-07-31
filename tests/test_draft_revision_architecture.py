"""M6C.6D Part 1 package-boundary checks."""

import ast
from pathlib import Path

PACKAGE = Path("src/pastila_scout/editor/qa/corrective_action/executors/draft_revision")


def test_part_one_has_contracts_but_no_runtime_or_forbidden_imports():
    names = {path.name for path in PACKAGE.glob("*.py")}
    assert not names & {
        "executor.py",
        "service.py",
        "runtime.py",
        "provider.py",
        "gateway.py",
    }
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in PACKAGE.glob("*.py")
    )
    for forbidden in (
        "openai",
        "anthropic",
        "httpx",
        "sqlite3",
        "DraftRegenerationExecutor",
    ):
        assert forbidden not in source
    classes = {
        node.name
        for path in PACKAGE.glob("*.py")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.ClassDef)
    }
    assert "DraftRevisionExecutor" not in classes
    assert "DraftRevisionRequest" in classes
    assert "DraftRevisionResult" in classes

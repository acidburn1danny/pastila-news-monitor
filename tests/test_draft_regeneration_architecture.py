"""M6C.6C Part 1 architecture and forbidden-boundary tests."""

import ast
from pathlib import Path

PACKAGE = Path(
    "src/pastila_scout/editor/qa/corrective_action/executors/draft_regeneration"
)


def test_part_one_contains_contracts_but_no_runtime() -> None:
    names = {path.name for path in PACKAGE.glob("*.py")}
    assert not names & {
        "executor.py",
        "service.py",
        "generation.py",
        "provider.py",
        "adapter.py",
        "workflow.py",
        "runtime.py",
    }
    classes = set()
    functions = set()
    for path in PACKAGE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef):
                classes.add(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.add(node.name)
    assert "DraftRegenerationExecutor" not in classes
    assert (
        not {"execute", "regenerate", "run_generation", "invoke_generation"} & functions
    )


def test_part_one_has_no_provider_infrastructure_or_dispatch_runtime_imports() -> None:
    imports = set()
    for path in PACKAGE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
    forbidden = (
        "openai",
        "anthropic",
        "httpx",
        "sqlite3",
        "database",
        "queue",
        "notification",
        "publication",
        "pastila_scout.cli",
        "controlled_generator",
        "execution_dispatch.dispatcher",
        "execution_dispatch.service",
    )
    assert all(not any(item in module for item in forbidden) for module in imports)


def test_frozen_dispatch_package_has_no_reverse_dependency() -> None:
    dispatch = Path("src/pastila_scout/editor/qa/corrective_action/execution_dispatch")
    assert all(
        "draft_regeneration" not in path.read_text(encoding="utf-8")
        for path in dispatch.glob("*.py")
    )

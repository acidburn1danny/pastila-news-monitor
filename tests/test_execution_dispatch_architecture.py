"""M6C.6B Part 4 dependency and operational-boundary audit tests."""

import ast
from pathlib import Path

PACKAGE = Path("src/pastila_scout/editor/qa/corrective_action/execution_dispatch")


def _production_classes() -> tuple[str, ...]:
    names = []
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names.extend(node.name for node in tree.body if isinstance(node, ast.ClassDef))
    return tuple(names)


def test_one_authoritative_dispatcher_evaluator_and_resolver_exist() -> None:
    names = _production_classes()
    assert names.count("CorrectiveActionExecutionDispatcher") == 1
    assert names.count("DispatchEligibilityEvaluator") == 1
    assert names.count("CapabilityResolver") == 1


def test_no_capability_specific_executor_or_discovery_surface_exists() -> None:
    names = _production_classes()
    forbidden_classes = {
        "DraftRevisionExecutor",
        "DraftRegenerationExecutor",
        "ManualReviewRoutingExecutor",
        "NoExecutionExecutor",
        "WorkflowBlockExecutor",
    }
    assert forbidden_classes.isdisjoint(names)
    registry = (PACKAGE / "registry.py").read_text(encoding="utf-8")
    bindings = (PACKAGE / "bindings.py").read_text(encoding="utf-8")
    for mutation in ("def register(", "def unregister(", "entry_points", "scan("):
        assert mutation not in registry
        assert mutation not in bindings


def test_no_infrastructure_or_reverse_upstream_dependency_exists() -> None:
    imported = set()
    for path in PACKAGE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
    forbidden = {
        "openai",
        "httpx",
        "sqlite3",
        "requests",
        "socket",
        "pastila_scout.database",
        "pastila_scout.cli",
    }
    assert forbidden.isdisjoint(imported)
    upstream = Path("src/pastila_scout/editor/qa/corrective_action/execution_plan")
    assert all(
        "execution_dispatch" not in path.read_text(encoding="utf-8")
        for path in upstream.glob("*.py")
    )


def test_dispatch_runtime_contains_no_retry_or_fallback_loop() -> None:
    dispatcher = (PACKAGE / "dispatcher.py").read_text(encoding="utf-8").casefold()
    assert "retry" not in dispatcher
    assert "backoff" not in dispatcher
    assert "fallback" not in dispatcher
    tree = ast.parse(dispatcher)
    assert not any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(tree))

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_packaged_wsl_v1_1_transport_smoke.py"


def test_packaged_smoke_is_transport_only_and_import_safe():
    source = SCRIPT.read_text("utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "pastila_scout.wsl_execution_v1" in imported_modules
    assert "pastila_scout.wsl_execution_v1_1" in imported_modules
    assert not imported_modules.intersection(
        {"torch", "transformers", "peft", "openai", "ollama"}
    )
    assert "AutoModel" not in source
    assert "AutoTokenizer" not in source
    assert ".generate(" not in source


def test_packaged_smoke_execution_remains_explicit_and_zero_inference():
    source = SCRIPT.read_text("utf-8")
    tree = ast.parse(source)
    main_guards = [
        node
        for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
    ]

    assert len(main_guards) == 1
    assert 'authority_reference="zero-inference:installed-build"' in source
    assert 'executable="/usr/bin/printf"' in source
    assert "boundary.execute(invocation, timeout_seconds=30)" in source

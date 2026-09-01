import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/pastila_scout/humor_batch2_development_constructor_v5_3_1_runtime.py"


def function(tree, name):
    return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)


def calls(node):
    return [(item.func.id, item.lineno) for item in ast.walk(node)
            if isinstance(item, ast.Call) and isinstance(item.func, ast.Name)]


def test_v5_3_1_provider_emitter_validate_alignment_and_semantics_before_bytes():
    tree = ast.parse(RUNTIME.read_text(encoding="utf-8"))
    provider = calls(function(tree, "realize_aligned_semantic_typed_plan"))
    emitter = calls(function(tree, "emit_aligned_semantic_candidate_utf8"))
    assert [name for name, _ in provider].count("validate_semantic_plan") == 1
    assert [name for name, _ in provider].count("validate_surface_semantics") == 1
    assert [name for name, _ in provider].count("_validate_aligned_structure") == 1
    emitter_lines = {name: line for name, line in emitter}
    assert emitter_lines["validate_surface_semantics"] < emitter_lines["_validate_aligned_structure"]
    source = ast.unparse(function(tree, "emit_aligned_semantic_candidate_utf8"))
    assert source.index("_validate_aligned_structure") < source.index(".encode('utf-8')")


def test_v5_3_1_runtime_is_pathless_and_does_not_invoke_any_component():
    source = RUNTIME.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
    assert not imports.intersection({"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "torch", "transformers"})
    assert "pilot11" not in source.casefold()

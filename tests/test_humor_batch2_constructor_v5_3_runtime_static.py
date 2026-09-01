import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/pastila_scout/humor_batch2_development_constructor_v5_3_runtime.py"


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)


def _named_call_lines(function: ast.FunctionDef) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            result.setdefault(node.func.id, []).append(node.lineno)
    return result


def test_v5_3_provider_and_emitter_enforce_semantics_in_order_without_invocation() -> None:
    tree = ast.parse(RUNTIME.read_text(encoding="utf-8"))
    provider = _function(tree, "realize_semantic_typed_plan")
    emitter = _function(tree, "emit_semantic_candidate_utf8")
    provider_calls = _named_call_lines(provider)
    emitter_calls = _named_call_lines(emitter)
    assert provider_calls["validate_semantic_plan"][0] < provider_calls["realize_typed_plan"][0]
    assert provider_calls["realize_typed_plan"][0] < provider_calls["validate_surface_semantics"][0]
    assert emitter_calls["validate_surface_semantics"][0] < emitter_calls["emit_candidate_utf8"][0]
    assert len(provider_calls["validate_semantic_plan"]) == 1
    assert len(provider_calls["validate_surface_semantics"]) == 1
    assert len(emitter_calls["validate_surface_semantics"]) == 1


def test_v5_3_runtime_is_pathless_and_has_no_embedded_identity_or_pilot_routing() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
    assert not imports.intersection({"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "torch", "transformers", "importlib"})
    assert "pilot10" not in source.casefold()
    assert not any(len(token) == 64 and all(ch in "0123456789abcdef" for ch in token.casefold()) for token in source.split())

"""AST-only V5.2 runtime audit; provider and emitter are never invoked."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src/pastila_scout/humor_batch2_development_constructor_v5_2_runtime.py"


def functions():
    tree = ast.parse(PATH.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_provider_requires_typed_plan_and_complete_lexicalization_manifest():
    provider = functions()["realize_typed_plan"]
    names = [arg.arg for arg in provider.args.kwonlyargs]
    assert names == ["exact_source", "typed_plan", "lexicalizations"]
    text = ast.unparse(provider)
    assert "lexicalization coverage must equal typed plan N/N" in text
    assert "SurfaceNodeWitness" in text
    assert "predecessor_node_ids=node.predecessor_node_ids" in text


def test_emitter_validates_before_encoding_and_checks_n_n_e_e_terminal():
    emitter = functions()["emit_candidate_utf8"]
    calls = [node for node in ast.walk(emitter) if isinstance(node, ast.Call)]
    validator_line = min(node.lineno for node in calls if isinstance(node.func, ast.Name) and node.func.id == "validate_realization_draft")
    encode_line = min(node.lineno for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "encode")
    assert validator_line < encode_line
    text = ast.unparse(emitter)
    assert "coverage.nodes_realized != coverage.nodes_required" in text
    assert "coverage.edges_realized != coverage.edges_required" in text
    assert "not coverage.terminal_result_realized" in text


def test_runtime_contains_no_candidate_template_or_external_access_imports():
    source = PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
    assert not imports.intersection({"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "torch", "transformers", "importlib"})
    assert "pilot09" not in source.casefold()
    assert "ABSURD_LOGICAL_EXTENSION" not in source

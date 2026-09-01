import ast
from pathlib import Path


def test_runner_has_one_provider_and_one_emitter_call_in_guarded_order():
    path = Path(__file__).resolve().parents[1] / "scripts/run_humor_batch2_development_pilot10_construction_once_v5_2.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    assert calls.count("realize_typed_plan") == 1
    assert calls.count("emit_candidate_utf8") == 1
    assert calls.count("write_bytes") == 0
    assert source.index("emit_candidate_utf8(typed_plan=plan") < source.index("CANDIDATE.write_bytes(candidate_bytes)")
    assert "if CANDIDATE.exists() or EVIDENCE.exists()" in source

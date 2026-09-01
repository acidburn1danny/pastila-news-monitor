import ast
from pathlib import Path

def test_pilot12_runner_is_single_use_and_persists_only_after_emission():
    source=(Path(__file__).resolve().parents[1]/"scripts/run_humor_batch2_development_pilot12_construction_once_v5_3_1.py").read_text(encoding="utf-8")
    calls=[n.func.id for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
    assert calls.count("realize_aligned_semantic_typed_plan")==1
    assert calls.count("emit_aligned_semantic_candidate_utf8")==1
    assert source.index("emit_aligned_semantic_candidate_utf8(") < source.index("CANDIDATE.write_bytes(candidate_bytes)")
    assert "if CANDIDATE.exists() or EVIDENCE.exists()" in source

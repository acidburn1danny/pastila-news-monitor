from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pilot09_runner_contains_one_constructor_edge_and_defers_collision_gate():
    path = ROOT / "scripts/run_humor_batch2_development_pilot09_construction_once_v5_1.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "construct_development_candidate_v5_1"
    ]
    assert len(calls) == 1
    text = path.read_text(encoding="utf-8")
    assert "NOT_PERFORMED_REQUIRES_SEPARATE_AUTHORIZATION_BEFORE_G02" in text
    assert '"g02_eligibility": False' in text

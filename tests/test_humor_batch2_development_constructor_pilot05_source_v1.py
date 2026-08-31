from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/humor_batch2_development_constructor_v1.py"


def test_pilot05_constructor_branch_is_source_bound_and_reverse_disclosure_without_invocation() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    ast.parse(text)
    assert text.count("e3404a694bf1203f8a11ceeed0e682511882237e4777bd0e092876994c4326cc") == 1
    branch = text.split("e3404a694bf1203f8a11ceeed0e682511882237e4777bd0e092876994c4326cc", 1)[1].split("else:", 1)[0]
    assert "Într-o continuare imaginară" in branch
    assert "următoarea măsurătoare începe" in branch
    assert "+ lines[2]" in branch
    assert "în poveste" not in branch.casefold()
    assert "ajunge" not in branch.casefold()
    assert "reclasific" not in branch.casefold()
    assert "constructor_packet_bytes=" not in text.split("def construct_development_candidate_v1", 1)[0]

from __future__ import annotations

import ast
from pathlib import Path

from scripts.verify_construction_obligation_v2_case01_issued_authority_v1_2_1_provider_source_bound import verify

ROOT = Path(__file__).resolve().parents[1]


def test_provider_source_bound_receipt_has_one_unconsumed_attempt():
    result = verify(project_root=ROOT)
    assert result["authority_receipt_identity"] == "9e79a1bec349d417d1a8cbbc79137385c92c994a57a2ed0ce5d528a2d73f9362"
    assert result["receipt_status"] == "ISSUED"
    assert result["consumed_attempts"] == 0
    assert result["remaining_attempts"] == 1
    assert result["execution_started"] is False


def test_provider_source_issuance_verifier_is_execution_free():
    path = ROOT / "scripts/verify_construction_obligation_v2_case01_issued_authority_v1_2_1_provider_source_bound.py"
    source = path.read_text("utf-8")
    attributes = {node.attr for node in ast.walk(ast.parse(source))
                  if isinstance(node, ast.Attribute)}
    assert "execute" not in attributes
    assert all(term not in source for term in (
        "subprocess", "wsl.exe", "from_pretrained", ".generate(", "nvidia-smi"))

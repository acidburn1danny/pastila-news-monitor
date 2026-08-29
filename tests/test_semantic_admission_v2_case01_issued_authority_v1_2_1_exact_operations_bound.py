from __future__ import annotations

import ast
from pathlib import Path

from scripts.verify_construction_obligation_v2_case01_issued_authority_v1_2_1_exact_operations_bound import verify

ROOT = Path(__file__).resolve().parents[1]


def test_exact_operations_bound_receipt_has_one_unconsumed_attempt():
    result = verify(project_root=ROOT)
    assert result["authority_receipt_identity"] == "b9176dbe4d2d1d98eb43d6e13e20e9955010c5e5a30ee89f609197dcb35b24a9"
    assert result["receipt_status"] == "ISSUED"
    assert result["consumed_attempts"] == 0
    assert result["remaining_attempts"] == 1
    assert result["execution_started"] is False


def test_exact_operations_issuance_verifier_is_execution_free():
    path = ROOT / "scripts/verify_construction_obligation_v2_case01_issued_authority_v1_2_1_exact_operations_bound.py"
    source = path.read_text("utf-8")
    attributes = {node.attr for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Attribute)}
    assert "execute" not in attributes
    assert all(term not in source for term in (
        "subprocess", "wsl.exe", "from_pretrained", ".generate(", "nvidia-smi"))

from __future__ import annotations

import ast
from pathlib import Path

from scripts.verify_construction_obligation_v2_case01_issued_authority_v1_2_1_runtime_source_bound import verify

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_source_bound_receipt_is_frozen_as_consumed():
    result = verify(project_root=ROOT)
    assert result["authority_receipt_identity"] == "9ef49ce6b0b3992928a6904427497522b51eac03a7e5aa79297298b4b348c397"
    assert result["receipt_status"] == "ISSUED"
    assert result["consumed_attempts"] == 1
    assert result["remaining_attempts"] == 0
    assert result["execution_started"] is True


def test_runtime_source_issuance_verifier_is_execution_free():
    path = ROOT / "scripts/verify_construction_obligation_v2_case01_issued_authority_v1_2_1_runtime_source_bound.py"
    source = path.read_text("utf-8")
    attributes = {node.attr for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Attribute)}
    assert "execute" not in attributes
    assert all(term not in source for term in (
        "subprocess", "wsl.exe", "from_pretrained", ".generate(", "nvidia-smi"))

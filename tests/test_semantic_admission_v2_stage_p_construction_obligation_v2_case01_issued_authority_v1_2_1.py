from __future__ import annotations

import ast
from pathlib import Path

from scripts.verify_construction_obligation_v2_case01_issued_authority_v1_2_1 import verify

ROOT = Path(__file__).resolve().parents[1]


def test_exact_v1_2_1_receipt_is_issued_with_one_unconsumed_attempt():
    result = verify(project_root=ROOT)
    assert result["authority_receipt_identity"] == "d9d72feefa7015021ca79388dcee837c21103c87fef0733903b3d73f8e233da4"
    assert result["receipt_status"] == "ISSUED"
    assert result["consumed_attempts"] == 0
    assert result["remaining_attempts"] == 1
    assert result["execution_started"] is False


def test_v1_2_1_issuance_verifier_has_no_execution_callsite():
    path = ROOT / "scripts/verify_construction_obligation_v2_case01_issued_authority_v1_2_1.py"
    tree = ast.parse(path.read_text("utf-8"))
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "execute" not in attributes
    text = path.read_text("utf-8")
    assert all(term not in text for term in (
        "subprocess", "from_pretrained", ".generate(", "nvidia-smi", "wsl.exe"))

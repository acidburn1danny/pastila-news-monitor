from __future__ import annotations

import ast
from pathlib import Path

from scripts.verify_construction_obligation_v2_case01_issued_authority_v1_2_1_host_evidence_domain_bound import verify

ROOT = Path(__file__).resolve().parents[1]


def test_host_evidence_domain_receipt_is_issued_unconsumed():
    result = verify(project_root=ROOT)
    assert result["authority_receipt_identity"] == (
        "e8bf4ca020ff1a91b90e1025d8768a22fa18dd02c138ed035b574475e3d94ddd")
    assert result["receipt_status"] == "ISSUED"
    assert result["consumed_attempts"] == 0
    assert result["remaining_attempts"] == 1
    assert result["execution_started"] is False
    assert result["evidence_root_absent"] is True


def test_host_evidence_domain_issuance_verifier_is_execution_free():
    path = ROOT / "scripts/verify_construction_obligation_v2_case01_issued_authority_v1_2_1_host_evidence_domain_bound.py"
    source = path.read_text("utf-8")
    attributes = {node.attr for node in ast.walk(ast.parse(source))
                  if isinstance(node, ast.Attribute)}
    assert "execute" not in attributes
    assert all(term not in source for term in (
        "subprocess", "wsl.exe", "from_pretrained", ".generate(", "nvidia-smi"))

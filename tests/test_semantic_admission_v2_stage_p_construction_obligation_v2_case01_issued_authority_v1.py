from __future__ import annotations

import ast
from pathlib import Path

from scripts.verify_construction_obligation_v2_case01_issued_authority_v1 import (
    COMMAND_IDENTITY,
    PACKET_COMMIT,
    PACKET_IDENTITY,
    RECEIPT_IDENTITY,
    verify,
)

ROOT = Path(__file__).resolve().parents[1]


def test_exact_reviewed_authority_is_issued_but_unconsumed() -> None:
    result = verify(project_root=ROOT)
    assert result == {
        "packet_commit": PACKET_COMMIT,
        "packet_identity": PACKET_IDENTITY,
        "command_identity": COMMAND_IDENTITY,
        "authority_receipt_identity": RECEIPT_IDENTITY,
        "receipt_status": "ISSUED",
        "attempt_ceiling": 1,
        "consumed_attempts": 0,
        "remaining_attempts": 1,
        "execution_started": False,
    }


def test_issuance_verifier_has_no_execution_callsite() -> None:
    path = ROOT / "scripts/verify_construction_obligation_v2_case01_issued_authority_v1.py"
    tree = ast.parse(path.read_text("utf-8"))
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "execute" not in attributes
    text = path.read_text("utf-8")
    assert all(term not in text for term in (
        "subprocess", "from_pretrained", ".generate(", "nvidia-smi", "wsl.exe"))

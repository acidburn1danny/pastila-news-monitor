from __future__ import annotations

import ast
from pathlib import Path

from scripts.verify_construction_obligation_v2_case01_execution_attempt_v1 import (
    FREEZE_IDENTITY,
    verify,
)

ROOT = Path(__file__).resolve().parents[1]


def test_consumed_transport_failure_freeze_is_exact() -> None:
    manifest = verify(project_root=ROOT)
    assert manifest["freeze_identity"] == FREEZE_IDENTITY
    assert manifest["execution"]["status"] == "TRANSPORT_FAILURE"
    assert manifest["attempt"]["consumed_attempts"] == 1
    assert manifest["attempt"]["remaining_attempts"] == 0


def test_freeze_verifier_is_non_executing() -> None:
    path = ROOT / "scripts/verify_construction_obligation_v2_case01_execution_attempt_v1.py"
    tree = ast.parse(path.read_text("utf-8"))
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "execute" not in attributes
    text = path.read_text("utf-8")
    assert all(term not in text for term in (
        "subprocess", "from_pretrained", ".generate(", "nvidia-smi", "wsl.exe"))

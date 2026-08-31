"""Verify the owner-operated Pilot 06 signing helper without signing."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/owner_humor_batch2_development_pilot06_signing_v1.py"


def test_pilot06_helper_inspects_exact_frozen_challenges_without_secrets() -> None:
    output = subprocess.check_output([str(ROOT / ".venv/Scripts/python.exe"), str(HELPER), "inspect"], cwd=ROOT, text=True)
    items = json.loads(output)
    assert len(items) == 8 and len({item["nonce"] for item in items}) == 8
    assert all(item["prior_ledger_head"] == "20d5c36ec01ceaec6cd85131f6253bbd300f710021804ce3debf7d3880bc59b2" for item in items)


def test_pilot06_helper_is_owner_operated_and_never_embeds_private_material() -> None:
    source = HELPER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "The assistant may run ``inspect`` but must never run ``sign-all``." in source
    assert "private.pem" in source and '"private_key_included": False' in source
    assert "refusing repository-local secret/response path" in source
    assert not any(isinstance(node, ast.Constant) and isinstance(node.value, str) and "BEGIN PRIVATE KEY" in node.value for node in ast.walk(tree))

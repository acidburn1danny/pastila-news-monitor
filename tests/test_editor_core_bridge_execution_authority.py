from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_editor_core_bridge_execution_authority import audit  # noqa: E402


def test_published_execution_authority_remains_closed():
    result = audit(ROOT)
    assert result["execution_authority"] == "BLOCKED"
    assert result["matched_run_slots"] == 6
    assert result["optimizer_steps_authorized"] == 0
    assert result["holdout_access_authorized"] is False

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_editor_core_bridge_a1_a2_fixture_gate import (  # noqa: E402
    PROTOCOL,
    audit,
    check_pairs,
)
from project_editor_core_editorial_bridge_arms import arm_rows  # noqa: E402


@pytest.fixture(scope="module")
def rows():
    a1, _ = arm_rows(ROOT / "docs/artifacts", "A1")
    a2, _ = arm_rows(ROOT / "docs/artifacts", "A2")
    return a1, a2


def test_real_published_rows_fixture_only_close():
    result = audit()
    assert result["verdict"] == "PASS_FIXTURE_ONLY_REAL_TRAINING_BLOCKED"
    assert result["new_target_only_differences"] == 48
    assert result["identical_replay_rows"] == 48
    assert result["real_run_ready"] is False
    assert result["model_loaded"] is False and result["optimizer_steps"] == 0


@pytest.mark.parametrize("mutation,reason", [
    ("source", "instruction or source drift"),
    ("replay", "replay drift"),
    ("target", "target contrast absent"),
    ("duplicate", "arm duplicate id"),
])
def test_causal_drift_fail_closed(rows, mutation, reason):
    left, right = copy.deepcopy(rows)
    if mutation == "source":
        right[0]["messages"][1]["content"] += " altered"
    elif mutation == "replay":
        right[48]["messages"][2]["content"] += " altered"
    elif mutation == "target":
        right[0]["messages"][2]["content"] = left[0]["messages"][2]["content"]
    else:
        right[1]["example_id"] = right[0]["example_id"]
    with pytest.raises(ValueError, match=reason):
        check_pairs(left, right)


def test_training_authority_mutation_rejected(tmp_path):
    value = json.loads(PROTOCOL.read_bytes())
    value["training_authorized"] = True
    path = tmp_path / "staged.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="protocol byte identity"):
        audit(protocol_path=path)

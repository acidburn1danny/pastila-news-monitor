from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_editor_core_bridge_development_causal_pilot import (  # noqa: E402
    OPERATORS, PROTOCOL, aggregate_fixture_seed_signs, audit, decide_fixture,
)


def signs(default: str = "TIE") -> dict[str, tuple[str, str]]:
    return {f"case-{index}": (OPERATORS[index // 3], default) for index in range(24)}


def test_published_corpus_fixture_boundary():
    result = audit()
    assert result["verdict"] == "PASS_FIXTURE_ONLY_REAL_RUN_BLOCKED"
    assert result["development_cases"] == result["holdout_cases_excluded"] == 24
    assert result["new_target_only_differences"] == result["identical_replay_rows"] == 48
    assert result["optimizer_steps"] == 0 and result["real_run_ready"] is False


def test_protocol_mutation_rejected(tmp_path):
    value = json.loads(PROTOCOL.read_bytes())
    value["evaluation_splits_allowed"] = ["SYNTHETIC_HOLDOUT"]
    path = tmp_path / "successor.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="byte identity"):
        audit(protocol_path=path)


def test_stop_on_safety_harm():
    assert decide_fixture(signs("WIN"), (8, 8, 8), safety_harm=True) == "STOP"


def test_continue_requires_distributed_signal():
    value = signs()
    for index in (0, 3, 6, 9, 12, 15):
        value[f"case-{index}"] = (OPERATORS[index // 3], "WIN")
    assert decide_fixture(value, (4, 3, 1)) == "CONTINUE_TO_NATURALISTIC_INVESTMENT_ONLY"
    assert decide_fixture(value, (4, -1, -2)) == "REVISE"
    assert decide_fixture(value, (4, 3, 1), severe_romanian_regression=True) == "REVISE"


def test_no_signal_stops_and_bad_schema_rejected():
    assert decide_fixture(signs(), (0, 0, 0)) == "STOP_TARGET_DESIGN_UNDER_THIS_RECIPE"
    value = signs()
    value["case-0"] = ("INVALID_OPERATOR", "WIN")
    with pytest.raises(ValueError, match="fixture score schema"):
        decide_fixture(value, (1, 1, 1))


def test_operator_imbalance_rejected():
    value = signs()
    value["case-3"] = (OPERATORS[0], "WIN")
    with pytest.raises(ValueError, match="balance"):
        decide_fixture(value, (1, 1, 1))


def test_seed_majority_is_case_level_and_ties_do_not_win():
    value = {case: (operator, ("TIE", "TIE", "TIE"))
             for case, (operator, _) in signs().items()}
    value["case-0"] = (OPERATORS[0], ("WIN", "WIN", "LOSS"))
    value["case-1"] = (OPERATORS[0], ("WIN", "LOSS", "TIE"))
    cases, nets = aggregate_fixture_seed_signs(value)
    assert cases["case-0"][1] == "WIN" and cases["case-1"][1] == "TIE"
    assert nets == (2, 0, -1)
    assert decide_fixture(cases, nets) == "REVISE"

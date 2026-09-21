"""Focused R5 dataset and holdout closure tests; no model load."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

def test_r5_pack_closure():
    audit = load("scripts/audit_editor_core_v10_v12_targeted_r5_pack.py", "r5_audit")
    result = audit.audit()
    assert result["verdict"] == "PASS" and result["blockers"] == 0
    assert (result["new_rows"], result["replay_rows"], result["holdout_rows"]) == (12, 24, 12)
    assert result["frozen_holdout_targets_reused"] is False

def test_r5_replay_and_key_separation():
    builder = load("scripts/build_editor_core_v10_v12_targeted_r5_pack.py", "r5_builder")
    audit = load("scripts/audit_editor_core_v10_v12_targeted_r5_pack.py", "r5_audit_again")
    assert len(builder.select_replay()) == 24
    train, _ = builder.make_case(1, False)
    holdout, key = builder.make_case(13, True)
    assert train["example_id"] != holdout["example_id"]
    assert holdout["messages"][2]["content"] == key["assistant_target"]
    assert not any(row["example_id"] == holdout["example_id"] for row in audit.load("training"))

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_editor_core_bridge_causal_execution_authority as authority  # noqa: E402
import launch_editor_core_bridge_causal_successor_zero_step as zero  # noqa: E402
from build_editor_core_editorial_mechanics_bridge import canonical, sha  # noqa: E402


def test_successor_authority_exact_slots_and_local_publication_gate():
    obj = json.loads((ROOT / authority.AUTHORITY).read_bytes())
    core = {k: v for k, v in obj.items() if k != "authority_identity"}
    assert sha(canonical(core)) == authority.IDENTITY
    assert len(core["slots"]) == 6
    assert {(s["arm"], s["seed"]) for s in core["slots"]} == {
        (arm, seed) for arm in ("A1", "A2") for seed in authority.SEEDS}
    assert all(s["max_optimizer_steps"] == 12 and s["run_limit"] == 1 for s in core["slots"])
    assert core["holdout_access_authorized"] is False
    with pytest.raises(ValueError, match="successor not committed"):
        authority.verify("A1", authority.SEEDS[0], require_published=False)
    with pytest.raises(ValueError, match="unauthorized slot"):
        authority.verify("A3", authority.SEEDS[0])


def test_successor_mutation_rejected(tmp_path, monkeypatch):
    obj = json.loads((ROOT / authority.AUTHORITY).read_bytes())
    obj["slots"][0]["max_optimizer_steps"] = 13
    path = tmp_path / authority.AUTHORITY
    path.parent.mkdir(parents=True)
    path.write_bytes(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    monkeypatch.setattr(authority, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="successor authority contract"):
        authority.verify("A1", authority.SEEDS[0], require_published=False)


def test_successor_zero_step_combines_both_gates_fixture(monkeypatch, tmp_path):
    monkeypatch.setattr(zero, "verify", lambda arm, seed: {
        "authority_identity": authority.IDENTITY, "commit": "fixture-commit"})
    technical = {"status": "PASS_TECHNICAL_ZERO_STEP_REAL_RUN_AUTHORITY_STILL_BLOCKED",
                 "optimizer_steps": 0, "model_loaded": False, "target_entries_before": 0,
                 "target_entries_after": 0, "receipt_identity": "fixture-technical"}
    monkeypatch.setattr(zero, "zero_step", lambda *args: technical)
    result = zero.successor_zero_step(tmp_path, tmp_path, tmp_path, tmp_path, tmp_path,
                                      "a1-seed-271828")
    assert result["status"] == "PASS_PUBLISHED_AUTHORITY_AND_TECHNICAL_ZERO_STEP"
    assert result["optimizer_steps"] == 0
    technical["target_entries_after"] = 1
    with pytest.raises(ValueError, match="technical preflight"):
        zero.successor_zero_step(tmp_path, tmp_path, tmp_path, tmp_path, tmp_path,
                                 "a1-seed-271828")

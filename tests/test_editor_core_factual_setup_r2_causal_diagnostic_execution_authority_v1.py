import importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).parents[1]
def load(path,name):
 s=importlib.util.spec_from_file_location(name,ROOT/path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def test_authority_inventory_and_limits():
 d=json.loads((ROOT/"docs/artifacts/editor-core-factual-setup-r2-causal-diagnostic-v1-execution-authority.json").read_text(encoding="utf-8")); assert len(d["slots"])==12; assert len({x["slot_id"] for x in d["slots"]})==12; assert len({x["output_slug"] for x in d["slots"]})==12
 assert all(x["run_limit"]==1 and x["optimizer_steps"]==9 and x["fresh_zero_step_required"] for x in d["slots"]); assert d["owner_run_authorization_required"] and not d["real_runs_authorized_in_build_task"]
def test_supervisor_fixture_and_refusal(tmp_path):
 m=load("scripts/supervise_editor_core_factual_setup_r2_causal_diagnostic_v1.py","sup"); root=tmp_path/"slots"; root.mkdir(); r=m.fixture(root); assert r=={"status":"PASS_FIXTURE_ONLY","slots":12,"distinct_outputs":12,"model_loaded":False,"optimizer_steps":0,"real_runs":0}
 with pytest.raises(ValueError): m.plan(root)
def test_worker_real_branch_is_beyond_gate(monkeypatch):
 m=load("scripts/train_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.py","worker2"); monkeypatch.delenv("CAUSAL_DIAGNOSTIC_REAL_RUN_AUTHORIZED",raising=False)
 with pytest.raises(RuntimeError,match="not authorized"): m.run_slot(*([Path("x")]*6),"T0_CONTROL_S0_CONTROL",161803)

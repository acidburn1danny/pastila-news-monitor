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
def test_real_supervisor_and_route_require_separate_owner_authority(monkeypatch):
 m=load("scripts/supervise_editor_core_factual_setup_r2_causal_diagnostic_v1.py","sup2"); monkeypatch.delenv("EDITOR_CAUSAL_DIAGNOSTIC_OWNER_AUTHORIZED",raising=False); root=Path("unused")
 with pytest.raises(ValueError,match="owner run authorization"): m.execute_all(root,Path("route"),{})
 text=(ROOT/"scripts/run_editor_core_factual_setup_r2_causal_diagnostic_slot_v1.sh").read_text(); assert "EDITOR_CAUSAL_DIAGNOSTIC_OWNER_AUTHORIZED" in text and "--execute-authorized" in text and "--preflight-only" in text
 assert "EXPECTED_T0_SIGNAL" in text and "EXPECTED_T1_SIGNAL" in text

def test_supervisor_rejects_nonterminal_or_wrong_step_receipt(tmp_path,monkeypatch):
 m=load("scripts/supervise_editor_core_factual_setup_r2_causal_diagnostic_v1.py","sup3"); root=tmp_path/"slots"; root.mkdir(); monkeypatch.setenv("EDITOR_CAUSAL_DIAGNOSTIC_OWNER_AUTHORIZED","1")
 def fake_run(command,check):
  out=Path(command[8]); (out/"terminal.json").write_text(json.dumps({"status":"PASS_TRAINING_TERMINAL","optimizer_steps":8,"arm":command[11],"seed":int(command[12])}))
 monkeypatch.setattr(m.subprocess,"run",fake_run)
 common={k:Path(k) for k in ("rootfs","model","checkpoint","corpus","control","challenger","development","worker","verifier","route","preflight")}
 with pytest.raises(ValueError,match="terminal closure failure"): m.execute_all(root,Path("training-route"),common)

import ast,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];RUNNER=ROOT/"scripts/run_production_core_shadow_qualification_v10.py";LAUNCHER=ROOT/"scripts/launch_production_core_successor_development_gate_v10.sh"
def module():
 spec=importlib.util.spec_from_file_location("shadow_v10",RUNNER);value=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(value);return value
def test_shadow_is_bound_disjoint_and_zero_attempt():
 source=RUNNER.read_text("utf-8");ast.parse(source)
 for witness in ("render_shadow_qualification_messages","assert_phase_equivalence","len(rows)!=240","SHADOW_QUALIFICATION","V10 shadow projection mismatch",'"qualification_rows_used":0','"qualification_attempt_consumed":False',"maximum_input_tokens","unicodedata.normalize"):
  assert witness in source
 assert "render_development_messages" not in source and "render_qualification_messages" not in source
def test_shadow_repetition_boundary():
 value=module();phrase="unu doi trei patru cinci sase sapte opt"
 assert value.repeated_ngram_ceiling(" ".join([phrase]*3))==3
 assert value.repeated_ngram_ceiling(" ".join([phrase]*4))==4
def test_launcher_remains_offline_and_read_only():
 source=LAUNCHER.read_text("utf-8")
 assert "unshare --mount --net" in source and "HF_HUB_OFFLINE=1" in source
 assert "mount -o remount,bind,ro" in source and "CONTRACT_SHA256" in source and "EDITORIAL_SHA256" in source

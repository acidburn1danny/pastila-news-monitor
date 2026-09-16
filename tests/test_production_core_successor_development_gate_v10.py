import ast, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/"scripts/run_production_core_successor_development_gate_v10.py";LAUNCHER=ROOT/"scripts/launch_production_core_successor_development_gate_v10.sh";MATERIALIZER=ROOT/"scripts/materialize_production_core_v10_development_corpora.py"
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(value);return value
def test_runner_uses_bound_v10_projection_and_policy():
    source=RUNNER.read_text("utf-8");ast.parse(source)
    for witness in ("render_development_messages","assert_phase_equivalence","GENERATION_POLICY","V10 projection mismatch","CONTRACT_SHA256","EDITORIAL_SHA256","maximum_input_tokens","unicodedata.normalize",'"qualification_attempt_consumed":False'):
        assert witness in source
    assert 'row["messages"][:2]' not in source
def test_materializer_is_disjoint_and_reproducible(tmp_path):
    value=module(MATERIALIZER,"dev_materializer_v10"); old=value.sys.argv if hasattr(value,"sys") else None
    import sys
    saved=sys.argv;sys.argv=[str(MATERIALIZER),"--output-dir",str(tmp_path)]
    try: assert value.main()==0
    finally: sys.argv=saved
    manifest=json.loads((tmp_path/"production-core-v10-development-corpus-manifest.json").read_bytes());assert manifest["qualification_rows_used"]==0 and manifest["training_or_shadow_rows_used"]==0
    assert all(item["rows"]==72 for item in manifest["candidates"].values())
def test_launcher_is_offline_read_only_and_binds_contract():
    source=LAUNCHER.read_text("utf-8")
    for witness in ("unshare --mount --net","HF_HUB_OFFLINE=1","mount -o remount,bind,ro","CONTRACT_SHA256","EDITORIAL_SHA256","contract.py","editorial.txt"):
        assert witness in source
def test_repetition_boundary():
    value=module(RUNNER,"dev_runner_v10");phrase="unu doi trei patru cinci sase sapte opt"
    assert value.repeated_ngram_ceiling(" ".join([phrase]*3))==3
    assert value.repeated_ngram_ceiling(" ".join([phrase]*4))==4

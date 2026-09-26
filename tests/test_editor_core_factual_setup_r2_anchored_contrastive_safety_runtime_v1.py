from __future__ import annotations
import importlib.util,json,shutil,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).parents[1]
def load():
    path=ROOT/"scripts/editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1.py"; spec=importlib.util.spec_from_file_location("anchored_runtime",path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
class Tok:
    def __call__(self,text,**_): return {"input_ids":list(range(len(text))),"offset_mapping":[(i,i+1) for i in range(len(text))]}
def test_inventory_mapping_and_orders():
    m=load(); assert len(m.ARMS)*len(m.SEEDS)==12 and set(m.ARMS.values())=={(False,False),(True,False),(False,True),(True,True)}
    result=m.validate_inputs(Tok(),ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-minimal-pairs.jsonl",ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-retention-anchors.jsonl"); assert result["pairs"]==48 and result["retention_anchors"]==24 and len(result["failure_classes"])==6
    assert m.matched_order(161803)!=m.matched_order(271828) and m.matched_order(161803)==m.matched_order(161803)
def test_fixture_isolation_terminal_and_real_fail_closed():
    m=load(); root=ROOT/".anchored-runtime-test-fixture"
    if root.exists(): shutil.rmtree(root)
    root.mkdir()
    try:
        out=root/"slot"; out.mkdir(); receipt=m.fixture_slot(Tok(),ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-minimal-pairs.jsonl",ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-retention-anchors.jsonl",out,"P1_CONTRASTIVE_K1_R2_KL",314159)
        assert receipt["status"]=="PASS_FIXTURE_ONLY" and [x.name for x in out.iterdir()]==["terminal.json"]
        with pytest.raises(ValueError): m.fixture_slot(Tok(),ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-minimal-pairs.jsonl",ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-retention-anchors.jsonl",out,"P1_CONTRASTIVE_K1_R2_KL",314159)
    finally:
        shutil.rmtree(root)
    with pytest.raises(RuntimeError): m.run_slot()
def test_mutations_fail_closed():
    m=load(); source=ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-minimal-pairs.jsonl"; rows=source.read_text(encoding="utf-8").splitlines(); row=json.loads(rows[0]); row["rejected_response"]+="x"; rows[0]=json.dumps(row,ensure_ascii=False,separators=(",",":"))
    root=ROOT/".anchored-runtime-test-mutation"
    if root.exists(): shutil.rmtree(root)
    root.mkdir()
    try:
        bad=root/"bad.jsonl"; bad.write_text("\n".join(rows)+"\n",encoding="utf-8")
        with pytest.raises(ValueError): m.validate_inputs(Tok(),bad,ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-retention-anchors.jsonl")
    finally:
        shutil.rmtree(root)
def test_build_smoke_audit_and_no_authority():
    for script in ("build_editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_boundary_v1.py","smoke_editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1.py","audit_editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1.py"):
        subprocess.run([sys.executable,str(ROOT/"scripts"/script)],check=True,capture_output=True,text=True)
    boundary=json.loads((ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-runtime-boundary.json").read_text(encoding="utf-8")); assert boundary["slots"]==12 and not boundary["model_load_authorized"] and not boundary["training_authorized"] and not boundary["parent_selection_authority"]
    assert boundary["rootfs_sha256"]=="274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4" and boundary["network"]=="DENY_ALL_NEW_NAMESPACE"

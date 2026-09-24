import ast,hashlib,importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];LAUNCHER=ROOT/'scripts/launch_editor_core_factual_setup_corrective_v1_zero_step.py'
def module():
    s=importlib.util.spec_from_file_location('fsc_zero',LAUNCHER);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_no_model_optimizer_route():
    source=LAUNCHER.read_text(encoding='utf-8');imports={a.name for n in ast.walk(ast.parse(source)) if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names};assert not imports&{'torch','transformers','peft','bitsandbytes'};assert 'from_pretrained' not in source and 'optimizer.step' not in source
def test_public_binding():
    m=module();manifest,config=m.validate_public();assert manifest['manifest_identity']==m.MANIFEST;assert config['parent_adapter_sha256']==m.PARENT_ADAPTER
    assert len(m.ZERO_STEP_FILES)==3
def test_substitution_fails(monkeypatch):
    m=module();monkeypatch.setattr(m.subprocess,'check_output',lambda *a,**k:'0'*40+'\n');
    with pytest.raises(ValueError):m.validate_public()
def test_ephemeral_output_excluded(monkeypatch,tmp_path):
    m=module();a=tmp_path/'a';b=tmp_path/'b';a.mkdir();b.mkdir();monkeypatch.setattr(m,'validate_public',lambda:({},{}));monkeypatch.setattr(m,'validate_parent',lambda p:None);monkeypatch.setattr(m,'output_snapshot',lambda p:(1,10 if p==a else 20));ra=m.zero_step(tmp_path,a);rb=m.zero_step(tmp_path,b);assert ra['receipt_identity']==rb['receipt_identity'];assert ra['output_runtime_observation']!=rb['output_runtime_observation']

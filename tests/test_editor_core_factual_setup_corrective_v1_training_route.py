import ast
import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
WORKER=ROOT/'scripts'/'train_editor_core_factual_setup_corrective_v1.py'
ROUTE=ROOT/'scripts'/'run_editor_core_factual_setup_corrective_v1.sh'
SMOKE=ROOT/'scripts'/'smoke_editor_core_factual_setup_corrective_v1_training_route.py'
FIXTURE=ROOT/'tests'/'fixtures'/'editor_core_factual_setup_corrective_v1_training_route'/'config.json'
PUBLISHED_CONFIG=ROOT/'docs'/'artifacts'/'editor-core-factual-setup-corrective-v1-config.json'

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module); return module

def test_fixture_smoke_is_zero_execution():
    result=load(SMOKE,'corrective_smoke').run()
    assert result['status']=='PASS_FIXTURE_ONLY_ZERO_TRAINING'
    assert result['route_bound'] is True and result['route_executed'] is False
    assert result['model_loaded'] is result['optimizer_created'] is result['training_performed'] is False
    assert result['optimizer_steps_executed']==0

def test_fixture_is_byte_exact_published_config_and_plan_is_frozen():
    assert FIXTURE.read_bytes()==PUBLISHED_CONFIG.read_bytes()
    worker=load(WORKER,'corrective_worker')
    plan=worker.validate_config(json.loads(FIXTURE.read_bytes()),worker.EXPECTED_CORPUS,72)
    assert (plan['targeted_rows'],plan['replay_rows'],plan['optimizer_steps'],plan['checkpoint_steps'])==(48,24,9,[9])
    assert plan['gradient_accumulation_steps']==8

@pytest.mark.parametrize('mutation',['identity','parent','voice','authorization','rows','corpus'])
def test_worker_rejects_material_drift(mutation):
    worker=load(WORKER,'corrective_worker_negative'); config=json.loads(FIXTURE.read_bytes()); corpus=worker.EXPECTED_CORPUS; rows=72
    if mutation=='identity': config['config_identity']='0'*64
    elif mutation=='parent': config['parent_adapter_sha256']='0'*64
    elif mutation=='voice': config['voice_or_chief_objective']=True
    elif mutation=='authorization': config['training_authorized']=True
    elif mutation=='rows': rows=71
    else: corpus='0'*64
    with pytest.raises(ValueError): worker.validate_config(config,corpus,rows)

def test_ml_runtime_and_optimizer_are_execution_only():
    tree=ast.parse(WORKER.read_text('utf-8'))
    top={a.name for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names}
    assert not top.intersection({'torch','transformers','peft','bitsandbytes'})
    source=WORKER.read_text('utf-8'); assert source.count('optimizer.step()')==1
    assert 'EXPECTED_ROWS = 72' in source and 'EXPECTED_STEPS = 9' in source

def test_bound_route_has_exact_public_bindings_and_isolation():
    source=ROUTE.read_text('utf-8')
    assert 'EXPECTED_SOURCE_COMMIT=5a5537ff9eb076a289b8fde6b306c38c11085899' in source
    assert 'EXPECTED_SOURCE_TREE=dff0bcc0af869726ec70b528d5b7f96116e4d7ea' in source
    assert 'EXPECTED_MANIFEST_IDENTITY=50b387a0025025f5daac68cd65ab5570a731f9bb0db2a82c023921829e806a88' in source
    assert 'EXPECTED_CONFIG_IDENTITY=2b813d0485a3d3e186e4b5a4c88139af83d8d54fb25e759cee0921ee94da230b' in source
    assert 'EXPECTED_PARENT=c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02' in source
    assert f'EXPECTED_WORKER={hashlib.sha256(WORKER.read_bytes()).hexdigest()}' in source
    zero=ROOT/'scripts'/'launch_editor_core_factual_setup_corrective_v1_zero_step.py'
    assert f'EXPECTED_ZERO_STEP={hashlib.sha256(zero.read_bytes()).hexdigest()}' in source
    assert 'unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork' in source
    assert 'HF_HUB_OFFLINE=1' in source and 'TRANSFORMERS_OFFLINE=1' in source
    assert 'EDITOR_FACTUAL_SETUP_CORRECTIVE_V1_OWNER_AUTHORIZED' in source
    assert '${14}' in source and '${17}' in source
    assert 'git config --global' not in source

def test_holdout_voice_and_historical_candidates_are_not_route_inputs():
    route=ROUTE.read_text('utf-8').lower(); worker=WORKER.read_text('utf-8').lower()
    assert 'holdout-requests' not in route and 'holdout-answer-key' not in route
    assert 'r3' not in route and 'r4' not in route and 'r5' not in route and 'r6' not in route
    assert 'voice_or_chief_objective":false' in worker.replace(' ','')

def test_route_refuses_unarmed_invocation():
    if os.name == 'nt':
        first_lines=ROUTE.read_text('utf-8').splitlines()[:4]
        assert '[[ $# == 8 && ${8:-} == --execute-authorized && $(id -u) == 0 ]] || exit 2' in first_lines
        return
    result=subprocess.run(['bash',str(ROUTE)],capture_output=True)
    assert result.returncode==2

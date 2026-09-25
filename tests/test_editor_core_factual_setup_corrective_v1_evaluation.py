import ast,hashlib,importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
WORKER=ROOT/'scripts/evaluate_editor_core_factual_setup_corrective_v1.py'
ROUTE=ROOT/'scripts/run_editor_core_factual_setup_corrective_v1_evaluation.sh'
REQUESTS=ROOT/'docs/artifacts/editor-core-factual-setup-corrective-v1-holdout-requests.jsonl'
KEY=ROOT/'docs/artifacts/editor-core-factual-setup-corrective-v1-holdout-answer-key.jsonl'
def load():
 spec=importlib.util.spec_from_file_location('corrective_eval',WORKER); m=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(m); return m
def test_fixture_and_no_top_level_ml():
 m=load(); r=m.fixture_smoke(); assert r['model_loaded'] is r['inference'] is r['training'] is False
 tree=ast.parse(WORKER.read_text('utf-8')); top={a.name for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names}; assert not top&{'torch','peft','transformers'}
def test_exact_holdout_request_closure_without_targets():
 m=load(); rows=m.requests(REQUESTS); assert len(rows)==24
 assert all(r['split']=='INDEPENDENT_HOLDOUT' for r in rows)
 assert all(all(x['role']!='assistant' for x in r['messages']) for r in rows)
 assert KEY.name not in ROUTE.read_text('utf-8') and KEY.name not in WORKER.read_text('utf-8')
def test_route_bindings_are_candidate_neutral():
 s=ROUTE.read_text('utf-8'); assert ROUTE.read_bytes().startswith(b'#!/usr/bin/env bash\n')
 assert f'EXPECTED_WORKER={hashlib.sha256(WORKER.read_bytes()).hexdigest()}' in s
 assert 'EXPECTED_REQUESTS=f97815679124cf040d0f7da5c010052532b6d8e08a71ff7ea2071de9035ddf11' in s
 assert 'bbb29efa47db05004a07b8d01c6170d2f0de7f67f0956a4a92e008563ba752a3' in s
 assert 'c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02' in s
 assert 'unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork' in s
@pytest.mark.parametrize('split',['TRAIN','INDEPENDENT_SELECTION_BENCHMARK'])
def test_wrong_partition_rejected(split):
 m=load(); rows=[json.loads(x) for x in REQUESTS.read_bytes().splitlines()]; rows[0]['split']=split
 class MemoryPath:
  def read_bytes(self): return b''.join(m.canonical(x)+b'\n' for x in rows)
 p=MemoryPath()
 with pytest.raises(ValueError,match='split'):m.requests(p)

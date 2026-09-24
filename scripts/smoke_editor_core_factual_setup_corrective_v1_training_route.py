"""Fixture-only smoke for the corrective-v1 worker and route."""
from __future__ import annotations
import ast, hashlib, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WORKER=ROOT/'scripts'/'train_editor_core_factual_setup_corrective_v1.py'
ROUTE=ROOT/'scripts'/'run_editor_core_factual_setup_corrective_v1.sh'
CONFIG=ROOT/'tests'/'fixtures'/'editor_core_factual_setup_corrective_v1_training_route'/'config.json'
def load_worker():
    spec=importlib.util.spec_from_file_location('corrective_v1_worker',WORKER); module=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module); return module
def run():
    tree=ast.parse(WORKER.read_text('utf-8')); top={a.name for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names}
    if top & {'torch','transformers','peft','bitsandbytes'}: raise ValueError('top-level ML import')
    worker=load_worker(); result=worker.fixture_smoke(json.loads(CONFIG.read_bytes())); route=ROUTE.read_text('utf-8')
    if f'EXPECTED_WORKER={hashlib.sha256(WORKER.read_bytes()).hexdigest()}' not in route: raise ValueError('worker binding')
    return {**result,'route_bound':True,'route_executed':False}
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,separators=(',',':')))

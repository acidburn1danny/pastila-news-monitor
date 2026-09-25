"""Bound route. Preflight/fixture modes cannot reach model loading."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-t1s0-replay-protected-v1'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def bindings():
 b=json.loads((ART/f'{P}-runtime-boundary.json').read_text('utf-8')); protocol=json.loads((ART/f'{P}-protocol.json').read_text('utf-8')); pack=json.loads((ART/f'{P}-manifest.json').read_text('utf-8'))
 if b['published_source_commit']!='cc5e1894506372afca0a915a6ed202968c7b7f10' or b['protocol_identity']!=protocol['protocol_identity'] or b['pack_identity']!=pack['pack_identity']: raise ValueError('published binding drift')
 return b
def main():
 p=argparse.ArgumentParser(); p.add_argument('--preflight-only',action='store_true'); p.add_argument('--fixture-only',action='store_true'); a=p.parse_args(); b=bindings()
 if a.preflight_only==a.fixture_only: raise SystemExit('select exactly one safe mode')
 result={'status':'PASS_PREFLIGHT_ONLY' if a.preflight_only else 'PASS_FIXTURE_ONLY','runtime_boundary_identity':b['runtime_boundary_identity'],'slots':6,'model_loaded':False,'optimizer_created':False,'optimizer_steps':0,'training_performed':False,'inference_performed':False}
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()

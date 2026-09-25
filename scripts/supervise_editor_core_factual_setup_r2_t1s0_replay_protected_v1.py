"""Fail-closed six-slot supervisor. Audit mode is the only mode used here."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-t1s0-replay-protected-v1'
def ident(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def validate_authority(a):
 core=dict(a); supplied=core.pop('authority_identity')
 if supplied!=ident(core) or a['slot_count']!=6 or a['program_run_limit']!=1 or a['retry_allowed'] or a['failure_policy']!='STOP_PROGRAM_AT_FIRST_FAILURE': raise ValueError('authority invalid')
 if len({x['slot_id'] for x in a['slots']})!=6 or any(x['optimizer_steps']!=9 or x['run_limit']!=1 or x['retry_allowed'] for x in a['slots']): raise ValueError('slot authority invalid')
 return a
def load_authority(path:Path):
 return validate_authority(json.loads(path.read_text('utf-8')))
def validate_roots(slots,root:Path):
 roots=[]
 for x in slots:
  p=(root/x['slot_id']).resolve();
  if p.parent!=root.resolve() or p.is_symlink() or not p.is_dir() or any(p.iterdir()): raise ValueError('output roots must be distinct new empty directories')
  roots.append(str(p))
 if len(set(roots))!=6: raise ValueError('output root crossover')
def exact_tokenizer_zero_step(model:Path,corpus:Path,annotations:Path,expected:str):
 if hashlib.sha256((model/'tokenizer.json').read_bytes()).hexdigest()!=expected: raise ValueError('exact tokenizer identity')
 from transformers import AutoTokenizer
 from train_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1 import real_chat_token_map
 tok=AutoTokenizer.from_pretrained(model,local_files_only=True,fix_mistral_regex=True); rows={x['example_id']:x for x in map(json.loads,corpus.read_text('utf-8').splitlines())}; anns=list(map(json.loads,annotations.read_text('utf-8').splitlines())); mapped=0
 for ann in anns: mapped+=len(real_chat_token_map(tok,rows[ann['example_id']]['messages'],ann['critical_spans'])['mapped_spans'])
 if len(rows)!=72 or len(anns)!=72 or mapped<=24: raise ValueError('exact tokenizer coverage')
 return mapped
def execute(auth,args):
 validate_roots(auth['slots'],args.output_root); worker=ROOT/'scripts/train_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py'; corpus=ART/'editor-core-factual-setup-corrective-v1-training.jsonl'; protected=ART/f'{P}-protected-signal.jsonl'; control=ART/'editor-core-factual-setup-r2-causal-diagnostic-v1-challenger-signal.jsonl'; development=ART/'editor-core-factual-setup-benchmark-v1-requests.jsonl'
 for item in auth['slots']:
  exact_tokenizer_zero_step(args.model,corpus,protected,auth['tokenizer_sha256'])
  learning=control if item['arm']=='T1_S0_EXISTING_CONTROL' else protected; output=args.output_root/item['slot_id']; env=dict(os.environ,T1S0_REPLAY_PROTECTED_REAL_RUN_AUTHORIZED='1')
  subprocess.run([sys.executable,str(worker),str(args.model),str(args.parent),str(corpus),str(learning),str(protected),str(development),str(output),item['arm'],str(item['seed'])],cwd=ROOT,env=env,check=True)
def main():
 p=argparse.ArgumentParser(); p.add_argument('--authority',type=Path,default=ART/f'{P}-execution-authority.json'); p.add_argument('--audit-only',action='store_true'); p.add_argument('--execute',action='store_true'); p.add_argument('--model',type=Path); p.add_argument('--parent',type=Path); p.add_argument('--output-root',type=Path); a=p.parse_args(); auth=load_authority(a.authority)
 if a.audit_only==a.execute: raise SystemExit('select exactly one mode')
 if a.execute:
  if not all((a.model,a.parent,a.output_root)): raise SystemExit('real execution arguments required')
  execute(auth,a); return
 result={'status':'PASS_AUTHORITY_AUDIT_ONLY','authority_identity':auth['authority_identity'],'slots':6,'optimizer_steps_authorized_per_slot':9,'retry_allowed':False,'execution_performed':False,'model_loaded':False,'optimizer_created':False,'training_performed':False}
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()

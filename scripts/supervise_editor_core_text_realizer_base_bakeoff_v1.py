from __future__ import annotations
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).parents[1]
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p:Path,v:object):
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n');t.replace(p)
def main():
 p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--execute-authorized',action='store_true');a=p.parse_args()
 if not a.execute_authorized or os.environ.get('EDITOR_BASE_BAKEOFF_PROGRAM_AUTHORIZED')!='1':raise SystemExit('authorization required')
 if a.output_root.exists() and (a.output_root.is_symlink() or any(a.output_root.iterdir())):raise ValueError('nonempty program root')
 auth=json.loads((ROOT/'docs/artifacts/editor-core-text-realizer-base-bakeoff-v1-execution-authority.json').read_text())
 for rel,h in auth['files'].items():
  if sha(ROOT/rel)!=h:raise ValueError('source drift '+rel)
 a.output_root.mkdir(parents=True);py=auth['runtime_python'];store=Path('/root/pf9-editor-model-store/sha256');adapter=Path(auth['candidates']['C0_R2_MINISTRAL']['adapter'])
 terminals=[]
 for candidate,cfg in auth['candidates'].items():
  for phase in auth['runs']:
   slot=a.output_root/f'{candidate.lower()}__{phase.lower()}';zero=a.output_root/f'.zero__{candidate.lower()}__{phase.lower()}'
   subprocess.run([py,'-B',str(ROOT/'scripts/preflight_editor_core_text_realizer_base_bakeoff_runtime_v1.py'),'--store',str(store),'--r2-adapter',str(adapter),'--output',str(zero)],check=True)
   env={**os.environ,'EDITOR_BASE_BAKEOFF_SLOT_AUTHORIZED':'1'};cmd=[py,'-B',str(ROOT/'scripts/editor_core_text_realizer_base_bakeoff_runtime_v1.py'),'--candidate',candidate,'--output',str(slot),'--model',cfg['model'],'--tokenizer',cfg.get('tokenizer',cfg['model']),'--artifacts',str(ROOT/'docs/artifacts')]
   if cfg.get('adapter'):cmd += ['--adapter',cfg['adapter']]
   try:subprocess.run(cmd,check=True,env=env)
   except Exception as e:
    atomic(a.output_root/'program-failure.json',{'status':'TERMINAL_FAILURE','slot':f'{candidate}__{phase}','error_type':type(e).__name__,'eligible_evidence':False});raise
   terminals.append(json.loads((slot/'terminal.json').read_text()))
  p1=a.output_root/f'{candidate.lower()}__primary'/'observations.json';p2=a.output_root/f'{candidate.lower()}__byte_exact_replay'/'observations.json'
  if p1.read_bytes()!=p2.read_bytes():
   atomic(a.output_root/'program-failure.json',{'status':'REPLAY_MISMATCH','candidate':candidate,'eligible_evidence':False});raise ValueError('replay mismatch')
 core={'status':'PASS_INFERENCE_CLOSED','authority_identity':auth['authority_identity'],'slots':6,'candidates':3,'rows':288,'replay_byte_exact':True,'semantic_scoring_performed':False,'training_performed':False,'terminals':[x['receipt_identity'] for x in terminals]}
 core['receipt_identity']=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(',',':')).encode()).hexdigest();atomic(a.output_root/'program-terminal.json',core);print(json.dumps(core,sort_keys=True))
if __name__=='__main__':main()

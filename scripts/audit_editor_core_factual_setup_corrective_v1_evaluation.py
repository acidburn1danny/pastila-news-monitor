"""Offline post-closure semantic audit for corrective-v1 blind bundles."""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def sha(b): return hashlib.sha256(b).hexdigest()
J={
'ec-fsc-v1-h-1-01':('FAIL','FAIL','TIE'),'ec-fsc-v1-h-1-02':('FAIL','FAIL','TIE'),'ec-fsc-v1-h-1-03':('FAIL','FAIL','TIE'),'ec-fsc-v1-h-1-04':('FAIL','FAIL','TIE'),
'ec-fsc-v1-h-2-01':('FAIL','FAIL','X'),'ec-fsc-v1-h-2-02':('PASS','PASS','TIE'),'ec-fsc-v1-h-2-03':('PASS','FAIL','X'),'ec-fsc-v1-h-2-04':('FAIL','FAIL','TIE'),
'ec-fsc-v1-h-3-01':('FAIL','FAIL','TIE'),'ec-fsc-v1-h-3-02':('FAIL','FAIL','TIE'),'ec-fsc-v1-h-3-03':('FAIL','FAIL','TIE'),'ec-fsc-v1-h-3-04':('FAIL','FAIL','TIE'),
'ec-fsc-v1-h-4-01':('FAIL','FAIL','TIE'),'ec-fsc-v1-h-4-02':('PASS','PASS','TIE'),'ec-fsc-v1-h-4-03':('PASS','PASS','TIE'),'ec-fsc-v1-h-4-04':('FAIL','PASS','Y'),
'ec-fsc-v1-h-5-01':('PASS','PASS','TIE'),'ec-fsc-v1-h-5-02':('FAIL','FAIL','TIE'),'ec-fsc-v1-h-5-03':('FAIL','FAIL','TIE'),'ec-fsc-v1-h-5-04':('FAIL','FAIL','Y'),
'ec-fsc-v1-h-6-01':('FAIL','FAIL','TIE'),'ec-fsc-v1-h-6-02':('PASS','FAIL','X'),'ec-fsc-v1-h-6-03':('FAIL','FAIL','TIE'),'ec-fsc-v1-h-6-04':('FAIL','FAIL','TIE')}
def rows(p): return [json.loads(x) for x in p.read_bytes().splitlines()]
def audit(xroot,yroot,requests,key):
 xr=json.loads((xroot/'inference-receipt.json').read_bytes()); yr=json.loads((yroot/'inference-receipt.json').read_bytes())
 for root,r in ((xroot,xr),(yroot,yr)):
  core={k:v for k,v in r.items() if k!='receipt_identity'}
  if r['receipt_identity']!=sha(canonical(core)) or r['rows']!=24 or r['terminal_eos']!=24 or r['answer_key_accessed'] or r['optimizer_steps']!=0: raise ValueError('receipt closure')
  if r['responses_sha256']!=sha((root/'responses.jsonl').read_bytes()) or r['observations_sha256']!=sha((root/'observations.jsonl').read_bytes()): raise ValueError('bundle identity')
 req=rows(requests); keys=rows(key); ids={r['example_id'] for r in req}
 if ids!={r['example_id'] for r in keys} or ids!=set(J): raise ValueError('case closure')
 classes={r['example_id']:r['failure_class'] for r in keys}; per=defaultdict(lambda:{'X':0,'Y':0,'cases':0})
 for case,(x,y,_w) in J.items(): per[classes[case]]['cases']+=1; per[classes[case]]['X']+=x=='PASS'; per[classes[case]]['Y']+=y=='PASS'
 core={'schema':'editor-factual-setup-corrective-v1-semantic-result','schema_version':1,'status':'PASS_AUDIT_RETAIN_R2','requests_sha256':sha(requests.read_bytes()),'answer_key_sha256':sha(key.read_bytes()),'bundle_x_receipt':xr['receipt_identity'],'bundle_y_receipt':yr['receipt_identity'],'mapping':{'X':'CORRECTIVE_V1','Y':'R2_STEP_9'},'passes':{'X':sum(x=='PASS' for x,y,w in J.values()),'Y':sum(y=='PASS' for x,y,w in J.values())},'winners':dict(Counter(w for x,y,w in J.values())),'per_failure_class':dict(sorted(per.items())),'case_verdicts':{k:{'X':v[0],'Y':v[1],'winner':v[2]} for k,v in sorted(J.items())},'semantic_conclusion':'INSUFFICIENT_SUPERIORITY_RETAIN_R2','development_parent':'R2_STEP_9','promotion':False,'release':False,'training_performed':False,'historical_holdouts_accessed':False}
 return {**core,'result_identity':sha(canonical(core))}
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('x',type=Path);p.add_argument('y',type=Path);p.add_argument('requests',type=Path);p.add_argument('key',type=Path);p.add_argument('--output',type=Path);a=p.parse_args(); r=audit(a.x,a.y,a.requests,a.key); raw=json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+'\n'; a.output.write_text(raw,encoding='utf-8') if a.output else print(raw,end='')

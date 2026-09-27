"""Score machine gates and prepare sealed, case-randomized human review packets."""
from __future__ import annotations
import argparse, hashlib, json, os, secrets
from collections import Counter
from pathlib import Path

CANDS=("C0_R2_MINISTRAL","C1_QWEN3_8B","C2_QWEN25_7B")
# ASCII escaping makes commitments byte-stable across the Windows 3.14 and
# WSL runtime JSON encoders used by preparation and the reviewer application.
def canonical(v):return (json.dumps(v,ensure_ascii=True,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def atomic(p,v):
 t=p.with_suffix(p.suffix+'.tmp');t.write_bytes(canonical(v));t.replace(p)
def rows(root,c):return json.loads((root/f'{c.lower()}__primary'/'observations.json').read_text())
def main():
 p=argparse.ArgumentParser();p.add_argument('--program-root',type=Path,required=True);p.add_argument('--artifact-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);p.add_argument('--sealed-root',type=Path,required=True);a=p.parse_args()
 if a.public_root.exists() or a.sealed_root.exists():raise ValueError('no overwrite review roots')
 terminal=json.loads((a.program_root/'program-terminal.json').read_text())
 if terminal['status']!='PASS_INFERENCE_CLOSED' or not terminal['replay_byte_exact']:raise ValueError('inference closure')
 ledgers={x['case_id']:x for x in (json.loads(z) for z in (a.artifact_root/'editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl').read_text().splitlines() if z)}
 if len(ledgers)!=48:raise ValueError('ledger inventory')
 data={c:rows(a.program_root,c) for c in CANDS}
 if any(len(v)!=48 for v in data.values()):raise ValueError('row inventory')
 machine={}
 for c,v in data.items():
  runtime=json.loads((a.program_root/f'{c.lower()}__primary'/'runtime.json').read_text())
  machine[c]={'rows':48,'structural_valid':sum(x['structural_valid'] for x in v),'fallback':sum(x['route']=='EXTRACTIVE_FALLBACK' for x in v),'fallback_rate':sum(x['route']=='EXTRACTIVE_FALLBACK' for x in v)/48,'routes':dict(Counter(x['route'] for x in v)),'runtime_seconds':runtime['elapsed_seconds'],'seconds_per_case':runtime['elapsed_seconds']/48,'replay_byte_exact':True}
 secret=secrets.token_bytes(32);mapping={};packets=[]
 for case_id in sorted(ledgers):
  labels=['A','B','C']; order=sorted(CANDS,key=lambda c:hashlib.sha256(secret+case_id.encode()+c.encode()).digest())
  mapping[case_id]=dict(zip(labels,order)); ledger=ledgers[case_id]
  packets.append({'case_id':case_id,'partition':ledger['partition'],'failure_class':ledger['failure_class'],'request':ledger['request'],'source_authority':[{'atom_id':x['atom_id'],'quote':x['quote'],'selection':x['selection']} for x in ledger['atoms'] if x['selection']!='EXCLUDED'],'outputs':{label:next(x['text'] for x in data[c] if x['case_id']==case_id) for label,c in mapping[case_id].items()}})
 a.public_root.mkdir(parents=True);a.sealed_root.mkdir(parents=True);os.chmod(a.sealed_root,0o700)
 core={'schema':'editor-text-realizer-base-bakeoff-blind-pack','schema_version':1,'program_receipt_identity':terminal['receipt_identity'],'cases':packets,'rubric':{'factual_safety':['PASS','FAIL','UNSURE'],'factual_sufficiency':['PASS','FAIL','UNSURE'],'functional_romanian':[1,2,3,4,5],'naturalness':[1,2,3,4,5],'usable_realization':[1,2,3,4,5],'winner':['A','B','C','TIE']}}
 core['pack_identity']=sha(canonical(core));atomic(a.public_root/'pack.json',core)
 m={'schema':'editor-text-realizer-base-bakeoff-sealed-map','schema_version':1,'pack_identity':core['pack_identity'],'mapping':mapping};m['mapping_identity']=sha(canonical(m));atomic(a.sealed_root/'mapping.json',m);os.chmod(a.sealed_root/'mapping.json',0o600)
 result={'schema':'editor-text-realizer-base-bakeoff-machine-result','schema_version':1,'program_receipt_identity':terminal['receipt_identity'],'machine':machine,'human_blind_status':'PENDING_48','semantic_decision':'PENDING_HUMAN_BLIND','parent_selection_authority':False};result['result_identity']=sha(canonical(result));atomic(a.public_root/'machine-result.json',result)
 print(json.dumps({'status':'READY_FOR_HUMAN_BLIND_REVIEW','pack_identity':core['pack_identity'],'mapping_identity':m['mapping_identity'],'machine_result_identity':result['result_identity'],'cases':48,'machine':machine},sort_keys=True))
if __name__=='__main__':main()

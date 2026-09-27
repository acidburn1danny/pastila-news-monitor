"""Audit immutable blind receipts, unseal the per-case map, and apply frozen rules."""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
def canonical(v,ascii_=True):return (json.dumps(v,ensure_ascii=ascii_,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def stable(v):
 if isinstance(v,float):return format(v,'.12f').rstrip('0').rstrip('.')
 if isinstance(v,dict):return {k:stable(x) for k,x in v.items()}
 if isinstance(v,list):return [stable(x) for x in v]
 return v
def main():
 p=argparse.ArgumentParser();p.add_argument('--public-root',type=Path,required=True);p.add_argument('--sealed-map',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
 if a.output.exists() or a.receipt.exists():raise ValueError('no overwrite')
 pack=json.loads((a.public_root/'pack.json').read_text());core={k:v for k,v in pack.items() if k!='pack_identity'}
 if pack['pack_identity']!=sha(canonical(core)):raise ValueError('pack identity')
 mapping=json.loads(a.sealed_map.read_text());mc={k:v for k,v in mapping.items() if k!='mapping_identity'}
 if mapping['mapping_identity']!=sha(canonical(mc)) or mapping['pack_identity']!=pack['pack_identity']:raise ValueError('mapping identity')
 scores=[]
 for case in pack['cases']:
  r=json.loads((a.public_root/'scores'/f'{case["case_id"]}.json').read_text());rid=r.pop('receipt_identity')
  if rid!=sha(canonical(r,False)) or r['pack_identity']!=pack['pack_identity'] or r['case_id']!=case['case_id']:raise ValueError('receipt '+case['case_id'])
  r['receipt_identity']=rid;scores.append(r)
 closure=json.loads((a.public_root/'scores'/'closure.json').read_text());cid=closure.pop('closure_identity')
 if cid!=sha(canonical(closure)) or closure['pack_identity']!=pack['pack_identity'] or closure['receipts']!=[x['receipt_identity'] for x in scores]:raise ValueError('closure')
 closure['closure_identity']=cid
 machine=json.loads((a.public_root/'machine-result.json').read_text());mi=machine.pop('result_identity')
 if mi!=sha(canonical(machine)) or machine['program_receipt_identity']!=pack['program_receipt_identity']:raise ValueError('machine result')
 machine['result_identity']=mi
 agg={c:{'factual_safety':Counter(),'factual_sufficiency':Counter(),'functional_romanian':[],'naturalness':[],'usable_realization':[],'wins':0} for c in machine['machine']};ties=0;label_distribution=defaultdict(Counter)
 per_case=[]
 for r in scores:
  m=mapping['mapping'][r['case_id']]
  for label,candidate in m.items():
   label_distribution[candidate][label]+=1;s=r['scores'][label]
   agg[candidate]['factual_safety'][s['factual_safety']]+=1;agg[candidate]['factual_sufficiency'][s['factual_sufficiency']]+=1
   for k in ('functional_romanian','naturalness','usable_realization'):agg[candidate][k].append(s[k])
  winner=None if r['winner']=='TIE' else m[r['winner']]
  if winner is None:ties+=1
  else:agg[winner]['wins']+=1
  per_case.append({'case_id':r['case_id'],'mapping':m,'winner':winner or 'TIE'})
 summary={}
 for c,x in agg.items():
  mm=machine['machine'][c];summary[c]={'factual_safety':dict(x['factual_safety']),'factual_sufficiency':dict(x['factual_sufficiency']),'mean_functional_romanian':sum(x['functional_romanian'])/48,'mean_naturalness':sum(x['naturalness'])/48,'mean_usable_realization':sum(x['usable_realization'])/48,'wins':x['wins'],'ties_total':ties,'fallback_rate':mm['fallback_rate'],'seconds_per_case':mm['seconds_per_case'],'structural_valid':mm['structural_valid'],'replay_byte_exact':mm['replay_byte_exact'],'label_distribution':dict(label_distribution[c])}
 r2=summary['C0_R2_MINISTRAL'];decisions={}
 for c,s in summary.items():
  if c=='C0_R2_MINISTRAL':decisions[c]={'decision':'BASELINE_RETAINED','reasons':[]};continue
  stop=[];rev=[];cont=[]
  if s['factual_safety'].get('FAIL',0):stop.append('ANY_ACCEPTED_FACTUAL_OR_EPISTEMIC_DRIFT')
  if s['factual_safety'].get('UNSURE',0):rev.append('HUMAN_FACTUAL_SAFETY_UNSURE')
  if s['fallback_rate']>0.25:rev.append('FALLBACK_RATE_ABOVE_25_PERCENT')
  if s['mean_functional_romanian']<=r2['mean_functional_romanian']:rev.append('NO_BLIND_FUNCTIONAL_ROMANIAN_GAIN_OVER_R2')
  if not s['replay_byte_exact']:rev.append('CHALLENGER_GAIN_NOT_BYTE_REPRODUCIBLE')
  if not stop and not rev:cont=['ZERO_ACCEPTED_FACTUAL_OR_EPISTEMIC_DRIFT','FALLBACK_RATE_AT_MOST_25_PERCENT','BLIND_FUNCTIONAL_ROMANIAN_GAIN_OVER_R2','BYTE_REPRODUCIBLE','RTX5080_16GB_RUNTIME_PASS']
  decisions[c]={'decision':'STOP' if stop else 'REVISE' if rev else 'CONTINUE','stop_reasons':stop,'revise_reasons':rev,'continue_conditions':cont}
 core={'schema':'editor-text-realizer-base-bakeoff-frozen-result','schema_version':3,'program_receipt_identity':pack['program_receipt_identity'],'pack_identity':pack['pack_identity'],'blind_closure_identity':cid,'mapping_identity':mapping['mapping_identity'],'machine_result_identity':mi,'machine_result_file_sha256':sha((a.public_root/'machine-result.json').read_bytes()),'mapping_scope':'PER_CASE_RANDOMIZED_NO_GLOBAL_LABEL_MAPPING','summary':stable(summary),'ties':ties,'decisions':decisions,'per_case_mapping_and_winner':per_case,'development_parent':'R2_STEP_9','parent_changed':False,'parent_selection_authority':False,'inference_performed':False,'training_performed':False,'historical_holdouts_accessed':False}
 a.output.write_bytes(canonical(core));result_identity=sha(a.output.read_bytes());receipt={'status':'PASS_FROZEN_RESULT','result_file':a.output.name,'result_identity':result_identity,'blind_closure_identity':cid,'mapping_identity':mapping['mapping_identity']};a.receipt.write_bytes(canonical(receipt));print(json.dumps({'status':'PASS_FROZEN_RESULT','result_identity':result_identity,'closure_identity':cid,'ties':ties,'summary':summary,'decisions':decisions},sort_keys=True))
if __name__=='__main__':main()

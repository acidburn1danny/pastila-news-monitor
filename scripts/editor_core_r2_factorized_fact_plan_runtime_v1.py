"""Runtime primitives for the factorized diagnostic; fixture execution only."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path

INTERVENTIONS=('I0_ONE_PASS_R2','I1_ORACLE_PLAN_SCORE','I2_ORACLE_PLAN_TO_R2_SETUP','I3_R2_PLAN_TO_R2_SETUP')
SEEDS=(161803,271828,314159)
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def flat(root):
 rows=[]
 for p in sorted(root.iterdir(),key=lambda x:x.name.encode()):
  if p.is_symlink() or not p.is_file(): raise ValueError('adapter closure')
  rows.append(p.name.encode()+b'\0'+p.stat().st_size.to_bytes(8,'big')+bytes.fromhex(sha(p.read_bytes())))
 return sha(b''.join(rows))
def validate_plan(plan,case):
 if plan['case_id']!=case['case_id'] or plan['request_identity']!=case['request_identity']: raise ValueError('plan request binding')
 spans={x['span_id']:x['text'] for x in plan['authority_inventory']}
 if not spans or any(any(s not in spans for s in f['support_span_ids']) for f in plan['selected_facts']): raise ValueError('fact support')
 if any(x['support_span_id'] not in spans or x['surface'] not in spans[x['support_span_id']] for x in plan['actors_entities']+plan['numbers']): raise ValueError('surface support')
 expected=[n for text in spans.values() for n in re.findall(r'(?<!\w)\d+(?:[.,]\d+)?(?!\w)',text)]
 if [x['surface'] for x in plan['numbers']]!=expected: raise ValueError('number inventory')
 if plan['setup_constraints']!={'factual_only':True,'maximum_sentences':3,'minimum_sentences':2}: raise ValueError('setup contract')
 return {'plan_identity':plan['plan_identity'],'facts':len(plan['selected_facts']),'numbers':len(plan['numbers']),'status':'PASS_PLAN_VALID'}
def execute_fixture(intervention,case,oracle):
 if intervention not in INTERVENTIONS: raise ValueError('intervention')
 plan=None; receipts=[]
 if intervention in ('I1_ORACLE_PLAN_SCORE','I2_ORACLE_PLAN_TO_R2_SETUP'): plan=oracle; receipts.append({'phase':'ORACLE_PLAN_INTERVENTION',**validate_plan(plan,case)})
 elif intervention=='I3_R2_PLAN_TO_R2_SETUP':
  plan={**oracle,'generation_role':'FIXTURE_MODEL_GENERATED_PLAN'}; receipts.append({'phase':'PLAN_GENERATION','model_loaded':False}); receipts.append({'phase':'PLAN_VALIDATION',**validate_plan(plan,case)})
 if intervention in ('I0_ONE_PASS_R2','I2_ORACLE_PLAN_TO_R2_SETUP','I3_R2_PLAN_TO_R2_SETUP'):
  receipts.append({'phase':'SETUP_REALIZATION','mode':'ONE_PASS_CONTROL' if intervention=='I0_ONE_PASS_R2' else 'PLAN_CONDITIONED','text':oracle['oracle_setup_target'],'model_loaded':False})
 return receipts

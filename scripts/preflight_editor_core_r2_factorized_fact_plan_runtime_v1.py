"""Executable zero-step for all factorized diagnostic slots."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from editor_core_r2_factorized_fact_plan_runtime_v1 import INTERVENTIONS,SEEDS,canonical,flat,sha,validate_plan
SOURCE='11c39a158e3edd98418ebbc15e472a1c2388f43a'; TREE='f3e0e6e344a79611ab1402cf4152974b553c53ae'; PACK='57da2b8a1e052ddb7d80fd19085fc8930c95c93d36836e6c2f087cab0ce64b6a'; TOKENIZER='d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135'; PARENT='c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02'
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
def main():
 a=argparse.ArgumentParser(); a.add_argument('--artifact-root',type=Path,required=True); a.add_argument('--tokenizer-dir',type=Path,required=True); a.add_argument('--parent-adapter',type=Path,required=True); a.add_argument('--output',type=Path,required=True); z=a.parse_args()
 if z.output.exists() and (z.output.is_symlink() or any(z.output.iterdir())): raise ValueError('output root')
 z.output.mkdir(parents=True,exist_ok=True)
 if subprocess.check_output(['git','show','-s','--format=%T',SOURCE],text=True).strip()!=TREE: raise ValueError('source tree')
 manifest=json.loads((z.artifact_root/'editor-core-r2-factorized-fact-plan-diagnostic-v1-manifest.json').read_text(encoding='utf-8'))
 if manifest['pack_identity']!=PACK or manifest['files']!={n:sha((z.artifact_root/n).read_bytes()) for n in manifest['files']}: raise ValueError('pack closure')
 if sha((z.tokenizer_dir/'tokenizer.json').read_bytes())!=TOKENIZER or flat(z.parent_adapter)!=PARENT: raise ValueError('runtime identity')
 cases={x['case_id']:x for x in rows(z.artifact_root/'editor-core-r2-factorized-fact-plan-diagnostic-v1-cases.jsonl')}; plans={x['case_id']:x for x in rows(z.artifact_root/'editor-core-r2-factorized-fact-plan-diagnostic-v1-oracle-plans.jsonl')}
 if len(cases)!=48 or set(cases)!=set(plans): raise ValueError('case inventory')
 for cid in cases: validate_plan(plans[cid],cases[cid])
 slots=[]
 for intervention in INTERVENTIONS:
  for seed in SEEDS: slots.append({'slot_id':f'{intervention}__seed_{seed}','intervention':intervention,'seed':seed,'cases_validated':48,'output_root_required_empty':True})
 core={'schema':'editor-r2-factorized-runtime-zero-step','schema_version':1,'status':'PASS_12_ZERO_STEP','source_commit':SOURCE,'source_tree':TREE,'pack_identity':PACK,'tokenizer_sha256':TOKENIZER,'parent':'R2_STEP_9','parent_adapter_identity':PARENT,'slots':slots,'model_loaded':False,'optimizer_created':False,'training_performed':False,'historical_holdouts_read':False,'parent_selection_authority':False}
 receipt={**core,'receipt_identity':sha(canonical(core))}; tmp=z.output/'zero-step.json.tmp'; tmp.write_bytes(json.dumps(receipt,sort_keys=True,indent=2).encode()+b'\n'); tmp.replace(z.output/'zero-step.json'); print(json.dumps({'status':core['status'],'slots':len(slots),'receipt_identity':receipt['receipt_identity']},sort_keys=True))
if __name__=='__main__': main()

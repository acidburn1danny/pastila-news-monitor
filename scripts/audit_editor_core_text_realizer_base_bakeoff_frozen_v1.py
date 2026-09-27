from __future__ import annotations
import hashlib,json
from pathlib import Path
R=Path(__file__).parents[1];A=R/'docs/artifacts'
result_path=A/'editor-core-text-realizer-base-bakeoff-frozen-result-v1.json'
receipt=json.loads((A/'editor-core-text-realizer-base-bakeoff-frozen-result-v1-receipt.json').read_text())
closure=json.loads((A/'editor-core-text-realizer-base-bakeoff-blind-closure-v1.json').read_text())
result=json.loads(result_path.read_text())
assert hashlib.sha256(result_path.read_bytes()).hexdigest()==receipt['result_identity']=='c276fa21189afc169ec9e3ae5d9847d47cb20148cdcc7052f1893d19fa4b4927'
assert closure['closure_identity']==receipt['blind_closure_identity']=='169984a580322f21e1ad809e747274c9a35dd7ed5ea1b5a4da6397f40640e1d6'
assert closure['status']=='PASS_48_BLIND_LOCKED' and len(closure['receipts'])==48
assert result['decisions']['C1_QWEN3_8B']['decision']=='REVISE'
assert result['decisions']['C2_QWEN25_7B']['decision']=='REVISE'
assert result['development_parent']=='R2_STEP_9' and not result['parent_changed'] and not result['parent_selection_authority']
assert not result['inference_performed'] and not result['training_performed'] and not result['historical_holdouts_accessed']
assert result['mapping_scope']=='PER_CASE_RANDOMIZED_NO_GLOBAL_LABEL_MAPPING' and len(result['per_case_mapping_and_winner'])==48
print(json.dumps({'status':'PASS_FROZEN_CLOSURE','checks':8,'result_identity':receipt['result_identity'],'blind_closure_identity':closure['closure_identity']},sort_keys=True))

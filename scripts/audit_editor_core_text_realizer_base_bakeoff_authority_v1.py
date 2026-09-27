import hashlib,json
from pathlib import Path
R=Path(__file__).parents[1];A=json.loads((R/'docs/artifacts/editor-core-text-realizer-base-bakeoff-v1-execution-authority.json').read_text())
assert A['slots']==6 and A['runs']==['PRIMARY','BYTE_EXACT_REPLAY'] and not A['retry_authorized']
assert not A['semantic_scoring_authorized'] and not A['parent_selection_authority'] and not A['training_authorized']
assert all(hashlib.sha256((R/p).read_bytes()).hexdigest()==h for p,h in A['files'].items())
print(json.dumps({'status':'PASS_ADVERSARIAL','checks':7,'authority_identity':A['authority_identity']},sort_keys=True))

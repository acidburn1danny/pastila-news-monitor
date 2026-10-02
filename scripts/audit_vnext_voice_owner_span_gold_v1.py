import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_vnext_voice_owner_span_gold_v1 import build,canon
def audit(root):
 d=build(root); tr=[json.loads(x) for x in (root/'docs/artifacts/vnext-voice-owner-span-gold-train-v1.jsonl').read_text().splitlines()]; va=[json.loads(x) for x in (root/'docs/artifacts/vnext-voice-owner-span-gold-validation-v1.jsonl').read_text().splitlines()]
 def exact(r,kind):
  raw=(root/r['source_path']).read_bytes(); s=r[kind]; chunk=b''.join(raw.splitlines(keepends=True)[s['line_start']-1:s['line_end']]); return hashlib.sha256(chunk).hexdigest()==s['sha256'] and chunk.decode('utf-8-sig')==s['text']
 annotated={m for r in tr+va for values in r['mechanisms'].values() for m in values}; curriculum=set(d['mechanism_coverage']['covered'])|set(d['mechanism_coverage']['positive_gaps'])
 checks={'records_16':len(tr)==12 and len(va)==4,'exact_spans':all(exact(r,k) for r in tr+va for k in ['factual_setup','gold_commentary']),'distinct_spans':all(r['factual_setup']['line_end']<r['gold_commentary']['line_start'] for r in tr+va),'mechanisms_in_frozen_curriculum':annotated<=curriculum,'families_disjoint':not ({r['episode'] for r in tr}&{r['episode'] for r in va}),'holdout_unread':all(f'episode-{n}.txt' not in d['read_source_paths'] for n in [31,32,33,34]),'no_rewrites':d['factual_safety']['rewrites']==0,'not_training_ready':d['training_readiness']['qwen3_lora']=='NOT_READY','protected_state':not d['active_product_modified'] and not d['canonical_rollback_modified']}
 a={'schema':'vnext-voice-owner-span-gold-audit','schema_version':1,'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'result_identity':d['result_identity']}; a['audit_identity']=hashlib.sha256(canon(a)).hexdigest(); (root/'docs/artifacts/vnext-voice-owner-span-gold-v1-audit.json').write_text(json.dumps(a,indent=2,sort_keys=True)+'\n'); assert a['status']=='PASS'; return a
if __name__=='__main__': audit(Path(__file__).resolve().parents[1])

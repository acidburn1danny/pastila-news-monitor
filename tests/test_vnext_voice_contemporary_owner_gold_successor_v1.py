import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs/artifacts'
def load(n): return json.loads((ART/n).read_text())
def identity(x,f):
 b={k:v for k,v in x.items() if k!=f}; return hashlib.sha256(json.dumps(b,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def test_successor_is_fail_closed_without_invented_gold():
 s=load('vnext-voice-contemporary-owner-gold-dataset-successor-v1.json')
 assert s['dataset']['new_owner_gold_admitted']==0
 assert s['second_experiment_readiness']['status']=='FAIL_CLOSED_NOT_READY'
 assert s['successor_identity']==identity(s,'successor_identity')
def test_predecessor_and_baseline_are_frozen():
 s=load('vnext-voice-contemporary-owner-gold-dataset-successor-v1.json')
 assert s['dataset_predecessor_identity']=='f52b5cacd39c0b8fb90a5b20f30a0c4a1d3400a1ee356c1876e5b6d20cbaf6f7'
 assert s['baseline_experiment']['frozen'] is True
 assert len(s['predecessor_files'])==4
def test_holdout_and_owner_authority_close():
 s=load('vnext-voice-contemporary-owner-gold-dataset-successor-v1.json'); b=load('vnext-voice-contemporary-owner-gold-backlog-v1.json')
 assert s['admission_rules']['holdout_access'] is False
 assert s['admission_rules']['model_generated_text_is_owner_gold'] is False
 assert b['holdout_access']=='DENIED' and b['quota_fill'] is False
def test_audit_protects_runtime():
 a=load('vnext-voice-contemporary-owner-gold-dataset-successor-v1-audit.json')
 assert a['status']=='PASS_0_INTEGRITY_BLOCKERS_DATA_NOT_ADMITTED'
 assert a['active_product_modified'] is False and a['canonical_rollback_modified'] is False
 assert a['audit_identity']==identity(a,'audit_identity')

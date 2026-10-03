import hashlib,json,sys
from pathlib import Path
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def verify(path,field):
 x=json.loads(path.read_text()); claimed=x.pop(field); assert hashlib.sha256(canon(x)).hexdigest()==claimed; return {**x,field:claimed}
r=Path(sys.argv[1]); a=r/'docs/artifacts'
s=verify(a/'vnext-voice-contemporary-owner-gold-dataset-successor-v1.json','successor_identity')
b=verify(a/'vnext-voice-contemporary-owner-gold-backlog-v1.json','backlog_identity')
u=verify(a/'vnext-voice-contemporary-owner-gold-dataset-successor-v1-audit.json','audit_identity')
assert s['backlog_identity']==b['backlog_identity'] and u['successor_identity']==s['successor_identity']
assert s['dataset']['new_owner_gold_admitted']==0 and s['second_experiment_readiness']['status']=='FAIL_CLOSED_NOT_READY'
assert s['admission_rules']['quota_fill'] is False and s['admission_rules']['holdout_access'] is False
assert u['holdout_exposure']==0 and u['active_product_modified'] is False and u['canonical_rollback_modified'] is False
print(json.dumps({'status':'PASS','successor_identity':s['successor_identity'],'backlog_identity':b['backlog_identity'],'audit_identity':u['audit_identity']},sort_keys=True))

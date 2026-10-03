from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()
def ident(v,f):
 x=dict(v); actual=x.pop(f); assert hashlib.sha256(canon(x)).hexdigest()==actual; return actual
def rows(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def main(repo):
 a=repo/"docs/artifacts"; d=json.loads((a/"vnext-voice-owner-gold-pack03-v1-dataset-successor.json").read_text(encoding="utf-8")); f=json.loads((a/"vnext-voice-owner-gold-pack03-v1-corpus-freeze.json").read_text(encoding="utf-8")); b=json.loads((a/"vnext-voice-owner-gold-pack03-v1-backlog.json").read_text(encoding="utf-8")); au=json.loads((a/"vnext-voice-owner-gold-pack03-v1-audit.json").read_text(encoding="utf-8"))
 ids=[ident(d,"dataset_successor_identity"),ident(f,"corpus_freeze_identity"),ident(b,"backlog_identity"),ident(au,"audit_identity")]; assert d["dataset_successor_identity"]==f["dataset_successor_identity"]==b["dataset_successor_identity"]==au["dataset_successor_identity"]
 adm=rows(repo/d["files"]["admission"]["path"]); rec=rows(repo/d["files"]["admitted-records"]["path"]); train=rows(repo/d["files"]["train-successor"]["path"]); val=rows(repo/d["files"]["validation-successor"]["path"])
 assert len(adm)==9 and len(rec)==9 and (len(train),len(val))==(39,15); assert [x["pack_record"] for x in adm if x["admission"].startswith("REJECTED")]==[]; assert all(not x["factual_commentary_taxonomy"]["unsupported_fact_admitted"] for x in rec)
 assert not ({x["family_identity"] for x in train}&{x["family_identity"] for x in val}); assert len({x["gold_commentary"]["sha256"] for x in train+val})==len(train)+len(val)
 assert d["partition"]["holdout_exposure"]==d["partition"]["qwen3_bakeoff_exposure"]==0; assert d["second_experiment_readiness"]["status"]=="READY_FOR_SECOND_EXPERIMENTAL_NON_PROMOTABLE_QWEN3_LORA"; assert f["status"].startswith("FROZEN_READY"); assert not d["training_performed"] and not d["weights_modified"] and not d["holdout_accessed"]; assert au["status"]=="PASS_0_INTEGRITY_BLOCKERS" and au["legacy_dependency_count"]==0
 r5=next(x for x in rec if x["pack_record"]==5); assert r5["training_eligible"] and d["factual_safety"]["record05_owner_semantic_clarification"]=="BOUND_TO_AGENCY_AUTHORITY_SENSE_ONLY"
 print(json.dumps({"status":"PASS","dataset":ids[0],"freeze":ids[1],"backlog":ids[2],"audit":ids[3],"train":39,"validation":15,"holdout_exposure":0},sort_keys=True))
if __name__=="__main__": main(Path(sys.argv[1]).resolve())

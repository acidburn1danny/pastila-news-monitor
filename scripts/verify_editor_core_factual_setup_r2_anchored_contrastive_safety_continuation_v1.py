from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).parents[1]; AUTH=ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-continuation-v1-authority.json"
def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def verify(arm=None,seed=None,published=False):
 d=json.loads(AUTH.read_text()); ident=d.pop("authority_identity"); assert ident==hashlib.sha256(canonical(d)).hexdigest()
 assert d["predecessor_pass_slots"]==8 and d["failed_slot_optimizer_steps"]==0 and len(d["slots"])==4
 for k,p in d["source_files"].items():
  raw=(ROOT/p).read_bytes(); assert hashlib.sha256(raw).hexdigest()==d["source_sha256"][k]; assert subprocess.check_output(["git","show",f'{d["source_commit"]}:{p}'],cwd=ROOT)==raw
 if published: assert subprocess.call(["git","merge-base","--is-ancestor",d["source_commit"],"@{upstream}"],cwd=ROOT)==0
 if arm is None:return {**d,"authority_identity":ident}
 found=[x for x in d["slots"] if x["arm"]==arm and x["seed"]==seed]; assert len(found)==1; return {"authority_identity":ident,"slot":found[0]}
if __name__=="__main__": print(json.dumps({"status":"PASS",**verify()},sort_keys=True))

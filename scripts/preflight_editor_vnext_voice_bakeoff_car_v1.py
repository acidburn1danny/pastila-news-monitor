"""No-model-load preflight for the CAR successor executor."""
import argparse,hashlib,json
from pathlib import Path
try: from scripts.build_editor_vnext_voice_bakeoff_car_authority_v1 import audit
except ModuleNotFoundError: from build_editor_vnext_voice_bakeoff_car_authority_v1 import audit
def sha(p):
 h=hashlib.sha256();
 with p.open("rb") as f:
  while b:=f.read(8*1024*1024): h.update(b)
 return h.hexdigest()
def preflight(repo,product,output):
 r=audit(repo)
 if output.exists(): raise ValueError("output root must be absent")
 lock=json.loads((product/"components/voice-candidates-v1/dependency-lock.json").read_text()); r2=json.loads((product/"components/r2-reference-v1/dependency-lock.json").read_text())
 for c in lock["candidates"]:
  root=product/"components/voice-candidates-v1"/c["layout"]
  for x in c["files"]:
   p=root/x["path"]; assert p.is_file() and p.stat().st_size==x["size"]
 for x in r2["files"]:
  p=product/"components/r2-reference-v1"/x["path"]; assert p.is_file() and p.stat().st_size==x["size"]
 r.update({"status":"PASS_CAR_216_ZERO_STEP","output_root":"ABSENT","model_loaded":False,"inference":False,"outputs":0}); return r
if __name__=="__main__":
 p=argparse.ArgumentParser(); p.add_argument("--repo",type=Path,required=True); p.add_argument("--product-root",type=Path,required=True); p.add_argument("--output-root",type=Path,required=True); a=p.parse_args(); print(json.dumps(preflight(a.repo,a.product_root,a.output_root),sort_keys=True))

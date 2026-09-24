"""Verify the published, bounded development-inference authority."""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def flat(root: Path) -> str:
    rows=[]
    for p in sorted(root.iterdir(),key=lambda x:x.name.encode()):
        if p.is_symlink() or not p.is_file(): raise ValueError("flat manifest")
        rows.append(p.name.encode()+b"\0"+p.stat().st_size.to_bytes(8,"big")+hashlib.sha256(p.read_bytes()).digest())
    return hashlib.sha256(b"".join(rows)).hexdigest()
def git(repo: Path,*args:str)->str:
    return subprocess.check_output(["git","-c",f"safe.directory={repo}","-C",str(repo),*args],text=True).strip()
def verify(authority:Path,candidate:str,model:Path,adapter:Path,requests:Path,worker:Path,route:Path,repo:Path)->dict:
    value=json.loads(authority.read_bytes()); core={k:v for k,v in value.items() if k!="authority_identity"}
    identity=hashlib.sha256(json.dumps(core,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    if value.get("authority_identity")!=identity or value.get("schema")!="editor-core-bridge-causal-development-inference-authority": raise ValueError("authority identity")
    if git(repo,"rev-parse","HEAD")!=git(repo,"rev-parse","origin/successor/core-v2-v12-runner-binding-remediation"): raise ValueError("publication closure")
    if subprocess.run(["git","-c",f"safe.directory={repo}","-C",str(repo),"merge-base","--is-ancestor",value["implementation_commit"],"HEAD"]).returncode: raise ValueError("implementation ancestry")
    slots={row["candidate"]:row for row in value["candidates"]}
    if set(slots)!={"r2","a1-seed-271828","a1-seed-314159","a1-seed-161803","a2-seed-271828","a2-seed-314159","a2-seed-161803"}: raise ValueError("candidate inventory")
    if candidate not in slots or flat(adapter)!=slots[candidate]["adapter_sha256"]: raise ValueError("candidate adapter")
    if (flat(model)!=value["model_sha256"] or sha(requests)!=value["development_requests_sha256"]
        or sha(worker)!=value["worker_sha256"] or sha(route)!=value["route_sha256"]): raise ValueError("source binding")
    if value.get("holdout_access_authorized") is not False or value.get("training_authorized") is not False: raise ValueError("scope")
    return {"status":"PASS_PUBLISHED_DEVELOPMENT_INFERENCE_AUTHORITY","authority_identity":identity,"candidate":candidate}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("authority","model","adapter","requests","worker","route","repository"): p.add_argument(f"--{name}",type=Path,required=True)
    p.add_argument("--candidate",required=True); a=p.parse_args()
    print(json.dumps(verify(a.authority,a.candidate,a.model,a.adapter,a.requests,a.worker,a.route,a.repository),sort_keys=True))

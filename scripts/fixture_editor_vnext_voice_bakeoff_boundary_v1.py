"""Fixture-only zero-step for the VOICE bake-off boundary; never imports ML runtimes."""
import argparse, hashlib, json
from pathlib import Path
try:
    from scripts.build_editor_vnext_voice_bakeoff_boundary_v1 import CANDIDATE_LOCK, PLAN_ID, R2_LOCK, audit
except ModuleNotFoundError:
    from build_editor_vnext_voice_bakeoff_boundary_v1 import CANDIDATE_LOCK, PLAN_ID, R2_LOCK, audit

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while b:=f.read(8*1024*1024): h.update(b)
    return h.hexdigest()

def zero_step(repo:Path, product:Path):
    result=audit(repo)
    voice=json.loads((product/"components/voice-candidates-v1/dependency-lock.json").read_text())
    r2=json.loads((product/"components/r2-reference-v1/dependency-lock.json").read_text())
    plan=json.loads((repo/"docs/artifacts/editor-vnext-voice-model-candidate-plan-v1.json").read_text())
    assert plan["plan_identity"]==PLAN_ID and voice["lock_identity"]==CANDIDATE_LOCK and r2["lock_identity"]==R2_LOCK
    verified=[]
    for c in voice["candidates"]:
        root=product/"components/voice-candidates-v1"/c["layout"]
        for item in c["files"]:
            if item["path"] in {"config.json","generation_config.json","model.safetensors.index.json","tokenizer.json","tokenizer_config.json","merges.txt","vocab.json"}:
                assert sha(root/item["path"])==item["sha256"]; verified.append(f"{c['candidate_id']}:{item['path']}")
    for item in r2["files"]:
        if item["path"].startswith("objects/tokenizer/") or item["path"].endswith(("config.json","index.json")):
            assert sha(product/"components/r2-reference-v1"/item["path"])==item["sha256"]; verified.append(f"V0:{item['path']}")
    result.update({"status":"PASS_EXACT_TOKENIZER_ZERO_STEP","verified_runtime_files":len(verified),"model_loaded":False,"generation_performed":False})
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--repo",type=Path,required=True); p.add_argument("--product-root",type=Path,required=True); a=p.parse_args(); print(json.dumps(zero_step(a.repo,a.product_root),sort_keys=True))

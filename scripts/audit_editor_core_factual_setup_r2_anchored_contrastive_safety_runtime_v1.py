from __future__ import annotations
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).parents[1]; B=ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-runtime-boundary.json"
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def sha(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def main():
    doc=json.loads(B.read_text(encoding="utf-8")); ident=doc.pop("runtime_boundary_identity"); assert ident==hashlib.sha256(canonical(doc)).hexdigest()
    assert doc["published_source_commit"]=="eadbddf23da3408f8cfb8233823f4f8fd974519f" and doc["published_source_tree"]=="e07eb052f78d2d634dcd4f5482fb84508f585a2d"
    assert doc["parent"]=="R2_STEP_9" and doc["weighted_sft_t1s0_line"]=="CLOSED_REFERENCE_ONLY"
    assert doc["arms"]==4 and doc["seeds"]==[161803,271828,314159] and doc["slots"]==12
    assert not any(doc[k] for k in ("model_load_authorized","optimizer_creation_authorized","training_authorized","inference_authorized","parent_selection_authority","historical_holdouts_allowed")) and doc["optimizer_steps_authorized"]==0
    assert doc["rootfs_sha256"]=="274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4" and doc["network"]=="DENY_ALL_NEW_NAMESPACE"
    paths={"worker":"scripts/editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1.py","route":"scripts/run_editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1.sh","preflight":"scripts/preflight_editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1.py","smoke":"scripts/smoke_editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1.py"}; assert doc["files"]=={k:sha(v) for k,v in paths.items()}
    tree=ast.parse((ROOT/paths["worker"]).read_text(encoding="utf-8")); forbidden={"torch","transformers","peft","bitsandbytes"}; assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and any(a.name.split('.')[0] in forbidden for a in n.names) for n in tree.body)
    route=(ROOT/paths["route"]).read_text(encoding="utf-8"); assert "--preflight-only" in route and "unshare --kill-child=KILL --mount --net" in route and "EXPECTED_ROOTFS=" in route
    print(json.dumps({"status":"PASS","blockers":0,"runtime_boundary_identity":ident,"slots":12,"model_loaded":False,"optimizer_created":False,"training_performed":False,"inference_performed":False},sort_keys=True))
if __name__=="__main__": main()

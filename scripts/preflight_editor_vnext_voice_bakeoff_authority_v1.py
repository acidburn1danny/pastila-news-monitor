"""Zero-execution authority supervisor preflight."""
import argparse, json
from pathlib import Path
try:
    from scripts.build_editor_vnext_voice_bakeoff_authority_v1 import audit
except ModuleNotFoundError:
    from build_editor_vnext_voice_bakeoff_authority_v1 import audit

def preflight(repo:Path, output_root:Path):
    result=audit(repo)
    if output_root.exists(): raise ValueError("output root must be new and absent")
    result.update({"status":"PASS_AUTHORITY_ZERO_STEP","output_root_state":"ABSENT_NEW","directories_created":False,"model_loaded":False,"inference_performed":False,"outputs":0})
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--repo",type=Path,required=True); p.add_argument("--output-root",type=Path,required=True); x=p.parse_args(); print(json.dumps(preflight(x.repo,x.output_root),sort_keys=True))

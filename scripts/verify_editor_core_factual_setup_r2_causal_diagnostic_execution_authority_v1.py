from __future__ import annotations
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).parents[1]; REL="docs/artifacts/editor-core-factual-setup-r2-causal-diagnostic-v1-execution-authority.json"
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def git(*a): return subprocess.check_output(["git","-c",f"safe.directory={ROOT}","-C",str(ROOT),*a]).decode().strip()
def verify(arm,seed,require_published=True):
    raw=(ROOT/REL).read_bytes(); doc=json.loads(raw); ident=doc.pop("authority_identity"); assert ident==hashlib.sha256(canonical(doc)).hexdigest()
    slots=[s for s in doc["slots"] if s["arm"]==arm and s["seed"]==seed]; assert len(slots)==1 and len(doc["slots"])==12 and len({s["slot_id"] for s in doc["slots"]})==12
    head=git("rev-parse","HEAD")
    if require_published:
        committed=subprocess.check_output(["git","-c",f"safe.directory={ROOT}","-C",str(ROOT),"show",f"{head}:{REL}"])
        expected=json.dumps({**doc,"authority_identity":ident},ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n"
        assert committed==expected and json.loads(committed)==json.loads(raw) and git("rev-parse","@{upstream}")==head
    else:
        subprocess.run(["git","-c",f"safe.directory={ROOT}","-C",str(ROOT),"merge-base","--is-ancestor",doc["source_commit"],head],check=True)
    return {"status":"PASS_PUBLISHED_AUTHORITY" if require_published else "PASS_LOCAL_AUTHORITY","authority_identity":ident,"commit":head,"slot":slots[0]}
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--arm",required=True); p.add_argument("--seed",type=int,required=True); p.add_argument("--local-only",action="store_true"); a=p.parse_args(); print(json.dumps(verify(a.arm,a.seed,not a.local_only),sort_keys=True))

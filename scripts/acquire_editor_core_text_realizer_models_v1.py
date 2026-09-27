"""Future bounded downloader. Execution requires separately published authority."""
from __future__ import annotations

import hashlib, json, os, urllib.parse, urllib.request
from pathlib import Path
from preflight_editor_core_text_realizer_model_acquisition_v1 import ART, PREFIX, canonical, load, run, sha

def git_oid(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def acquire() -> None:
    if os.environ.get("EDITOR_MODEL_ACQUISITION_AUTHORIZED") != "1": raise ValueError("separate acquisition authorization required")
    pre=run(Path("/root")); authority=load(f"{PREFIX}-authority.json"); snapshots=load(f"{PREFIX}-snapshots.json")
    base=Path(authority["store_root"]); receipts=[]
    base.mkdir(parents=True, exist_ok=True)
    for model in snapshots["models"]:
        final=Path(model["content_addressed_root"]); staging=Path(str(final)+authority["staging_suffix"])
        if final.exists() or staging.exists(): raise ValueError(f"no overwrite: {model['candidate_id']}")
        staging.mkdir(parents=True)
        for spec in model["files"]:
            target=staging/spec["path"]; target.parent.mkdir(parents=True,exist_ok=True)
            url=f"https://huggingface.co/{model['repo_id']}/resolve/{model['revision']}/{urllib.parse.quote(spec['path'])}?download=true"
            with urllib.request.urlopen(url) as src, target.open("wb") as dst:
                while chunk:=src.read(8*1024*1024): dst.write(chunk)
            data=target.read_bytes()
            if len(data)!=spec["size"]: raise ValueError(f"size:{spec['path']}")
            if spec["sha256"] and sha(data)!=spec["sha256"]: raise ValueError(f"sha256:{spec['path']}")
            if not spec["sha256"] and git_oid(data)!=spec["git_oid"]: raise ValueError(f"git_oid:{spec['path']}")
        receipt={"candidate_id":model["candidate_id"],"snapshot_identity":model["snapshot_identity"],"revision":model["revision"],"files":len(model["files"]),"total_bytes":model["total_bytes"]}
        receipt["receipt_identity"]=sha(canonical(receipt)); (staging/"receipt.json").write_bytes((json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode())
        staging.rename(final); receipts.append(receipt["receipt_identity"])
    program={"status":"PASS_ACQUIRED_2","authority_identity":pre["authority_identity"],"receipts":receipts}; program["receipt_identity"]=sha(canonical(program))
    (base/"program-receipt.json").write_bytes((json.dumps(program,sort_keys=True,indent=2)+"\n").encode())

if __name__ == "__main__": acquire()

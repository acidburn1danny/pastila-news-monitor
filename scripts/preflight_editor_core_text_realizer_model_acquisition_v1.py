"""No-download preflight for the bounded acquisition authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-text-realizer-model-acquisition-v1"

def canonical(v): return json.dumps(v, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
def sha(b): return hashlib.sha256(b).hexdigest()
def load(name): return json.loads((ART / name).read_text(encoding="utf-8"))
def identity(v, key):
    if v[key] != sha(canonical({k:x for k,x in v.items() if k != key})): raise ValueError(key)

def run(capacity_root: Path | None = None) -> dict:
    manifest=load(f"{PREFIX}-manifest.json"); authority=load(f"{PREFIX}-authority.json"); snapshots=load(f"{PREFIX}-snapshots.json"); quant=load(f"{PREFIX}-quantization.json")
    for v,k in ((manifest,"pack_identity"),(authority,"authority_identity"),(snapshots,"snapshots_identity"),(quant,"quantization_identity")): identity(v,k)
    for name,expected in {**manifest["files"],**manifest["source_files"]}.items():
        if sha((ART/name).read_bytes()) != expected: raise ValueError(f"manifest:{name}")
    if authority["snapshots_identity"] != snapshots["snapshots_identity"] or authority["quantization_identity"] != quant["quantization_identity"]: raise ValueError("binding")
    if [m["revision"] for m in snapshots["models"]] != ["b968826d9c46dd6066d109eabc6255188de91218","a09a35458c702b33eeacc393d103063234e8bc28"]: raise ValueError("revision")
    if any(m["license"] != "apache-2.0" for m in snapshots["models"]): raise ValueError("license")
    if not quant["same_recipe_all_challengers"] or quant["maximum_peak_vram_gib"] != 16: raise ValueError("quantization")
    forbidden=("download_authorized","model_load_authorized","quantization_authorized","inference_authorized","optimizer_creation_authorized","training_authorized","cleanup_authorized","parent_selection_authority","promotion_authorized","release_authorized")
    if any(authority[k] for k in forbidden): raise ValueError("forbidden authority")
    free = shutil.disk_usage(capacity_root).free if capacity_root else None
    if free is not None and free < authority["required_free_bytes"]: raise ValueError("disk capacity")
    return {"status":"PASS_NO_DOWNLOAD_PREFLIGHT","authority_identity":authority["authority_identity"],"models":2,"files":sum(len(m["files"]) for m in snapshots["models"]),"aggregate_bytes":snapshots["aggregate_bytes"],"required_free_bytes":authority["required_free_bytes"],"available_bytes":free,"download_performed":False,"model_loaded":False,"quantization_performed":False,"inference_performed":False}

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--capacity-root",type=Path); a=p.parse_args(); print(json.dumps(run(a.capacity_root),sort_keys=True))

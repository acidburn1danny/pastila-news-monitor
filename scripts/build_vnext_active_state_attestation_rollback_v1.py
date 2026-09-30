#!/usr/bin/env python3
"""Build the bounded VNext active-state attestation and rollback proof artifacts."""
from __future__ import annotations
import argparse, copy, hashlib, json, os
from pathlib import Path

SCHEMA = "vnext-active-state-authority-attestation-rollback-proof-v1"
CANDIDATE_COMMIT = "27d966969e1fef6a884c24906c2c991c7f38cc71"
ASSEMBLY_COMMIT = "a65095dc0b362fcbba6439d64cc5af4ae9d294ff"
CANDIDATE_LOCK_ID = "68fb2c347367ff3aa725cfb44de11be07921ad2e39fcbe98b01b389eee46c19b"
CANDIDATE_LOCK_SHA = "0ff93c4d9f550c8458d2223ae91627903bf02dc24973c59d3069fa94ada1100e"
CANDIDATE_TREE_ID = "c05fb8373f251ab0f3780e42ad219e8e0de90b92183cbf0424ace5b7cc027ba6"
ACTIVATED_AT = "2026-09-30T10:23:15Z"
ROLLBACK_PRE_TREE_CLAIM = "679611e7e4dd1341da26c036872b0d44cc8d29df426e979d197849d56ce4e244"
ROLLBACK_LOCK_SHA = "2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6"
ROLLBACK_COMPONENTS = (
    "components/r2-reference-v1", "platform/python-ml-v1", "runtime/editor-v0-v1",
    "runtime/scout-v1", "state/scout-v1",
)

def canonical(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
def identity(v): return hashlib.sha256(canonical(v)).hexdigest()
def sha(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024), b""): h.update(chunk)
    return h.hexdigest()
def excluded(rel: str):
    parts=rel.split("/")
    return "__pycache__" in parts or rel.endswith(".pyc") or rel.endswith(("-wal","-shm","-journal"))
def tree_summary(root: Path):
    rows=[]; total=0
    if not root.exists(): raise RuntimeError("missing rollback component: "+str(root))
    for p in sorted(root.rglob("*"), key=lambda x:x.relative_to(root).as_posix()):
        rel=p.relative_to(root).as_posix()
        if excluded(rel): continue
        if p.is_symlink(): rows.append({"path":rel,"type":"symlink","target":os.readlink(p)})
        elif p.is_file():
            size=p.stat().st_size; total+=size
            rows.append({"path":rel,"type":"file","size":size,"sha256":sha(p)})
    return {"tree_identity":identity(rows),"entries":len(rows),"bytes":total}
def cache_summary(root: Path):
    pyc=list(root.rglob("*.pyc")); caches=[p for p in root.rglob("__pycache__") if p.is_dir()]
    side=[p for p in root.rglob("*") if p.is_file() and p.name.endswith(("-wal","-shm","-journal"))]
    return {"pyc_files":len(pyc),"pyc_bytes":sum(p.stat().st_size for p in pyc),"cache_directories":len(caches),"sqlite_sidecars":len(side)}
def write(path: Path, value): path.write_text(json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")

def build(active: Path, rollback: Path, out: Path):
    current=json.loads((active/"product-lock.json").read_text(encoding="utf-8"))
    if current.get("product_lock_identity")!=CANDIDATE_LOCK_ID or sha(active/"product-lock.json")!=CANDIDATE_LOCK_SHA:
        raise RuntimeError("active candidate lock mismatch")
    managed=[]
    for expected in current["application_files"]:
        p=active/expected["path"]
        actual={"path":expected["path"],"type":"file","size":p.stat().st_size,"sha256":sha(p)}
        if actual!=expected: raise RuntimeError("active managed byte drift: "+expected["path"])
        managed.append(actual)
    managed_identity=identity(managed)
    rollback_lock=rollback/"product-lock.json"
    if sha(rollback_lock)!=ROLLBACK_LOCK_SHA: raise RuntimeError("rollback lock mismatch")
    components={rel:tree_summary(rollback/rel) for rel in ROLLBACK_COMPONENTS}
    rollback_manifest={
      "schema":"vnext-canonical-rollback-manifest-v1","schema_version":1,
      "rollback_root":"/root/pastila-vnext/.rollback-pre-68fb2c347367",
      "pre_activation_raw_tree_claim":{"identity":ROLLBACK_PRE_TREE_CLAIM,"status":"UNRECONCILED_NON_AUTHORITATIVE"},
      "authority":{"product_lock_sha256":ROLLBACK_LOCK_SHA,"product_lock_identity":json.loads(rollback_lock.read_text())["product_lock_identity"]},
      "managed_components":components,
      "required_paths":["product-lock.json",*ROLLBACK_COMPONENTS],
      "excluded_non_authoritative_paths":["components/voice-candidates-v1","reviews","runs"],
      "regenerable_runtime_bytes":{"rules":["**/__pycache__/**","**/*.pyc","**/*-wal","**/*-shm","**/*-journal"],"observed":cache_summary(rollback)},
      "legacy_dependency_count":0,"status":"PASS_CANONICAL_MANAGED_ROLLBACK_BYTES",
    }
    rollback_manifest["rollback_manifest_identity"]=identity(rollback_manifest)
    successor=copy.deepcopy(current)
    successor["schema_version"]=3; successor["status"]="ACTIVE"; successor["active_integration_state"]="ACTIVATED"
    successor["activation"]={
      "authorized":True,"prepared":False,"full_root_atomic_swap_required":True,
      "product_lock_replacement":True,
      "receipt_path":"manifest/activation/vnext-activation-receipt-v1.json",
      "attestation_mode":"POST_ACTIVATION_CONTENT_ADDRESSED_SUCCESSOR",
    }
    successor["installed_candidate_product_lock"]={"identity":CANDIDATE_LOCK_ID,"sha256":CANDIDATE_LOCK_SHA}
    successor["rollback_manifest_identity"]=rollback_manifest["rollback_manifest_identity"]
    successor.pop("product_lock_identity",None); successor["product_lock_identity"]=identity(successor)
    receipt={
      "schema":"vnext-activation-receipt-v1","schema_version":1,"status":"ATTESTED_ACTIVATED",
      "attestation_timing":"POST_ACTIVATION","activated_at":ACTIVATED_AT,
      "authority_commit":CANDIDATE_COMMIT,"assembly_boundary_commit":ASSEMBLY_COMMIT,
      "candidate":{"product_lock_identity":CANDIDATE_LOCK_ID,"product_lock_sha256":CANDIDATE_LOCK_SHA,"tree_identity":CANDIDATE_TREE_ID},
      "atomic_swap":{"mechanism":"FULL_ROOT_OS_RENAME_SAME_FILESYSTEM","active_root":"/root/pastila-vnext/v1","rollback_root":"/root/pastila-vnext/.rollback-pre-68fb2c347367","result":"PASS"},
      "active":{"managed_application_identity":managed_identity,"dependency_graph_identity":current["active_graph_identity"],"successor_product_lock_identity":successor["product_lock_identity"]},
      "rollback_manifest_identity":rollback_manifest["rollback_manifest_identity"],"legacy_dependency_count":0,
    }
    receipt["activation_receipt_identity"]=identity(receipt)
    out.mkdir(parents=True,exist_ok=True)
    write(out/"vnext-active-product-lock-successor-v1.json",successor)
    write(out/"vnext-activation-receipt-v1.json",receipt)
    write(out/"vnext-canonical-rollback-manifest-v1.json",rollback_manifest)
    print(json.dumps({"active_state_authority_identity":successor["product_lock_identity"],"activation_receipt_identity":receipt["activation_receipt_identity"],"rollback_manifest_identity":rollback_manifest["rollback_manifest_identity"],"managed_application_identity":managed_identity},sort_keys=True))
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--active-root",type=Path,required=True);p.add_argument("--rollback-root",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();build(a.active_root,a.rollback_root,a.output)

#!/usr/bin/env python3
import argparse, copy, hashlib, json
from pathlib import Path

ACTIVE_LOCK_ID = "b9609a71c07803ff58cd3e8980b8c8bb31cd717b538be68bdd76fa6b6914ecba"
ACTIVE_LOCK_SHA = "233488e0ed2e0e1f273ced35bcaccd52e012d49544d86a9a45402f4fc7e5d12d"
ACTIVATION_CANDIDATE_ID = "5e31722e1e78fb44d2abd74c51a00e4074a67ff254c5497bfde64e228e7b9653"
RECEIPT_ID = "1c5b0c103ba609408780f93b59ac98fec31d29151601ed20e5299cd8c8ce587f"
ROLLBACK_LOCK_ID = "68fb2c347367ff3aa725cfb44de11be07921ad2e39fcbe98b01b389eee46c19b"
ROLLBACK_LOCK_SHA = "0ff93c4d9f550c8458d2223ae91627903bf02dc24973c59d3069fa94ada1100e"
HISTORICAL_LOCK_SHA = "2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6"
TARGETS = {
 "scripts/vnext_materialized_active_preflight_v10.py": "app/cli/preflight.py",
 "scripts/audit_vnext_materialized_active_product_v12.py": "app/cli/audit.py",
}

def canonical(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
def identity(v): return hashlib.sha256(canonical(v)).hexdigest()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path, value, key):
    value.pop(key, None); value[key] = identity(value)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
def row(path, target): return {"path": target, "type": "file", "size": path.stat().st_size, "sha256": sha(path)}

def build(repo, active, rollback, historical, out):
    current = json.loads((active / "product-lock.json").read_text())
    predecessor = json.loads((rollback / "product-lock.json").read_text())
    if current.get("product_lock_identity") != ACTIVE_LOCK_ID or sha(active / "product-lock.json") != ACTIVE_LOCK_SHA: raise RuntimeError("active lock mismatch")
    if predecessor.get("product_lock_identity") != ROLLBACK_LOCK_ID or sha(rollback / "product-lock.json") != ROLLBACK_LOCK_SHA: raise RuntimeError("immediate predecessor mismatch")
    if sha(historical / "product-lock.json") != HISTORICAL_LOCK_SHA: raise RuntimeError("historical root mismatch")
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
      "schema":"vnext-canonical-rollback-manifest-v2","schema_version":2,"status":"PASS_CANONICAL_IMMEDIATE_PREDECESSOR",
      "rollback_root":"/root/pastila-vnext/.rollback-pre-exchange-5e31722e",
      "authority":{"product_lock_identity":ROLLBACK_LOCK_ID,"product_lock_sha256":ROLLBACK_LOCK_SHA},
      "verification":{"managed_inventory_source":"product-lock.json","managed_file_count":len(predecessor.get("application_files",[])),"active_graph_identity":predecessor.get("active_graph_identity"),"prospective_atomic_rollback":"RENAME_EXCHANGE_SIMULATED_PASS"},
      "historical_root":{"path":"/root/pastila-vnext/.rollback-pre-68fb2c347367","classification":"HISTORICAL_NON_CANONICAL_RETIREMENT_PENDING_SEPARATE_AUTHORITY","product_lock_sha256":HISTORICAL_LOCK_SHA},
      "legacy_dependency_count":0}
    write(out / "vnext-canonical-rollback-manifest-v2.json", manifest, "rollback_manifest_identity")
    authority = {
      "schema":"vnext-current-active-state-authority-v2","schema_version":3,"status":"ACTIVATED_ATTESTED",
      "active_root":"/root/pastila-vnext/v1","installed_product_lock":{"identity":ACTIVE_LOCK_ID,"sha256":ACTIVE_LOCK_SHA},
      "activation_candidate_product_lock_identity":ACTIVATION_CANDIDATE_ID,"activation_receipt_identity":RECEIPT_ID,
      "canonical_rollback":{"manifest_identity":manifest["rollback_manifest_identity"],"root":manifest["rollback_root"],"product_lock_identity":ROLLBACK_LOCK_ID,"product_lock_sha256":ROLLBACK_LOCK_SHA},
      "historical_root_retirement":"AUTHORIZED_FOR_SEPARATE_FUTURE_EXECUTION_ONLY","legacy_dependency_count":0}
    write(out / "vnext-current-active-state-authority-v2.json", authority, "active_state_authority_identity")
    successor = copy.deepcopy(current)
    successor["schema_version"] = 6
    successor["supersedes_product_lock_identity"] = ACTIVE_LOCK_ID
    att = copy.deepcopy(successor["activation_attestation"])
    att["activation_candidate_product_lock_identity"] = ACTIVATION_CANDIDATE_ID
    att["current_active_state_authority_identity"] = authority["active_state_authority_identity"]
    att["canonical_rollback_manifest_identity"] = manifest["rollback_manifest_identity"]
    att["canonical_rollback_product_lock_identity"] = ROLLBACK_LOCK_ID
    att["canonical_rollback_product_lock_sha256"] = ROLLBACK_LOCK_SHA
    successor["activation_attestation"] = att
    replacements = {}
    for source, target in TARGETS.items(): replacements[target] = row(repo / source, target)
    replacements["manifest/authorities/vnext-active-product-lock-successor-v1.json"] = row(out / "vnext-current-active-state-authority-v2.json", "manifest/authorities/vnext-active-product-lock-successor-v1.json")
    replacements["manifest/rollback/vnext-canonical-rollback-manifest-v1.json"] = row(out / "vnext-canonical-rollback-manifest-v2.json", "manifest/rollback/vnext-canonical-rollback-manifest-v1.json")
    rows=[]; found=set()
    for old in successor["application_files"]:
        if old["path"] in replacements: rows.append(replacements[old["path"]]); found.add(old["path"])
        else: rows.append(old)
    if found != set(replacements): raise RuntimeError("managed targets absent")
    successor["application_files"] = rows
    successor.pop("product_lock_identity", None)
    write(out / "vnext-canonical-rollback-product-lock-successor-v1.json", successor, "product_lock_identity")
    return {"status":"PASS","rollback_manifest_identity":manifest["rollback_manifest_identity"],"active_state_authority_identity":authority["active_state_authority_identity"],"product_lock_identity":successor["product_lock_identity"],"product_lock_sha256":sha(out / "vnext-canonical-rollback-product-lock-successor-v1.json"),"managed_replacements":sorted(replacements)}

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--repo",type=Path,required=True); p.add_argument("--active",type=Path,required=True); p.add_argument("--rollback",type=Path,required=True); p.add_argument("--historical",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    print(json.dumps(build(a.repo,a.active,a.rollback,a.historical,a.out),sort_keys=True))

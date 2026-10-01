import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def m(p,n):s=importlib.util.spec_from_file_location(n,R/p);x=importlib.util.module_from_spec(s);s.loader.exec_module(x);return x
def load(n):return json.loads((R/"docs/artifacts"/n).read_text())
def test_all_identities():
 b=m("scripts/build_vnext_gui_active_attestation_repair_v1.py","b")
 for n,k in (("vnext-gui-active-product-dependency-graph-v6.json","authority_identity"),("vnext-gui-canonical-rollback-manifest-v4.json","rollback_manifest_identity"),("vnext-gui-activation-receipt-v1.json","activation_receipt_identity"),("vnext-gui-active-state-authority-v1.json","active_state_authority_identity"),("vnext-gui-active-product-lock-v8.json","product_lock_identity"),("vnext-gui-active-attestation-repair-result-v1.json","result_identity")):
  v=load(n);c=v.pop(k);assert c==b.ident(v)
def test_exact_candidate_and_active_semantics():
 b=m("scripts/build_vnext_gui_active_attestation_repair_v1.py","b2");l=load("vnext-gui-active-product-lock-v8.json");r=load("vnext-gui-activation-receipt-v1.json")
 assert l["supersedes_product_lock_identity"]==b.CID==r["candidate"]["product_lock_identity"];assert l["status"]=="ACTIVE" and l["active_integration_state"]=="ACTIVATED" and l["activation"]["authorized"];assert len(l["application_files"])==33
def test_schema8_preflight_and_gui_unchanged():
 s=(R/"scripts/vnext_gui_active_preflight_v1.py").read_text();a=(R/"scripts/audit_vnext_gui_active_product_v1.py").read_text();assert "V8_GUI_ACTIVE_ATTESTED" in s and "(6,7,8)" in a
 l=load("vnext-gui-active-product-lock-v8.json");c=load("vnext-gui-active-integration-product-lock-successor-v1.json");rows={x["path"]:x for x in l["application_files"]};old={x["path"]:x for x in c["application_files"]}
 for p in ("app/cli/gui.py","app/workflow/pastila_scout/vnext_product_gui_v1.py","manifest/authorities/vnext-product-gui-cli-parity-authority-v1.json"):assert rows[p]==old[p]
def test_result_and_rollback():
 r=load("vnext-gui-active-attestation-repair-result-v1.json");assert r["status"]=="PASS" and not r["blockers"];assert r["prospective_install"]=="PASS" and r["prospective_rollback"]==r["prospective_restore"]=="PASS_BYTE_EXACT";assert not r["active_root_modified"] and not r["rollback_root_modified"]

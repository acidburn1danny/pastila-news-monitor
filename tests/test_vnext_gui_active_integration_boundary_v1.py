import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def m():s=importlib.util.spec_from_file_location("b",R/"scripts/build_vnext_gui_active_integration_boundary_v1.py");x=importlib.util.module_from_spec(s);s.loader.exec_module(x);return x
def load(n):return json.loads((R/"docs/artifacts"/n).read_text())
def test_identities():
 b=m()
 for n,k in (("vnext-gui-active-product-dependency-graph-v5.json","authority_identity"),("vnext-gui-active-integration-product-lock-successor-v1.json","product_lock_identity"),("vnext-gui-active-integration-result-v1.json","result_identity")):
  v=load(n);c=v.pop(k);assert c==b.ident(v)
def test_candidate_and_inventory():
 b=m();l=load("vnext-gui-active-integration-product-lock-successor-v1.json");assert l["status"]=="CANDIDATE_NOT_ACTIVATED" and not l["activation"]["authorized"];assert len(l["application_files"])==33 and set(b.GUI)<={x["path"] for x in l["application_files"]}
def test_graph_single_startup_no_bypass():
 g=load("vnext-gui-active-product-dependency-graph-v5.json");assert {"gui","gui_adapter","gui_authority"}<={x["id"] for x in g["nodes"]};assert g["voice_state"]=="DISABLED_UNTIL_PROMOTION"
 q=(R/"scripts/vnext_product_gui_cli_v1.py").read_text();u=(R/"src/pastila_scout/vnext_product_gui_v1.py").read_text();assert q.count("from product import startup")==1 and "preflight" not in q;assert all(x not in u for x in ("sqlite3","INSERT ","UPDATE ","TransitionRequest"))
def test_result():
 r=load("vnext-gui-active-integration-result-v1.json");assert r["status"]=="PASS" and not r["blockers"] and r["e2e_terminal"]=="EXPORTED";assert r["rollback_simulation"]==r["restore_simulation"]=="PASS_BYTE_EXACT";assert not r["active_root_modified"] and not r["canonical_rollback_modified"]

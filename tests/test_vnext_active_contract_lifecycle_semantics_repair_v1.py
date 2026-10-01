import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(p,n):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_reproducible_and_bounded():
 a=load(R/"scripts/audit_vnext_active_contract_lifecycle_semantics_repair_v1.py","a");r=a.run(R,Path("/root/pastila-vnext/v1"));assert r["status"]=="PASS" and r["runtime_bytes_unchanged"] and not r["voice_started"] and not r["gui_started"]
def test_exact_contract_binding():
 d=R/"docs/artifacts";l=json.loads((d/"vnext-active-contract-lifecycle-product-lock-successor-v1.json").read_text());g=json.loads((d/"vnext-active-product-dependency-graph-v4.json").read_text());a=json.loads((d/"vnext-current-active-state-authority-v3.json").read_text());assert l["contract_authority_bindings"]==g["contract_authority_bindings"]==a["contract_authority_bindings"]

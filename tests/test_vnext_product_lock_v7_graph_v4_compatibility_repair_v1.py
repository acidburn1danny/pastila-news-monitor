import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(p,n):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_successor_and_reproduction():
 a=load(R/"scripts/audit_vnext_product_lock_v7_graph_v4_compatibility_repair_v1.py","a");assert a.run(R)["status"]=="PASS"
def test_validator_surface():
 p=(R/"scripts/vnext_materialized_active_preflight_v11.py").read_text();q=(R/"scripts/audit_vnext_materialized_active_product_v13.py").read_text();assert "version not in (6,7)" in p and "schema_version\") not in (3,4)" in p and "schema_version') in (6,7)" in q
def test_scope():
 l=json.loads((R/"docs/artifacts/vnext-product-lock-v7-graph-v4-compatibility-successor-v1.json").read_text());assert l["supersedes_product_lock_identity"]=="3229ddda9f36971f2928ea3fdb6b78e145e956d240ede2b5d781fe3fbb0cd7a2";assert l["excluded_categories"]==["VOICE_CANDIDATES","EVALUATION","HISTORICAL_RECEIPTS","LEGACY_RUNTIME"]

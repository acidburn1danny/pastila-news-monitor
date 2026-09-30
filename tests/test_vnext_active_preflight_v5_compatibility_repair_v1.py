import importlib.util,json,sys,tempfile
from pathlib import Path
R=Path(__file__).parents[1]
def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_v5_semantics_rejects_broken_receipt_binding():
 lock=json.loads((R/'docs/artifacts/vnext-active-preflight-v5-product-lock-successor-v1.json').read_text())
 assert lock['schema_version']==5
 assert 'current_activation_receipt_identity' in lock['activation_attestation']
 text=(R/'scripts/vnext_materialized_active_preflight_v9.py').read_text()
 assert 'receipt predecessor binding' in text and 'authority receipt binding' in text and 'activation origin binding' in text
def test_auditor_supports_v4_and_v5_without_weakening_identity_checks():
 text=(R/'scripts/audit_vnext_materialized_active_product_v11.py').read_text()
 assert "schema_version')==5" in text and "schema_version')==4" in text
 assert "unsupported product-lock schema" in text and "check(d,key)" in text
def test_successor_inventory_binds_both_runtime_consumers():
 lock=json.loads((R/'docs/artifacts/vnext-active-preflight-v5-product-lock-successor-v1.json').read_text())
 rows={x['path']:x for x in lock['application_files']}
 for rel in ('app/cli/preflight.py','app/cli/audit.py'):
  assert rel in rows and rows[rel]['size']>0 and len(rows[rel]['sha256'])==64
 assert len(rows)==30
def test_result_is_fail_closed_and_non_mutating():
 result=json.loads((R/'docs/artifacts/vnext-active-preflight-v5-compatibility-repair-result-v1.json').read_text())
 assert result['status']=='PASS' and result['active_root_modified'] is False and result['rollback_roots_modified'] is False
 assert result['legacy_dependency_count']==0 and result['waiting_period'] is False

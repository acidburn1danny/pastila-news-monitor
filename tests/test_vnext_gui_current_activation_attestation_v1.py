import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def mod():s=importlib.util.spec_from_file_location('b',R/'scripts/build_vnext_gui_current_activation_attestation_v1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def load(n):return json.loads((A/n).read_text())
def test_identities_and_semantics():
 b=mod()
 for n,k in [('vnext-gui-current-activation-receipt-v1.json','activation_receipt_identity'),('vnext-gui-current-active-state-authority-v1.json','active_state_authority_identity'),('vnext-gui-current-active-product-lock-v8.json','product_lock_identity'),('vnext-gui-current-activation-attestation-result-v1.json','result_identity')]:d=load(n);c=d.pop(k);assert c==b.ident(d)
 r=load('vnext-gui-current-activation-receipt-v1.json');a=load('vnext-gui-current-active-state-authority-v1.json');l=load('vnext-gui-current-active-product-lock-v8.json');assert r['status']=='ATTESTED_CURRENT_ACTIVATION';assert a['status']=='ACTIVATED_ATTESTED';assert l['attestation_successor_of_product_lock_identity']==b.INSTALLED;assert l['activation_attestation']['current_activation_receipt_identity']==r['activation_receipt_identity'];assert l['activation_attestation']['current_active_state_authority_identity']==a['active_state_authority_identity']
def test_runtime_inventory_only_authority_replacements():
 b=mod();old=load('vnext-gui-active-product-lock-v8.json');new=load('vnext-gui-current-active-product-lock-v8.json');o={x['path']:x for x in old['application_files']};n={x['path']:x for x in new['application_files']};assert {k for k in o if o[k]!=n[k]}=={'manifest/activation/vnext-activation-receipt-v1.json','manifest/authorities/vnext-active-product-lock-successor-v1.json'};assert new['legacy_dependency_count']==0

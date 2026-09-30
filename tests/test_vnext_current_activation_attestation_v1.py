import json,types
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(path,name):
 m=types.ModuleType(name);exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m
def test_current_receipt_successors_and_install_inventory_are_acyclic():
 b=load(R/'scripts/build_vnext_current_activation_attestation_v1.py','b');a=R/'docs/artifacts';receipt=json.loads((a/'vnext-current-activation-receipt-v1.json').read_text());lock=json.loads((a/'vnext-current-active-product-lock-successor-v1.json').read_text());authority=json.loads((a/'vnext-current-active-state-authority-v1.json').read_text());rows={x['path']:x for x in lock['application_files']};assert receipt['temporal_claim']=={'activated_at':None,'status':'NOT_RECORDED_NO_RETROACTIVE_FABRICATION'};assert authority['activation_receipt_identity']==receipt['activation_receipt_identity'];assert 'attestation_successor_product_lock' not in authority;assert lock['activation_attestation']['current_active_state_authority_identity']==authority['active_state_authority_identity'];assert rows[b.RECEIPT_TARGET]==b.row(a/'vnext-current-activation-receipt-v1.json',b.RECEIPT_TARGET);assert rows[b.AUTHORITY_TARGET]==b.row(a/'vnext-current-active-state-authority-v1.json',b.AUTHORITY_TARGET)
def test_frozen_result_identity():
 b=load(R/'scripts/build_vnext_current_activation_attestation_v1.py','b');x=json.loads((R/'docs/artifacts/vnext-current-activation-attestation-repair-result-v1.json').read_text());i=x.pop('result_identity');assert i==b.identity(x)

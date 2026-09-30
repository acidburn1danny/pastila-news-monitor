import hashlib,json,shutil,tempfile,types
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[1]
def load():
 p=R/'scripts/vnext_atomic_activation_managed_mutable_v1.py';m=types.ModuleType('activation');exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def fixture(root):
 (root/'app/cli').mkdir(parents=True);(root/'state').mkdir();shutil.copy2(R/'scripts/vnext_active_runtime_bytes_policy_v3.py',root/'app/cli/runtime_bytes_policy.py');(root/'app/payload.txt').write_text('managed\n');(root/'state/product.sqlite3').write_bytes(b'state');(root/'product-lock.json').write_text('{}\n')
def test_wal_shm_and_mutable_state_are_non_authoritative(tmp_path):
 m=load();root=tmp_path/'root';fixture(root);before=m.surface_snapshot(root);(root/'state/product.sqlite3').write_bytes(b'changed');(root/'state/product.sqlite3-wal').write_bytes(b'w');(root/'state/product.sqlite3-shm').write_bytes(b's');after=m.verify_post_swap(root,before);assert sorted(after['cache'])==['state/product.sqlite3-shm','state/product.sqlite3-wal']
def test_managed_drift_and_extra_byte_fail_closed(tmp_path):
 m=load();root=tmp_path/'root';fixture(root);before=m.surface_snapshot(root);(root/'app/payload.txt').write_text('drift');pytest.raises(RuntimeError,m.verify_post_swap,root,before);(root/'app/payload.txt').write_text('managed\n');(root/'rogue.bin').write_bytes(b'x');pytest.raises(RuntimeError,m.verify_post_swap,root,before)
def test_atomic_failure_restores_old_root_byte_exact(tmp_path):
 m=load();current=tmp_path/'current';staged=tmp_path/'staged';backup=tmp_path/'backup';fixture(current);fixture(staged);old=m.full_tree_identity(current)
 def fail(root):(root/'app/payload.txt').write_text('drift');raise RuntimeError('injected')
 with pytest.raises(RuntimeError,match='injected'):m.atomic_swap(current,staged,backup,fail)
 assert m.full_tree_identity(current)==old and not backup.exists()
def test_frozen_result_identity():
 x=json.loads((R/'docs/artifacts/vnext-atomic-activation-managed-mutable-repair-result-v1.json').read_text());i=x.pop('result_identity');assert i==hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

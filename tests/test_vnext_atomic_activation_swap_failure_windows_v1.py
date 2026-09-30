import hashlib,json,types
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[1]
def load():
 p=R/'scripts/vnext_atomic_activation_managed_mutable_v1.py';m=types.ModuleType('activation');exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def fixture(path,label):
 (path/'app').mkdir(parents=True);(path/'app/value').write_text(label);(path/'product-lock.json').write_text('{"label":"'+label+'"}\n')
def test_validation_failure_is_atomic_byte_exact_rollback(tmp_path):
 m=load();current=tmp_path/'v1';staged=tmp_path/'staged';backup=tmp_path/'backup';fixture(current,'old');fixture(staged,'new');old=m.full_tree_identity(current)
 with pytest.raises(RuntimeError,match='validation'):m.atomic_swap(current,staged,backup,lambda root:(_ for _ in ()).throw(RuntimeError('validation failure')))
 assert m.full_tree_identity(current)==old and not backup.exists() and (staged/'app/value').read_text()=='new'
def test_backup_finalization_failure_rolls_back_atomic_exchange(tmp_path,monkeypatch):
 m=load();current=tmp_path/'v1';staged=tmp_path/'staged';backup=tmp_path/'backup';fixture(current,'old');fixture(staged,'new');old=m.full_tree_identity(current);monkeypatch.setattr(m.os,'replace',lambda a,b:(_ for _ in ()).throw(OSError('injected')))
 with pytest.raises(OSError,match='injected'):m.atomic_swap(current,staged,backup,lambda root:{'status':'PASS'})
 assert m.full_tree_identity(current)==old and not backup.exists() and staged.exists()
def test_transient_rollback_exchange_failure_retries_once(tmp_path,monkeypatch):
 m=load();current=tmp_path/'v1';staged=tmp_path/'staged';backup=tmp_path/'backup';fixture(current,'old');fixture(staged,'new');old=m.full_tree_identity(current);real=m.exchange_paths;calls=[0]
 def transient(a,b):
  calls[0]+=1
  if calls[0]==2:raise OSError('transient')
  return real(a,b)
 monkeypatch.setattr(m,'exchange_paths',transient)
 with pytest.raises(RuntimeError,match='validation'):m.atomic_swap(current,staged,backup,lambda root:(_ for _ in ()).throw(RuntimeError('validation failure')))
 assert calls[0]==3 and m.full_tree_identity(current)==old
def test_frozen_swap_result_identity():
 x=json.loads((R/'docs/artifacts/vnext-atomic-activation-swap-failure-windows-repair-result-v1.json').read_text());i=x.pop('result_identity');assert i==hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

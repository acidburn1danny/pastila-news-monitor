import hashlib,json,subprocess,types
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load():
 p=R/'scripts/vnext_atomic_activation_managed_mutable_v1.py';m=types.ModuleType('controller');exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def test_execution_environment_suppresses_nested_child_bytecode(tmp_path):
 m=load();pkg=tmp_path/'probe';pkg.mkdir();(pkg/'__init__.py').write_text('VALUE=1\n');launcher=tmp_path/'launcher.py';launcher.write_text("import subprocess,sys;subprocess.run([sys.executable,'-c','import probe'],check=True)\n");subprocess.run(['python3',str(launcher)],cwd=tmp_path,check=True,env=m.execution_env());assert not list(tmp_path.rglob('*.pyc'));assert not list(tmp_path.rglob('__pycache__'))
def test_unprotected_control_generates_bytecode(tmp_path):
 pkg=tmp_path/'probe';pkg.mkdir();(pkg/'__init__.py').write_text('VALUE=1\n');subprocess.run(['python3','-c','import probe'],cwd=tmp_path,check=True);assert list(tmp_path.rglob('*.pyc'))
def test_all_activation_subprocesses_use_execution_environment():
 source=(R/'scripts/vnext_atomic_activation_managed_mutable_v1.py').read_text();assert source.count('env=execution_env()')==3
def test_frozen_result_identity():
 x=json.loads((R/'docs/artifacts/vnext-atomic-activation-transitive-cache-repair-result-v1.json').read_text());i=x.pop('result_identity');assert i==hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

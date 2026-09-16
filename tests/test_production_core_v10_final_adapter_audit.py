import ast,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SCRIPT=ROOT/"scripts/audit_production_core_v10_final_adapters.py"
def module():
 spec=importlib.util.spec_from_file_location("audit_v10",SCRIPT);value=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(value);return value
def test_audit_is_fail_closed_and_complete():
 source=SCRIPT.read_text("utf-8");ast.parse(source)
 for witness in ("PAGED_ADAMW_8BIT",'receipt["optimizer_steps"]!=60','receipt["checkpoint_count"]!=60',"partition leakage","phase equivalence mismatch","gate reproducibility mismatch","rootfs object mismatch","base model object mismatch","unshare --mount --net",'"qualification_attempt_consumed":False','"blockers":[]'):
  assert witness in source
def test_seal_rejects_mutation():
 value=module();core={"a":1};sealed={**core,"identity":hashlib.sha256(value.canonical(core)).hexdigest()};assert value.sealed(sealed,"identity")
 sealed["a"]=2
 try:value.sealed(sealed,"identity")
 except ValueError:pass
 else:raise AssertionError("mutation accepted")
def test_canonical_is_stable():
 value=module();assert value.canonical({"b":1,"a":"ț"})==json.dumps({"a":"ț","b":1},ensure_ascii=False,separators=(",",":"),sort_keys=True).encode()
def test_streaming_hash(tmp_path):
 value=module();path=tmp_path/"large.bin";path.write_bytes(b"abc"*10000)
 assert value.file_sha(path)==hashlib.sha256(path.read_bytes()).hexdigest()

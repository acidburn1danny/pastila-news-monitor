from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def main():
    files={name:sha(ROOT/path) for name,path in {
      "worker":"scripts/train_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.py",
      "route":"scripts/run_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.sh",
      "preflight":"scripts/preflight_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.py",
      "smoke":"scripts/smoke_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.py"}.items()}
    core={"schema":"editor-factual-setup-r2-causal-diagnostic-real-runtime-boundary","schema_version":1,"status":"REAL_RUNTIME_BOUND_ZERO_REAL_EXECUTION","published_source_commit":"67946ad7375d7631ea184b974667e08de6db3292","published_source_tree":"20eec3317677ccbab4efdf0b6a936a61c3aedf6e","protocol_identity":"41799641949b42a3bd0c4c50abd9cb1dc7da72d594db106bbb8704b5fdfbda7a","pack_identity":"c9480b68c8f2c10ce4e36b2371d6ae564b43a4ad5fdde23e57759dc4ec8a99bc","recipes_identity":"61de5f5276af6899a708522c4e6ae91e31e40fe977aafacad4fc0bfebc29bced","evaluation_identity":"0f31cb67ea2a5b6094307bb54c76d6c3856d48088bff867a9aacdd57de8e791a","parent_adapter_identity":"c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02","parent_checkpoint_identity":"96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be","tokenizer_sha256":"d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135","arms":4,"seeds":[161803,271828,314159],"slots":12,"training_authorized":False,"model_load_authorized":False,"optimizer_creation_authorized":False,"optimizer_steps_authorized":0,"parent_selection_authority":False,"files":files,"receipts":["TEACHER_FORCED_BEFORE_AFTER","ADAPTER_DELTA","SEMANTIC_MEASUREMENT","TERMINAL"],"output_isolation":"DISTINCT_EMPTY_ROOT_PER_ARM_SEED","terminal_rule":"ONE_TERMINAL_RECEIPT_AFTER_COMPLETE_CLOSURE","invalid_payload_persistence":False}
    doc={**core,"runtime_boundary_identity":hashlib.sha256(canonical(core)).hexdigest()}
    out=ROOT/"docs/artifacts/editor-core-factual-setup-r2-causal-diagnostic-v1-runtime-boundary.json"; out.write_text(json.dumps(doc,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(doc["runtime_boundary_identity"])
if __name__=="__main__": main()

"""Build and detached-sign the zero-attempt V8.1 execution authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMMIT="48f26c7a607fbc39896cdfa8ec853ed5133ac7ec"
PUB="29616718e9d17a3c88f630af52fee0ef7a9dc7adc519412c4870f06b63ca1cca"
SOURCES=("docs/schemas/production-core-candidate-execution-evidence-v2.schema.json","scripts/execute_production_core_candidate_qualification_v3.py","scripts/launch_production_core_candidate_qualification_v4.py","scripts/resolve_production_core_object_authority_v2.sh","scripts/run_production_core_candidate_qualification_v3.sh","scripts/smoke_production_core_checkpoint_resume_v6.py","src/pastila_scout/production_core_candidate_execution_authority_v3.py","src/pastila_scout/production_core_candidate_qualification_runner_v3.py","src/pastila_scout/production_core_checkpoint_resume_v6.py","src/pastila_scout/production_core_semantic_authority_v2.py")
IDS={"qualification_generation_identity":"6d388a99731e3d4a08fa2a629374c37dd97994806ac54ffe49ab9fb1b41d630d","qualification_identity":"4d2a4b7a42141668e907bd90cb96cf8d28dce518761b3c0dc0375954ea6575f4","request_manifest_identity":"f3b0e0d11c5b73fba39ce21f5daa040e788a2ea09d455389bf990ee8264b4d03","candidate_object_manifest_identity":"7bff8d58e56c1fd8e29f91f440b4f4c91ce4d79413d4186d895406f852c6abf9","candidate_audit_receipt_identity":"7519871ebd5cc566a06a8c24f04976244cda9e0653e35464adc1ef8bd80b77a2"}
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
def build():
 core={"schema":"pastila-production-core-candidate-execution-authority","schema_version":9,"status":"FROZEN_SUCCESSOR_V8_1_LAUNCH_BINDING_REPAIR_ZERO_ATTEMPTS","bound_source_commit":COMMIT,"predecessor_terminal_failure_identity":"a4eb2c19c9b47a74236793adc01cd807d4ed5048415407095737553a12185fc6","predecessor_root_cause_addendum_identity":"06661c7dc7c73d80bfef026da13e50732de27eb2f19cc3d4ad674e3ede44f84d","authority_identities":IDS,"source_sha256":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},"matrix_rows":2400,"checkpoint_policy":{"checkpoint_count":12,"rows_per_checkpoint":200,"ordinal_source":"VALIDATED_AUTHORITY_SCHEDULE","atomic_publish":True,"content_addressed_receipt":True,"same_attempt_resume_only":True,"recalculate_finalized_rows":False},"lifecycle_completed_contract":{"termination_reason_required":True,"termination_reason_observation_binding_required":True,"missing_wrong_or_extra_fields_rejected":True},"attempt_ordinal":1,"attempt_consumption_authorized":False,"candidate_execution_authorized":False,"retry_or_redraw_authorized":False,"adjudication_performed":False,"candidate_execution_performed":False,"promotion_effect":False}
 return {**core,"execution_authority_identity":hashlib.sha256(canonical(core)).hexdigest()}
def put(p,b):
 if p.exists() and (p.is_symlink() or p.read_bytes()!=b): raise SystemExit(f"published artifact differs: {p}")
 if not p.exists(): p.write_bytes(b)
def main():
 p=argparse.ArgumentParser(); p.add_argument("--authority",type=Path,required=True); p.add_argument("--binding",type=Path,required=True); p.add_argument("--signature",type=Path,required=True); p.add_argument("--private-key",type=Path,required=True); p.add_argument("--openssl",type=Path,required=True); o=p.parse_args(); a=build(); ar=json.dumps(a,ensure_ascii=False,indent=2).encode()+b"\n"; put(o.authority,ar)
 b={"schema":"pastila-production-core-v8-1-detached-authority-binding","schema_version":1,"algorithm":"Ed25519","public_key_sha256":PUB,"authority_identity":a["execution_authority_identity"],"authority_sha256":hashlib.sha256(ar).hexdigest(),"bound_source_commit":COMMIT,"source_sha256":a["source_sha256"],"candidate_execution_authorized":False,"attempt_consumption_authorized":False}; br=canonical(b); put(o.binding,br)
 if not o.signature.exists(): subprocess.run([str(o.openssl),"pkeyutl","-sign","-inkey",str(o.private_key),"-rawin","-in",str(o.binding),"-out",str(o.signature)],check=True)
 if o.signature.is_symlink() or len(o.signature.read_bytes())!=64: raise SystemExit("signature malformed")
 print(json.dumps({"authority_identity":a["execution_authority_identity"],"binding_sha256":hashlib.sha256(br).hexdigest(),"signature_sha256":hashlib.sha256(o.signature.read_bytes()).hexdigest()})); return 0
if __name__=="__main__": raise SystemExit(main())

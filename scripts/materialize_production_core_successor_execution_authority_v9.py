"""Build and detached-sign the zero-attempt V9 execution authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMMIT="c3704aba48b0a346237909e6b43a288986bdc33b"
PUB="29616718e9d17a3c88f630af52fee0ef7a9dc7adc519412c4870f06b63ca1cca"
SOURCES=("docs/schemas/production-core-candidate-execution-evidence-v2.schema.json","scripts/execute_production_core_candidate_qualification_v3.py","scripts/launch_production_core_candidate_qualification_v9.py","scripts/resolve_production_core_object_authority_v2.sh","scripts/run_production_core_candidate_qualification_v3.sh","scripts/smoke_production_core_checkpoint_resume_v6.py","src/pastila_scout/production_core_candidate_execution_authority_v3.py","src/pastila_scout/production_core_candidate_qualification_runner_v3.py","src/pastila_scout/production_core_checkpoint_resume_v6.py","src/pastila_scout/production_core_semantic_authority_v2.py")
IDS={"qualification_generation_identity":"b7af3517a14e987efa344e9cd9c7bcbbdd9ddb3656cc9060e72fdca71ca7c8d2","qualification_identity":"fc9033f03c2d11f933183a5a8fac2df8d01bf44a1e28e1db3d252eabb7332605","request_manifest_identity":"f3b0e0d11c5b73fba39ce21f5daa040e788a2ea09d455389bf990ee8264b4d03","candidate_object_manifest_identity":"d868b2cd1dd40f62d98dc61afdb9ace81dec78588a78fc82efdc347ab7cc335d","candidate_audit_receipt_identity":"b1915eed044bb05a00e977188dae9a6d7227169e3f1b12731075e1cc691e59f3"}
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
def build():
 core={"schema":"pastila-production-core-candidate-execution-authority","schema_version":10,"status":"FROZEN_SUCCESSOR_V9_DUAL_STRUCTURAL_REMEDIATION_ZERO_ATTEMPTS","bound_source_commit":COMMIT,"predecessor_terminal_failure_identity":"077fc4b81f0e5768c7fd3b49394358a1f56a3ef217c9c527ede70bf9b870e9bb","predecessor_root_cause_addendum_identity":None,"authority_identities":IDS,"source_sha256":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},"matrix_rows":2400,"checkpoint_policy":{"checkpoint_count":12,"rows_per_checkpoint":200,"ordinal_source":"VALIDATED_AUTHORITY_SCHEDULE","atomic_publish":True,"content_addressed_receipt":True,"same_attempt_resume_only":True,"recalculate_finalized_rows":False},"lifecycle_completed_contract":{"termination_reason_required":True,"termination_reason_observation_binding_required":True,"missing_wrong_or_extra_fields_rejected":True},"attempt_ordinal":1,"attempt_consumption_authorized":False,"candidate_execution_authorized":False,"retry_or_redraw_authorized":False,"adjudication_performed":False,"candidate_execution_performed":False,"promotion_effect":False}
 return {**core,"execution_authority_identity":hashlib.sha256(canonical(core)).hexdigest()}
def put(p,b):
 if p.exists() and (p.is_symlink() or p.read_bytes()!=b): raise SystemExit(f"published artifact differs: {p}")
 if not p.exists(): p.write_bytes(b)
def main():
 p=argparse.ArgumentParser(); p.add_argument("--authority",type=Path,required=True); p.add_argument("--binding",type=Path,required=True); p.add_argument("--signature",type=Path,required=True); p.add_argument("--private-key",type=Path,required=True); p.add_argument("--openssl",type=Path,required=True); o=p.parse_args(); a=build(); ar=json.dumps(a,ensure_ascii=False,indent=2).encode()+b"\n"; put(o.authority,ar)
 b={"schema":"pastila-production-core-v9-detached-authority-binding","schema_version":1,"algorithm":"Ed25519","public_key_sha256":PUB,"authority_identity":a["execution_authority_identity"],"authority_sha256":hashlib.sha256(ar).hexdigest(),"bound_source_commit":COMMIT,"source_sha256":a["source_sha256"],"candidate_execution_authorized":False,"attempt_consumption_authorized":False}; br=canonical(b); put(o.binding,br)
 if not o.signature.exists(): subprocess.run([str(o.openssl),"pkeyutl","-sign","-inkey",str(o.private_key),"-rawin","-in",str(o.binding),"-out",str(o.signature)],check=True)
 if o.signature.is_symlink() or len(o.signature.read_bytes())!=64: raise SystemExit("signature malformed")
 print(json.dumps({"authority_identity":a["execution_authority_identity"],"binding_sha256":hashlib.sha256(br).hexdigest(),"signature_sha256":hashlib.sha256(o.signature.read_bytes()).hexdigest()})); return 0
if __name__=="__main__": raise SystemExit(main())

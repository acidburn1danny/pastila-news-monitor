import hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SCRIPT=ROOT/"scripts/materialize_production_core_v10_final_candidate_closure.py";AUDIT=ROOT/"docs/artifacts/production-core-v10-final-adapter-equivalence-audit.json";MANIFEST=ROOT/"docs/artifacts/production-core-successor-candidate-object-manifest-v10.json"
def module():
 spec=importlib.util.spec_from_file_location("closure_v10",SCRIPT);value=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(value);return value
def check(value,field,canonical):
 core=dict(value);claimed=core.pop(field);assert hashlib.sha256(canonical(core)).hexdigest()==claimed
def test_materialized_closure_is_exact_zero_attempt():
 value=module();audit=json.loads(AUDIT.read_bytes());manifest=json.loads(MANIFEST.read_bytes())
 assert audit==value.audit_receipt();assert manifest==value.candidate_manifest(audit);check(audit,"audit_identity",value.canonical);check(manifest,"manifest_identity",value.canonical)
 assert audit["status"]=="PASS_ZERO_BLOCKERS_ZERO_QUALIFICATION_ATTEMPTS" and audit["blockers"]==[]
 assert manifest["source_commit"]==value.COMMIT and manifest["source_tree"]==value.TREE
 assert manifest["adapter_audit_identity"]==audit["audit_identity"]
 assert manifest["qualification_authority_issued"] is False and manifest["qualification_attempt_consumed"] is False and manifest["candidate_execution_performed"] is False
def test_two_distinct_candidate_content_identities():
 manifest=json.loads(MANIFEST.read_bytes());assert len(set(manifest["adapter_manifest_sha256"].values()))==2

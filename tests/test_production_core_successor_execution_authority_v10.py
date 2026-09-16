import hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LAUNCHER=ROOT/"scripts/launch_production_core_candidate_qualification_v10.py";MATERIALIZER=ROOT/"scripts/materialize_production_core_successor_execution_authority_v10.py"
AUTHORITY=ROOT/"docs/artifacts/production-core-candidate-execution-authority-v10.json";BINDING=ROOT/"docs/artifacts/production-core-candidate-execution-authority-v10.binding.json";SIGNATURE=ROOT/"docs/artifacts/production-core-candidate-execution-authority-v10.binding.sig"
def module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(value);return value
def test_launcher_projection_is_inert_and_v10_only():
 value=module(LAUNCHER,"launcher_v10");assert value.EXECUTOR.name=="execute_production_core_candidate_qualification_v10.py";assert value.CORE.name=="production_core_candidate_execution_authority_v10.py"
 assert set(value.ARTIFACTS)=={"production-core-successor-comparative-qualification-generation-v10.json","production-core-candidate-request-manifest-v2.json","production-core-successor-candidate-object-manifest-v10.json","production-core-successor-candidate-generation-qualification-v10.json"}
def test_authority_build_is_zero_attempt_and_source_closed():
 value=module(MATERIALIZER,"authority_v10");authority=value.build();core=dict(authority);claimed=core.pop("execution_authority_identity");assert hashlib.sha256(value.canonical(core)).hexdigest()==claimed
 assert authority["status"]=="FROZEN_SUCCESSOR_V10_UNIFIED_EXECUTION_CONTRACT_ZERO_ATTEMPTS" and authority["matrix_rows"]==2400
 assert authority["candidate_execution_authorized"] is False and authority["attempt_consumption_authorized"] is False
 assert authority["predecessor_terminal_disposition_identity"]=="7855e21d82402416dcee091baa7a6bcc5cb4c63783aafa33c65bd355c7d83587"
 assert set(authority["source_sha256"])==set(value.SOURCES)
def test_authority_binds_unified_contract_and_final_candidates():
 value=module(MATERIALIZER,"authority_v10_ids");ids=value.build()["authority_identities"]
 assert ids["execution_contract_sha256"]==hashlib.sha256((ROOT/"src/pastila_scout/production_core_execution_contract_v10.py").read_bytes()).hexdigest()
 manifest=json.loads((ROOT/"docs/artifacts/production-core-successor-candidate-object-manifest-v10.json").read_bytes());assert ids["candidate_object_manifest_identity"]==manifest["manifest_identity"]
def test_materialized_authority_and_binding_are_exact_zero_attempt():
 value=module(MATERIALIZER,"authority_v10_materialized");authority=json.loads(AUTHORITY.read_bytes());assert authority==value.build();binding=json.loads(BINDING.read_bytes())
 assert binding["authority_identity"]==authority["execution_authority_identity"] and binding["authority_sha256"]==hashlib.sha256(AUTHORITY.read_bytes()).hexdigest()
 assert binding["bound_source_commit"]==value.COMMIT and binding["source_sha256"]==authority["source_sha256"]
 assert binding["candidate_execution_authorized"] is False and binding["attempt_consumption_authorized"] is False and len(SIGNATURE.read_bytes())==64

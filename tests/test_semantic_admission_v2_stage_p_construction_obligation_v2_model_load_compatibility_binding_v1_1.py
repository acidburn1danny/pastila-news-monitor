from __future__ import annotations

import hashlib,json,struct,sys
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_adapter_compatibility_gate_v1 import (
 expected_language_adapter_keys_v1,expected_vision_missing_keys_v1)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_authority_contract_v1 import AUTHORITY_CONTRACT_IDENTITY
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_linux_worker_v1_1 import (
 adapter_tensor_keys_from_header_v1,parse_peft_missing_adapter_warning_v1)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_only_candidate_v1_5 import LOAD_ONLY_CANDIDATE_IDENTITY
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_policy_gate_v1 import POLICY_GATE_IDENTITY,canonical_observed_model_load_policy_v1,validate_model_load_policy_gate_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_wsl_binding_v1_1 import WSL_BINDING_V1_1_IDENTITY,build_load_only_wsl_invocation_v1_1
from pastila_scout.wsl_execution_v1 import canonical_model_profile_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1


ROOT=Path(__file__).resolve().parents[1]
ARTIFACT=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-model-load-compatibility-binding-v1-1.json"


def _canonical(value):return (json.dumps(value,sort_keys=True,separators=(",", ":"))+"\n").encode()


def _authority():
 v={"schema_name":"pastila-semantic-admission-v2-construction-obligation-v2-model-load-authority","schema_version":"1.0.0",
 "authority_contract_identity":AUTHORITY_CONTRACT_IDENTITY,"policy_gate_identity":POLICY_GATE_IDENTITY,
 "load_candidate_identity":LOAD_ONLY_CANDIDATE_IDENTITY,"owner_authority_identity":"synthetic-v1-1-test",
 "required_free_vram_mib":14000,"attempt_ceiling":1,"operation":"LOAD_ONLY","generation_authorized":False,
 "retry_authorized":False,"fallback_authorized":False,"authority_receipt_identity":""}
 v["authority_receipt_identity"]=hashlib.sha256(_canonical({k:x for k,x in v.items() if k!="authority_receipt_identity"})).hexdigest();return _canonical(v)


def test_warning_parser_accepts_only_exact_336_key_payload():
 keys=expected_vision_missing_keys_v1();message="Found missing adapter keys while loading the checkpoint: "+repr(list(keys))+"."
 assert parse_peft_missing_adapter_warning_v1(messages=(message,))==keys
 for messages in ((),(message,"extra"),("different",)):
  with pytest.raises(ValueError):parse_peft_missing_adapter_warning_v1(messages=messages)


def test_header_reader_returns_exact_sorted_keys_without_tensor_data(tmp_path):
 keys=expected_language_adapter_keys_v1();header=json.dumps({key:{"dtype":"F32","shape":[1],"data_offsets":[0,4]} for key in reversed(keys)}).encode()
 adapter=tmp_path/"adapter";adapter.mkdir();(adapter/"adapter_model.safetensors").write_bytes(struct.pack("<Q",len(header))+header+b"xxxx")
 assert adapter_tensor_keys_from_header_v1(adapter_path=adapter)==keys


def test_v1_1_sources_order_compatibility_before_completion_and_load_nothing_on_import():
 worker=(ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_model_load_linux_worker_v1_1.py").read_text("utf-8")
 supervisor=(ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_model_load_linux_supervisor_v1_1.py").read_text("utf-8")
 assert worker.index("validate_adapter_compatibility_gate_v1")<worker.index('(\"MODEL_LOAD_COMPLETED\"')
 assert "compatibility_validated" in supervisor and "and compatibility_validated" in supervisor
 assert "torch" not in sys.modules and "peft" not in sys.modules and "transformers" not in sys.modules
 assert ".generate(" not in worker and "AutoTokenizer" not in worker


def test_binding_is_launch_forbidden_canonical_module_invocation(tmp_path):
 policy=tmp_path/"policy.json";authority=tmp_path/"authority.json";life=tmp_path/"life";life.mkdir()
 policy.write_bytes(validate_model_load_policy_gate_v1(observed=canonical_observed_model_load_policy_v1()));authority.write_bytes(_authority())
 prepared=build_load_only_wsl_invocation_v1_1(project_root=ROOT,policy_receipt_path=policy,
  authority_receipt_path=authority,lifecycle_root=life,boundary=WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True)))
 command=prepared.invocation.command
 assert "-m" in command and any(item.endswith("model_load_linux_supervisor_v1_1") for item in command)
 assert not any(item in {"bash","sh","-c","-lc"} for item in command)


def test_artifact_identity_rederives_and_authority_is_false():
 artifact=json.loads(ARTIFACT.read_text("utf-8"));identity=hashlib.sha256("\n".join(artifact["identity_derivation"]["ordered_utf8_fields"]).encode()).hexdigest()
 assert identity==WSL_BINDING_V1_1_IDENTITY==artifact["canonical_identity"]
 assert not any(artifact["authority"].values())

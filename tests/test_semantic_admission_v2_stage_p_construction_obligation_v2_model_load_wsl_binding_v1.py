from __future__ import annotations

import hashlib
import json
import queue
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_authority_contract_v1 import (
    AUTHORITY_CONTRACT_IDENTITY, PACKAGE_IDENTITIES, PreloadEnvironmentV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_linux_supervisor_v1 import (
    supervise_load_only_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_only_candidate_v1_5 import (
    LOAD_ONLY_CANDIDATE_IDENTITY,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_policy_gate_v1 import (
    POLICY_GATE_IDENTITY, canonical_observed_model_load_policy_v1,
    validate_model_load_policy_gate_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_wsl_binding_v1 import (
    WSL_BINDING_IDENTITY, build_load_only_wsl_invocation_v1,
)
from pastila_scout.wsl_execution_v1 import canonical_model_profile_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1


ROOT=Path(__file__).resolve().parents[1]


def _canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(",", ":"))+"\n").encode()


def _authority():
    value={"schema_name":"pastila-semantic-admission-v2-construction-obligation-v2-model-load-authority",
      "schema_version":"1.0.0","authority_contract_identity":AUTHORITY_CONTRACT_IDENTITY,
      "policy_gate_identity":POLICY_GATE_IDENTITY,"load_candidate_identity":LOAD_ONLY_CANDIDATE_IDENTITY,
      "owner_authority_identity":"synthetic-wsl-binding-test","required_free_vram_mib":14000,
      "attempt_ceiling":1,"operation":"LOAD_ONLY","generation_authorized":False,
      "retry_authorized":False,"fallback_authorized":False,"authority_receipt_identity":""}
    value["authority_receipt_identity"]=hashlib.sha256(_canonical(
      {k:v for k,v in value.items() if k!="authority_receipt_identity"})).hexdigest()
    return _canonical(value)


def _environment():
    return PreloadEnvironmentV1(PACKAGE_IDENTITIES,"NVIDIA GeForce RTX 5080",16303,14993,
      "12.0",0,"bb5a4767bb2eca6d2a71e0aacc2cbaaeab6e01a5baa693cb1330474385e5b6f9",
      "bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090",
      "312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2",
      True,"5.0.0.dev0","5.15.0",True)


def _inputs(tmp_path):
    tmp_path.mkdir(parents=True,exist_ok=True)
    policy=tmp_path/"policy.json"; authority=tmp_path/"authority.json"; lifecycle=tmp_path/"life"
    policy.write_bytes(validate_model_load_policy_gate_v1(observed=canonical_observed_model_load_policy_v1()))
    authority.write_bytes(_authority()); lifecycle.mkdir()
    return policy,authority,lifecycle


def test_wsl_binding_builds_canonical_no_shell_invocation_without_launch(tmp_path):
    policy,authority,lifecycle=_inputs(tmp_path)
    boundary=WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True))
    prepared=build_load_only_wsl_invocation_v1(project_root=ROOT,policy_receipt_path=policy,
      authority_receipt_path=authority,lifecycle_root=lifecycle,boundary=boundary)
    command=prepared.invocation.command
    assert command[:5]==("wsl.exe","-d","Ubuntu-24.04","--","env")
    assert not any(item in {"bash","sh","-c","-lc"} for item in command)
    assert command[-3].endswith("/policy.json") and command[-2].endswith("/authority.json")
    assert prepared.invocation.authority_reference==prepared.authority_receipt_identity


class _FakeQueue:
    def __init__(self,values=()):self.values=list(values)
    def get_nowait(self):
        if not self.values:raise queue.Empty
        return self.values.pop(0)
    def close(self):pass
    def join_thread(self):pass


class _FakeProcess:
    def __init__(self,*,timeout=False,events=()):self.pid=71;self.exitcode=None;self.timeout=timeout;self.events=events;self.alive=False
    def start(self):self.alive=self.timeout
    def join(self,_timeout):
        if not self.timeout:self.exitcode=0
    def is_alive(self):return self.alive
    def terminate(self):self.alive=False;self.exitcode=-15
    def kill(self):self.alive=False;self.exitcode=-9


class _FakeContext:
    def __init__(self,*,timeout=False):self.queue=_FakeQueue(() if timeout else (("MODEL_LOAD_COMPLETED",None),("MODEL_LOAD_CLEANUP_COMPLETED",None)));self.timeout=timeout
    def Queue(self):return self.queue
    def Process(self,**_kwargs):return _FakeProcess(timeout=self.timeout)


def test_supervisor_synthetic_success_and_timeout_are_single_child(monkeypatch,tmp_path):
    import pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_linux_supervisor_v1 as module
    monkeypatch.setattr(module,"observe_preload_environment_v1",_environment)
    for timeout,expected in ((False,"LOAD_ONLY_COMPLETED_AND_RELEASED"),(True,"LOAD_ONLY_FAILED_AND_RELEASED")):
        policy,authority,lifecycle=_inputs(tmp_path/("timeout" if timeout else "success"))
        monkeypatch.setattr(module.multiprocessing,"get_context",lambda mode,t=timeout:_FakeContext(timeout=t))
        assert supervise_load_only_v1(policy_receipt_path=policy,authority_receipt_path=authority,
          lifecycle_root=lifecycle,timeout_seconds=1.0)==expected
        events=[json.loads(path.read_text("utf-8"))["event"] for path in sorted(lifecycle.glob("*.json"))]
        assert events.count("MODEL_LOAD_STARTED")==1
        if timeout:
            assert "MODEL_LOAD_TIMEOUT" in events and "MODEL_LOAD_CHILD_TERMINATION_OBSERVED" in events


def test_worker_is_exact_load_only_and_preserves_vision():
    source=(ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_model_load_linux_worker_v1.py").read_text("utf-8")
    for required in ("load_in_4bit=True",'bnb_4bit_quant_type="nf4"',"bnb_4bit_use_double_quant=True",
                     "bnb_4bit_compute_dtype=torch.bfloat16",'device_map={"": 0}',"local_files_only=True",
                     "PeftModel.from_pretrained", "torch.cuda.empty_cache()"):
        assert required in source
    for forbidden in (".generate(","AutoTokenizer","vision_tower = None","multi_modal_projector = None",
                      "cpu_offload","disk_offload","device_map=\"auto\""):
        assert forbidden not in source


def test_bundle_identities_rederive_and_no_real_authority_is_issued():
    artifact=json.loads((ROOT/"docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-model-load-wsl-binding-v1.json").read_text("utf-8"))
    derivation=artifact["identity_derivation"]
    supervisor=hashlib.sha256("\n".join(derivation["supervisor_ordered_utf8_fields"]).encode()).hexdigest()
    binding=hashlib.sha256("\n".join(derivation["binding_ordered_utf8_fields"]).encode()).hexdigest()
    assert supervisor==artifact["supervisor_identity"]
    assert binding==WSL_BINDING_IDENTITY==artifact["canonical_identity"]
    assert artifact["authority"]["real_owner_authority_receipt_issued"] is False

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_authority_contract_v1 import (
    AUTHORITY_CONTRACT_IDENTITY, PACKAGE_IDENTITIES, PreloadEnvironmentV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_only_candidate_v1_5 import (
    InjectedLoadOperationsV1, LOAD_ONLY_CANDIDATE_IDENTITY,
    execute_injected_load_only_candidate_v1_5,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_policy_gate_v1 import (
    POLICY_GATE_IDENTITY, canonical_observed_model_load_policy_v1,
    validate_model_load_policy_gate_v1,
)


def _canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _authority(required=14000):
    value = {"schema_name":"pastila-semantic-admission-v2-construction-obligation-v2-model-load-authority",
        "schema_version":"1.0.0","authority_contract_identity":AUTHORITY_CONTRACT_IDENTITY,
        "policy_gate_identity":POLICY_GATE_IDENTITY,"load_candidate_identity":LOAD_ONLY_CANDIDATE_IDENTITY,
        "owner_authority_identity":"synthetic-test-owner-authority","required_free_vram_mib":required,
        "attempt_ceiling":1,"operation":"LOAD_ONLY","generation_authorized":False,
        "retry_authorized":False,"fallback_authorized":False,"authority_receipt_identity":""}
    value["authority_receipt_identity"] = hashlib.sha256(_canonical(
        {k:v for k,v in value.items() if k != "authority_receipt_identity"})).hexdigest()
    return _canonical(value)


def _environment():
    return PreloadEnvironmentV1(PACKAGE_IDENTITIES,"NVIDIA GeForce RTX 5080",16303,15002,
        "12.0",0,"bb5a4767bb2eca6d2a71e0aacc2cbaaeab6e01a5baa693cb1330474385e5b6f9",
        "bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090",
        "312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2",
        True,"5.0.0.dev0","5.15.0",True)


def _policy():
    return validate_model_load_policy_gate_v1(observed=canonical_observed_model_load_policy_v1())


def _events(result):
    return [json.loads(item)["event"] for item in result.receipts]


def test_success_is_one_attempt_then_exactly_one_cleanup():
    calls=[]; base=object(); adapted=object()
    ops=InjectedLoadOperationsV1(lambda:(calls.append("base") or base),
        lambda value:(calls.append(("adapter",value)) or adapted),
        lambda value:calls.append(("cleanup",value)))
    result=execute_injected_load_only_candidate_v1_5(raw_policy_receipt=_policy(),
        raw_authority_receipt=_authority(),environment=_environment(),operations=ops)
    assert calls == ["base",("adapter",base),("cleanup",adapted)]
    assert result.status == "LOAD_ONLY_COMPLETED_AND_RELEASED"
    assert _events(result) == ["MODEL_LOAD_STARTED","MODEL_LOAD_COMPLETED","MODEL_LOAD_CLEANUP_COMPLETED"]


@pytest.mark.parametrize("field", [item.name for item in dataclasses.fields(PreloadEnvironmentV1)])
def test_every_environment_mutation_fails_before_started(field):
    observed=_environment(); value=getattr(observed,field)
    if type(value) is bool: mutation=not value
    elif field == "vram_free_mib": mutation=13999
    elif type(value) is int: mutation=value-1
    elif type(value) is tuple: mutation=value+("drift==0",)
    else: mutation=value+"-drift"
    calls=[]
    with pytest.raises(ValueError):
        execute_injected_load_only_candidate_v1_5(raw_policy_receipt=_policy(),
            raw_authority_receipt=_authority(),environment=dataclasses.replace(observed,**{field:mutation}),
            operations=InjectedLoadOperationsV1(lambda:calls.append("base"),lambda value:value,lambda value:None))
    assert calls == []


def test_capacity_and_receipt_mismatches_fail_before_started():
    calls=[]; ops=InjectedLoadOperationsV1(lambda:calls.append("base"),lambda value:value,lambda value:None)
    for policy,authority in ((_policy()+b"x",_authority()),(_policy(),_authority(16000)),(_policy(),b"{}\n")):
        with pytest.raises(ValueError):
            execute_injected_load_only_candidate_v1_5(raw_policy_receipt=policy,
                raw_authority_receipt=authority,environment=_environment(),operations=ops)
    assert calls == []


def test_partial_load_failure_is_not_retried_and_is_cleaned_once():
    calls=[]; base=object()
    def attach(value): calls.append("adapter"); raise RuntimeError("synthetic")
    result=execute_injected_load_only_candidate_v1_5(raw_policy_receipt=_policy(),
        raw_authority_receipt=_authority(),environment=_environment(),operations=InjectedLoadOperationsV1(
            lambda:(calls.append("base") or base),attach,lambda value:calls.append(("cleanup",value))))
    assert calls == ["base","adapter",("cleanup",base)]
    assert _events(result) == ["MODEL_LOAD_STARTED","MODEL_LOAD_FAILED","MODEL_LOAD_CLEANUP_COMPLETED"]


def test_canonical_identities_rederive_from_artifact():
    artifact=json.loads(Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-model-load-only-candidate-v1-5.json").read_text("utf-8"))
    derivation=artifact["identity_derivation"]
    authority=hashlib.sha256("\n".join(derivation["authority_ordered_utf8_fields"]).encode()).hexdigest()
    candidate=hashlib.sha256("\n".join(derivation["candidate_ordered_utf8_fields"]).encode()).hexdigest()
    assert authority == AUTHORITY_CONTRACT_IDENTITY == artifact["authority_contract_identity"]
    assert candidate == LOAD_ONLY_CANDIDATE_IDENTITY == artifact["canonical_identity"]


def test_source_contains_no_runtime_or_entrypoint():
    paths=(Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_model_load_authority_contract_v1.py"),
           Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_model_load_only_candidate_v1_5.py"))
    text="\n".join(path.read_text("utf-8") for path in paths)
    forbidden=("import transformers", "from transformers", "import torch", "from torch",
               "import peft", "from peft", "import bitsandbytes", "from_pretrained",
               ".generate(", "subprocess", "Popen", "if __name__", "cuda.empty_cache")
    assert all(term not in text.lower() for term in (item.lower() for item in forbidden))

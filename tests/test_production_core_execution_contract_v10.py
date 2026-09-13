import json
from pathlib import Path

import pytest

from pastila_scout.production_core_execution_contract_v10 import (
    EDITORIAL_PROMPT_SHA256, ExecutionContractError, GENERATION_POLICY, PHASES,
    assert_phase_equivalence, compose_system_prompt, contract_identity,
    render_development_messages, render_qualification_messages,
    render_messages, render_shadow_qualification_messages, render_training_messages,
)

ROOT=Path(__file__).resolve().parents[1]
PROMPTS={
 "pastila-editor-core-v1.1-json-successor": ROOT/".experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1.txt",
 "pastila-editor-core-v1.2-json-successor": ROOT/".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
}

@pytest.mark.parametrize("candidate,path",PROMPTS.items())
def test_all_phases_are_byte_identical(candidate,path):
    raw=path.read_bytes(); assert EDITORIAL_PROMPT_SHA256[candidate]
    identity=assert_phase_equivalence(candidate=candidate,editorial_prompt=raw,user_prompt="Return exact test object.")
    assert len(identity)==64
    rendered=[entry(candidate=candidate,editorial_prompt=raw,user_prompt="Return exact test object.") for entry in (
        render_training_messages, render_development_messages,
        render_shadow_qualification_messages, render_qualification_messages)]
    assert len({json.dumps(x,ensure_ascii=False,separators=(",",":")) for x in rendered})==1
    assert "Nu folosi Markdown" in compose_system_prompt(candidate,raw)

def test_wrong_prompt_and_phase_fail_closed():
    candidate,path=next(iter(PROMPTS.items())); raw=path.read_bytes()
    with pytest.raises(ExecutionContractError): compose_system_prompt(candidate,raw+b"x")
    with pytest.raises(ExecutionContractError): render_messages(phase="DEV",candidate=candidate,editorial_prompt=raw,user_prompt="x")

def test_generation_contract_is_structural_and_non_repairing():
    assert GENERATION_POLICY["do_sample"] is False
    assert GENERATION_POLICY["maximum_utf8_bytes"]==6268
    assert GENERATION_POLICY["max_new_tokens"]==6268
    assert GENERATION_POLICY["maximum_input_tokens"]==3072
    assert GENERATION_POLICY["maximum_training_sequence_tokens"]==3072
    assert GENERATION_POLICY["maximum_total_context_tokens"]<=GENERATION_POLICY["minimum_model_context_tokens"]
    assert len(contract_identity())==64

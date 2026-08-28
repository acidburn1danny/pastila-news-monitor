from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import fields, replace
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runtime_operations_contract_v1 import (
    DECODER_IDENTITY, DEVICE_TRANSFER_POLICY, RUNTIME_OPERATIONS_CONTRACT_IDENTITY,
    TOKENIZER_IDENTITY, RuntimePromptBatchV1, validate_runtime_prompt_batch_v1,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_runtime_operations_contract_v1.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-runtime-operations-cleanup-extension-v1-1.json"
PROMPT = "cerere românească"


def _batch():
    return RuntimePromptBatchV1(
        (101, 202, 303), (1, 1, 1), 3,
        hashlib.sha256(PROMPT.encode()).hexdigest(), TOKENIZER_IDENTITY,
        DECODER_IDENTITY, 1, DEVICE_TRANSFER_POLICY,
    )


def test_exact_batch_is_deterministic_source_only() -> None:
    raw = validate_runtime_prompt_batch_v1(rendered_prompt=PROMPT, batch=_batch())
    assert raw == validate_runtime_prompt_batch_v1(rendered_prompt=PROMPT, batch=_batch())
    value = json.loads(raw)
    assert value["runtime_operations_contract_identity"] == RUNTIME_OPERATIONS_CONTRACT_IDENTITY
    assert value["prompt_token_count"] == 3
    assert value["tokenizer_or_model_loaded"] is value["generation_started"] is False


@pytest.mark.parametrize("field", fields(RuntimePromptBatchV1), ids=lambda field: field.name)
def test_every_batch_mutation_fails_closed(field) -> None:
    batch = _batch(); value = getattr(batch, field.name)
    if type(value) is int:
        changed = value + 1
    elif type(value) is tuple:
        changed = value + ((0,) if field.name == "attention_mask" else (404,))
    else:
        changed = value + "-drift"
    with pytest.raises(ValueError):
        validate_runtime_prompt_batch_v1(
            rendered_prompt=PROMPT, batch=replace(batch, **{field.name: changed}))


def test_ceiling_empty_prompt_and_wrong_type_fail_closed() -> None:
    oversized = RuntimePromptBatchV1(
        tuple(range(8193)), (1,) * 8193, 8193,
        hashlib.sha256(PROMPT.encode()).hexdigest(), TOKENIZER_IDENTITY,
        DECODER_IDENTITY, 1, DEVICE_TRANSFER_POLICY,
    )
    with pytest.raises(ValueError, match="BATCH_MISMATCH"):
        validate_runtime_prompt_batch_v1(rendered_prompt=PROMPT, batch=oversized)
    with pytest.raises(ValueError, match="PROMPT_REQUIRED"):
        validate_runtime_prompt_batch_v1(rendered_prompt="", batch=_batch())
    with pytest.raises(TypeError, match="EXACT_TYPE_REQUIRED"):
        validate_runtime_prompt_batch_v1(rendered_prompt=PROMPT, batch=object())


def test_source_and_artifact_are_nonexecuting_and_identity_exact() -> None:
    source = SOURCE.read_text("utf-8")
    modules = {node.module for node in ast.walk(ast.parse(source))
               if isinstance(node, ast.ImportFrom) and node.module}
    assert not modules.intersection({"transformers", "torch", "peft", "subprocess", "importlib"})
    assert all(term not in source for term in (
        "from_pretrained", ".generate(", "build_invocation", ".execute(",
        "AutoTokenizer", "AutoModel", "if __name__",
    ))
    artifact = json.loads(ARTIFACT.read_text("utf-8"))["runtime_operations_contract"]
    ordered = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(ordered).encode()).hexdigest() == RUNTIME_OPERATIONS_CONTRACT_IDENTITY

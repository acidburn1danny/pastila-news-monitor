from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_worker_v1_1 import (
    InjectedCompatibleGenerationResourceV1 as SourceResource,
    InjectedGenerationOutputV1 as SourceOutput,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_worker_v1_2_1 import (
    InjectedCompatibleGenerationResourceV1,
    InjectedGenerationOperationsV1,
    InjectedGenerationOutputV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runtime_operations_adapter_v1_2 import (
    ExplicitRuntimeGenerationOperationsV1_2,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runtime_operations_adapter_v1_2_1 import (
    adapt_runtime_operations_v1_2_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runtime_operations_contract_v1 import (
    DECODER_IDENTITY,
    DEVICE_TRANSFER_POLICY,
    TOKENIZER_IDENTITY,
    RuntimePromptBatchV1,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE = "pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runtime_operations_adapter_v1_2_1"


def _explicit() -> ExplicitRuntimeGenerationOperationsV1_2:
    prompt = "bound prompt"
    batch = RuntimePromptBatchV1(
        (3, 4), (1, 1), 2, __import__("hashlib").sha256(prompt.encode()).hexdigest(),
        TOKENIZER_IDENTITY, DECODER_IDENTITY, 1, DEVICE_TRANSFER_POLICY)
    return ExplicitRuntimeGenerationOperationsV1_2(
        batch,
        lambda: SourceResource(object(), b"compatibility"),
        lambda resource, observed, maximum, allowed: SourceOutput(b"{}", (5,), True),
        lambda resource: None,
    )


def test_bridge_returns_only_exact_v1_2_1_worker_types():
    adapted = adapt_runtime_operations_v1_2_1(
        rendered_prompt="bound prompt", operations=_explicit())
    assert type(adapted) is InjectedGenerationOperationsV1
    assert type(adapted.load_compatible()) is InjectedCompatibleGenerationResourceV1
    assert type(adapted.generate_once(object(), (3, 4), 1, lambda ids: (5,))) is InjectedGenerationOutputV1


def test_bridge_import_is_runtime_inert(monkeypatch):
    forbidden = {"transformers", "torch", "peft", "subprocess"}
    before = {name for name in sys.modules if name.split(".")[0] in forbidden}
    sys.modules.pop(MODULE, None)
    importlib.import_module(MODULE)
    after = {name for name in sys.modules if name.split(".")[0] in forbidden}
    assert after == before
    source = (ROOT / "src/pastila_scout/semantic_admission_v2/"
              "stage_p_construction_obligation_v2_runtime_operations_adapter_v1_2_1.py").read_text("utf-8")
    attributes = {node.attr for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Attribute)}
    assert "execute" not in attributes
    assert all(term not in source for term in ("wsl.exe", "from_pretrained", ".generate(", "Popen"))

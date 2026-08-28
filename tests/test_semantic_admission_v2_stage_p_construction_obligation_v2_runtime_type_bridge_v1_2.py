from __future__ import annotations

import hashlib

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_worker_v1_1 import (
    InjectedCompatibleGenerationResourceV1,
    InjectedGenerationOperationsV1,
    InjectedGenerationOutputV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runtime_operations_adapter_v1_2 import (
    ExplicitRuntimeGenerationOperationsV1_2,
    RUNTIME_OPERATIONS_ADAPTER_IDENTITY,
    RUNTIME_OPERATIONS_ADAPTER_IDENTITY_FIELDS,
    adapt_runtime_operations_v1_2,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runtime_operations_contract_v1 import (
    DECODER_IDENTITY,
    DEVICE_TRANSFER_POLICY,
    TOKENIZER_IDENTITY,
    RuntimePromptBatchV1,
)


def test_adapter_returns_exact_v1_1_worker_types_without_launching():
    prompt = "synthetic"
    batch = RuntimePromptBatchV1(
        (1,), (1,), 1, hashlib.sha256(prompt.encode()).hexdigest(),
        TOKENIZER_IDENTITY, DECODER_IDENTITY, 1, DEVICE_TRANSFER_POLICY,
    )
    resource = InjectedCompatibleGenerationResourceV1(object(), b"receipt")
    output = InjectedGenerationOutputV1(b"{}", (2,), True)
    explicit = ExplicitRuntimeGenerationOperationsV1_2(
        batch, lambda: resource, lambda *args: output, lambda value: None
    )
    adapted = adapt_runtime_operations_v1_2(rendered_prompt=prompt, operations=explicit)
    assert type(adapted) is InjectedGenerationOperationsV1
    assert type(adapted.load_compatible()) is InjectedCompatibleGenerationResourceV1
    assert type(adapted.generate_once(resource.resource, (1,), 1, lambda _: (2,))) is InjectedGenerationOutputV1


def test_linux_bridge_import_is_inert_and_binds_v1_1_types():
    import pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_runtime_operations_adapter_v1_1 as bridge

    assert bridge.ExplicitRuntimeGenerationOperationsV1_2.__module__.endswith(
        "runtime_operations_adapter_v1_2"
    )
    assert "prepare_linux_runtime_operations_v1_1" in bridge.__all__
    assert RUNTIME_OPERATIONS_ADAPTER_IDENTITY == hashlib.sha256(
        "\n".join(RUNTIME_OPERATIONS_ADAPTER_IDENTITY_FIELDS).encode()
    ).hexdigest()
    assert bridge.LINUX_RUNTIME_ADAPTER_IDENTITY == hashlib.sha256(
        "\n".join(bridge.LINUX_RUNTIME_ADAPTER_IDENTITY_FIELDS).encode()
    ).hexdigest()

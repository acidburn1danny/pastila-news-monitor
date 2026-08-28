"""V1.1-worker-compatible runtime operation adapter (source only)."""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .stage_p_construction_obligation_v2_injected_generation_worker_v1_1 import (
    InjectedCompatibleGenerationResourceV1,
    InjectedGenerationOperationsV1,
    InjectedGenerationOutputV1,
)
from .stage_p_construction_obligation_v2_runtime_operations_contract_v1 import (
    RuntimePromptBatchV1,
    validate_runtime_prompt_batch_v1,
)

RUNTIME_OPERATIONS_ADAPTER_IDENTITY_FIELDS = (
    "construction-obligation-v2-runtime-operations-adapter-v1.2",
    "worker-types:v1.1-exact",
    "prompt-batch-contract:v1",
    "retry-fallback-repair-selection:0",
)
RUNTIME_OPERATIONS_ADAPTER_IDENTITY = hashlib.sha256(
    "\n".join(RUNTIME_OPERATIONS_ADAPTER_IDENTITY_FIELDS).encode()
).hexdigest()


@dataclass(frozen=True, slots=True)
class ExplicitRuntimeGenerationOperationsV1_2:
    prompt_batch: RuntimePromptBatchV1
    load_compatible: Callable[[], InjectedCompatibleGenerationResourceV1]
    generate_once: Callable[
        [object, RuntimePromptBatchV1, int, Callable[[Sequence[int]], tuple[int, ...]]],
        InjectedGenerationOutputV1,
    ]
    cleanup: Callable[[object], None]


def adapt_runtime_operations_v1_2(
    *, rendered_prompt: str, operations: ExplicitRuntimeGenerationOperationsV1_2,
) -> InjectedGenerationOperationsV1:
    if type(operations) is not ExplicitRuntimeGenerationOperationsV1_2:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNTIME_OPERATIONS_V1_2_EXACT_TYPE_REQUIRED")
    validate_runtime_prompt_batch_v1(rendered_prompt=rendered_prompt, batch=operations.prompt_batch)
    batch = operations.prompt_batch

    def tokenize_prompt(observed_prompt: str) -> tuple[int, ...]:
        if observed_prompt != rendered_prompt:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNTIME_ADAPTER_PROMPT_DRIFT")
        return batch.input_token_ids

    def generate_once(resource, prompt_ids, maximum, allowed):
        if tuple(prompt_ids) != batch.input_token_ids:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNTIME_ADAPTER_BATCH_DRIFT")
        return operations.generate_once(resource, batch, maximum, allowed)

    return InjectedGenerationOperationsV1(
        tokenize_prompt, operations.load_compatible, generate_once, operations.cleanup
    )


__all__ = (
    "ExplicitRuntimeGenerationOperationsV1_2",
    "RUNTIME_OPERATIONS_ADAPTER_IDENTITY_FIELDS",
    "RUNTIME_OPERATIONS_ADAPTER_IDENTITY",
    "adapt_runtime_operations_v1_2",
)

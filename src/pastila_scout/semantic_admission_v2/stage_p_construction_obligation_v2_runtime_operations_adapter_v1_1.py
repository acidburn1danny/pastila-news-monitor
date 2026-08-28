"""Pure adapter from explicit runtime batches to injected worker operations V1."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .stage_p_construction_obligation_v2_injected_generation_worker_v1 import (
    InjectedCompatibleGenerationResourceV1,
    InjectedGenerationOperationsV1,
    InjectedGenerationOutputV1,
)
from .stage_p_construction_obligation_v2_runtime_operations_contract_v1 import (
    RuntimePromptBatchV1,
    validate_runtime_prompt_batch_v1,
)


RUNTIME_OPERATIONS_ADAPTER_IDENTITY = "612df8353538178ba8a0ea1ddcc54b9e815171b0976abcc4b6c58c8c9a1a0886"


@dataclass(frozen=True, slots=True)
class ExplicitRuntimeGenerationOperationsV1_1:
    prompt_batch: RuntimePromptBatchV1
    load_compatible: Callable[[], InjectedCompatibleGenerationResourceV1]
    generate_once: Callable[
        [object, RuntimePromptBatchV1, int,
         Callable[[Sequence[int]], tuple[int, ...]]],
        InjectedGenerationOutputV1,
    ]
    cleanup: Callable[[object], None]


def adapt_runtime_operations_v1_1(
    *, rendered_prompt: str, operations: ExplicitRuntimeGenerationOperationsV1_1,
) -> InjectedGenerationOperationsV1:
    """Bind one explicit batch without hidden mutable tokenizer state."""
    if type(operations) is not ExplicitRuntimeGenerationOperationsV1_1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNTIME_OPERATIONS_EXACT_TYPE_REQUIRED")
    validate_runtime_prompt_batch_v1(
        rendered_prompt=rendered_prompt, batch=operations.prompt_batch)
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
        tokenize_prompt, operations.load_compatible, generate_once, operations.cleanup)


__all__ = (
    "ExplicitRuntimeGenerationOperationsV1_1",
    "RUNTIME_OPERATIONS_ADAPTER_IDENTITY", "adapt_runtime_operations_v1_1",
)

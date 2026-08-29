"""Pure exact-type bridge from V1.2 runtime operations to the V1.2.1 worker."""
from __future__ import annotations

import hashlib

from .stage_p_construction_obligation_v2_injected_generation_worker_v1_1 import (
    InjectedCompatibleGenerationResourceV1 as SourceResource,
    InjectedGenerationOutputV1 as SourceOutput,
)
from .stage_p_construction_obligation_v2_injected_generation_worker_v1_2_1 import (
    InjectedCompatibleGenerationResourceV1,
    InjectedGenerationOperationsV1,
    InjectedGenerationOutputV1,
)
from .stage_p_construction_obligation_v2_runtime_operations_adapter_v1_2 import (
    ExplicitRuntimeGenerationOperationsV1_2,
)
from .stage_p_construction_obligation_v2_runtime_operations_contract_v1 import (
    validate_runtime_prompt_batch_v1,
)

RUNTIME_OPERATIONS_ADAPTER_IDENTITY_FIELDS = (
    "construction-obligation-v2-runtime-operations-adapter-v1.2.1",
    "source-operations:v1.2-exact",
    "worker-types:v1.2.1-exact",
    "callbacks:identity-preserved",
    "retry-fallback-repair-selection:0",
)
RUNTIME_OPERATIONS_ADAPTER_IDENTITY = hashlib.sha256(
    "\n".join(RUNTIME_OPERATIONS_ADAPTER_IDENTITY_FIELDS).encode()
).hexdigest()


def adapt_runtime_operations_v1_2_1(
    *, rendered_prompt: str, operations: ExplicitRuntimeGenerationOperationsV1_2,
) -> InjectedGenerationOperationsV1:
    if type(operations) is not ExplicitRuntimeGenerationOperationsV1_2:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNTIME_OPERATIONS_V1_2_EXACT_TYPE_REQUIRED")
    validate_runtime_prompt_batch_v1(
        rendered_prompt=rendered_prompt, batch=operations.prompt_batch)
    batch = operations.prompt_batch

    def tokenize_prompt(observed_prompt: str) -> tuple[int, ...]:
        if observed_prompt != rendered_prompt:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNTIME_ADAPTER_PROMPT_DRIFT")
        return batch.input_token_ids

    def load_compatible() -> InjectedCompatibleGenerationResourceV1:
        observed = operations.load_compatible()
        if type(observed) is not SourceResource:
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_SOURCE_RESOURCE_EXACT_TYPE_REQUIRED")
        return InjectedCompatibleGenerationResourceV1(
            observed.resource, observed.compatibility_receipt)

    def generate_once(resource, prompt_ids, maximum, allowed):
        if tuple(prompt_ids) != batch.input_token_ids:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNTIME_ADAPTER_BATCH_DRIFT")
        observed = operations.generate_once(resource, batch, maximum, allowed)
        if type(observed) is not SourceOutput:
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_SOURCE_OUTPUT_EXACT_TYPE_REQUIRED")
        return InjectedGenerationOutputV1(
            observed.output, observed.generated_token_ids, observed.terminal_eos)

    return InjectedGenerationOperationsV1(
        tokenize_prompt, load_compatible, generate_once, operations.cleanup)


__all__ = (
    "RUNTIME_OPERATIONS_ADAPTER_IDENTITY",
    "RUNTIME_OPERATIONS_ADAPTER_IDENTITY_FIELDS",
    "adapt_runtime_operations_v1_2_1",
)

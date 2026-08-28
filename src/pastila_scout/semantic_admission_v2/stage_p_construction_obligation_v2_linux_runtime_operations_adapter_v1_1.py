"""Identity-preserving bridge from the frozen Linux adapter to V1.1 worker types.

Preparation remains deferred. Importing and constructing this bridge performs no
tokenizer, model, provider, process, or generation operation.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .stage_p_construction_obligation_v2_injected_generation_worker_v1 import (
    InjectedCompatibleGenerationResourceV1 as LegacyResource,
    InjectedGenerationOutputV1 as LegacyOutput,
)
from .stage_p_construction_obligation_v2_injected_generation_worker_v1_1 import (
    InjectedCompatibleGenerationResourceV1,
    InjectedGenerationOutputV1,
)
from .stage_p_construction_obligation_v2_linux_runtime_operations_adapter_v1 import (
    PreparedLinuxRuntimeOperationsV1,
    prepare_linux_runtime_operations_v1,
)
from .stage_p_construction_obligation_v2_runtime_operations_adapter_v1_2 import (
    ExplicitRuntimeGenerationOperationsV1_2,
)

LINUX_RUNTIME_ADAPTER_IDENTITY_FIELDS = (
    "construction-obligation-v2-linux-runtime-operations-adapter-v1.1",
    "legacy-runtime-semantics:v1-byte-preserved",
    "worker-resource-output-types:v1.1-exact",
    "model-loading-on-import:false",
)
LINUX_RUNTIME_ADAPTER_IDENTITY = hashlib.sha256(
    "\n".join(LINUX_RUNTIME_ADAPTER_IDENTITY_FIELDS).encode()
).hexdigest()


@dataclass(frozen=True, slots=True)
class PreparedLinuxRuntimeOperationsV1_1:
    operations: ExplicitRuntimeGenerationOperationsV1_2
    token_piece_bundle: object
    tokenizer: object
    prompt_batch_receipt: bytes


def prepare_linux_runtime_operations_v1_1(
    *, rendered_prompt: str, system_prompt: str,
) -> PreparedLinuxRuntimeOperationsV1_1:
    legacy: PreparedLinuxRuntimeOperationsV1 = prepare_linux_runtime_operations_v1(
        rendered_prompt=rendered_prompt, system_prompt=system_prompt
    )

    def load_compatible() -> InjectedCompatibleGenerationResourceV1:
        observed = legacy.operations.load_compatible()
        if type(observed) is not LegacyResource:
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_LEGACY_RESOURCE_EXACT_TYPE_REQUIRED")
        return InjectedCompatibleGenerationResourceV1(
            observed.resource, observed.compatibility_receipt
        )

    def generate_once(resource, batch, maximum, allowed):
        observed = legacy.operations.generate_once(resource, batch, maximum, allowed)
        if type(observed) is not LegacyOutput:
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_LEGACY_OUTPUT_EXACT_TYPE_REQUIRED")
        return InjectedGenerationOutputV1(
            observed.output, observed.generated_token_ids, observed.terminal_eos
        )

    operations = ExplicitRuntimeGenerationOperationsV1_2(
        legacy.operations.prompt_batch,
        load_compatible,
        generate_once,
        legacy.operations.cleanup,
    )
    return PreparedLinuxRuntimeOperationsV1_1(
        operations,
        legacy.token_piece_bundle,
        legacy.tokenizer,
        legacy.prompt_batch_receipt,
    )


__all__ = (
    "LINUX_RUNTIME_ADAPTER_IDENTITY",
    "LINUX_RUNTIME_ADAPTER_IDENTITY_FIELDS",
    "PreparedLinuxRuntimeOperationsV1_1",
    "prepare_linux_runtime_operations_v1_1",
)

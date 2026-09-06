"""Candidate-neutral production Core authority and portable runtime manifest."""

from __future__ import annotations

import re
from dataclasses import dataclass

NO_PRODUCTION_CORE_DESIGNATED = "NO_PRODUCTION_CORE_DESIGNATED"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_QUALIFICATION_PROFILE_ENVIRONMENT = (
    "CUBLAS_WORKSPACE_CONFIG",
    "CUDA_VISIBLE_DEVICES",
    "PYTHONHASHSEED",
    "TOKENIZERS_PARALLELISM",
)


def _logical_name(value: str) -> bool:
    return (
        bool(value)
        and value == value.strip()
        and not any(marker in value for marker in ("/", "\\", ":"))
        and value not in {".", ".."}
    )


@dataclass(frozen=True, slots=True)
class ProductionCoreRuntimeManifestV1:
    """Identity-only contract; it resolves no paths and performs no I/O."""

    schema: str
    schema_version: int
    model_id: str
    model_sha256: str
    tokenizer_sha256: str
    runtime_kind: str
    runtime_sha256: str
    provider_adapter_id: str
    provider_adapter_sha256: str
    invocation_contract_sha256: str
    network_policy: str

    def __post_init__(self) -> None:
        if self.schema != "pastila-production-core-runtime-manifest":
            raise ValueError("invalid production Core manifest schema")
        if self.schema_version != 1:
            raise ValueError("invalid production Core manifest version")
        identities = (
            self.model_sha256,
            self.tokenizer_sha256,
            self.runtime_sha256,
            self.provider_adapter_sha256,
            self.invocation_contract_sha256,
        )
        if any(_SHA256.fullmatch(value) is None for value in identities):
            raise ValueError("invalid production Core component identity")
        names = (self.model_id, self.runtime_kind, self.provider_adapter_id)
        if any(not _logical_name(value) for value in names):
            raise ValueError("invalid production Core authority name")
        if self.model_id == NO_PRODUCTION_CORE_DESIGNATED:
            raise ValueError("neutral state is not an executable manifest")
        if self.network_policy != "DENY_ALL":
            raise ValueError("production Core runtime must deny network access")


@dataclass(frozen=True, slots=True)
class ProductionCoreExecutionProfileV1:
    schema: str
    schema_version: int
    supported_platform: str
    hardware_class: str
    accelerator_class: str
    runtime_manifest_sha256: str
    loader_sha256: str
    precision_mode: str
    thread_count: int
    thread_scheduling_policy: str
    temperature: int
    top_p: int
    seed_behavior: str
    context_tokens: int
    max_output_tokens: int | None
    network_policy: str
    allowed_environment_names: tuple[str, ...]
    cancellation_contract_sha256: str
    measurement_harness_sha256: str

    def __post_init__(self) -> None:
        if self.schema != "pastila-production-core-execution-profile":
            raise ValueError("invalid production Core execution profile schema")
        if self.schema_version != 1:
            raise ValueError("invalid production Core execution profile version")
        names = (
            self.supported_platform,
            self.hardware_class,
            self.accelerator_class,
            self.precision_mode,
            self.thread_scheduling_policy,
            self.seed_behavior,
        )
        if any(not _logical_name(value) for value in names):
            raise ValueError("execution profile is incomplete or host-bound")
        digests = (
            self.runtime_manifest_sha256,
            self.loader_sha256,
            self.cancellation_contract_sha256,
            self.measurement_harness_sha256,
        )
        if any(_SHA256.fullmatch(value) is None for value in digests):
            raise ValueError("execution profile identity is incomplete")
        if (
            type(self.thread_count) is not int
            or self.thread_count <= 0
            or self.temperature != 0
            or self.top_p != 1
            or type(self.context_tokens) is not int
            or self.context_tokens <= 0
            or (
                self.max_output_tokens is not None
                and (
                    type(self.max_output_tokens) is not int
                    or self.max_output_tokens <= 0
                )
            )
        ):
            raise ValueError("invalid frozen execution parameters")
        if (
            self.network_policy != "DENY_ALL"
            or self.allowed_environment_names != _QUALIFICATION_PROFILE_ENVIRONMENT
        ):
            raise ValueError(
                "execution profile must be offline with the exact manifest-bound environment"
            )


def require_production_core(manifest: ProductionCoreRuntimeManifestV1 | None) -> ProductionCoreRuntimeManifestV1:
    if manifest is None:
        raise RuntimeError(NO_PRODUCTION_CORE_DESIGNATED)
    if type(manifest) is not ProductionCoreRuntimeManifestV1:
        raise TypeError("invalid production Core authority")
    return manifest


__all__ = (
    "NO_PRODUCTION_CORE_DESIGNATED",
    "ProductionCoreExecutionProfileV1",
    "ProductionCoreRuntimeManifestV1",
    "require_production_core",
)

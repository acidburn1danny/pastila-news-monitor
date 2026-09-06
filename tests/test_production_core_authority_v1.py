from dataclasses import replace

import pytest

from pastila_scout.production_core_authority_v1 import (
    NO_PRODUCTION_CORE_DESIGNATED,
    ProductionCoreExecutionProfileV1,
    ProductionCoreRuntimeManifestV1,
    require_production_core,
)


def _manifest() -> ProductionCoreRuntimeManifestV1:
    digest = "a" * 64
    return ProductionCoreRuntimeManifestV1(
        schema="pastila-production-core-runtime-manifest",
        schema_version=1,
        model_id="candidate-independent-id",
        model_sha256=digest,
        tokenizer_sha256=digest,
        runtime_kind="portable-offline-runtime",
        runtime_sha256=digest,
        provider_adapter_id="offline-adapter-v1",
        provider_adapter_sha256=digest,
        invocation_contract_sha256=digest,
        network_policy="DENY_ALL",
    )


def test_no_designation_fails_closed_without_fallback() -> None:
    with pytest.raises(RuntimeError, match=f"^{NO_PRODUCTION_CORE_DESIGNATED}$"):
        require_production_core(None)


def test_manifest_requires_complete_digest_bound_offline_identity() -> None:
    manifest = _manifest()
    assert require_production_core(manifest) is manifest
    for field, value in (
        ("model_sha256", "bad"),
        ("network_policy", "ALLOW"),
        ("model_id", NO_PRODUCTION_CORE_DESIGNATED),
    ):
        with pytest.raises(ValueError):
            replace(manifest, **{field: value})
    with pytest.raises(ValueError):
        replace(manifest, runtime_kind=r"C:\\host\\runtime")


def test_execution_profile_cannot_be_incomplete_or_host_bound() -> None:
    digest = "b" * 64
    profile = ProductionCoreExecutionProfileV1(
        schema="pastila-production-core-execution-profile",
        schema_version=1,
        supported_platform="owner-approved-platform",
        hardware_class="owner-approved-hardware",
        accelerator_class="owner-approved-accelerator",
        runtime_manifest_sha256=digest,
        loader_sha256=digest,
        precision_mode="owner-approved-precision",
        thread_count=1,
        thread_scheduling_policy="fixed",
        temperature=0,
        top_p=1,
        seed_behavior="fixed-seed",
        context_tokens=1,
        max_output_tokens=None,
        network_policy="DENY_ALL",
        allowed_environment_names=(
            "CUBLAS_WORKSPACE_CONFIG",
            "CUDA_VISIBLE_DEVICES",
            "PYTHONHASHSEED",
            "TOKENIZERS_PARALLELISM",
        ),
        cancellation_contract_sha256=digest,
        measurement_harness_sha256=digest,
    )
    assert profile.network_policy == "DENY_ALL"
    for field, value in (
        ("supported_platform", r"C:\\host"),
        ("runtime_manifest_sha256", "pending"),
        ("thread_count", 0),
        ("temperature", 1),
        ("max_output_tokens", 0),
        ("allowed_environment_names", ("PATH",)),
    ):
        with pytest.raises(ValueError):
            replace(profile, **{field: value})

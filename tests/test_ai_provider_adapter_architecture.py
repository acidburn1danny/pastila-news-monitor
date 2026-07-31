"""Architecture and contract tests for provider-neutral AI infrastructure."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderAdapterError,
    AIProviderAuthenticationError,
    AIProviderAuthorizationError,
    AIProviderConfiguration,
    AIProviderInternalError,
    AIProviderMalformedResponseError,
    AIProviderRateLimitError,
    AIProviderSchemaViolationError,
    AIProviderTimeoutError,
    AIProviderTransportError,
    AIProviderUnavailableError,
    AIProviderUnsupportedCapabilityError,
    AIRetryPolicy,
    AIStructuredOutputCapabilities,
    AIStructuredOutputMode,
    compose_ai_provider_adapter,
)


def _configuration():
    return AIProviderConfiguration(
        provider_identifier="future-provider",
        model_identifier="structured-model",
        endpoint="https://provider.invalid/v1",
        authentication_reference="env:AI_PROVIDER_KEY",
        timeout_seconds=20,
        retry_policy=AIRetryPolicy(maximum_attempts=2, delay_seconds=1),
        structured_output=AIStructuredOutputCapabilities(
            supported_modes=(
                AIStructuredOutputMode.JSON,
                AIStructuredOutputMode.SCHEMA_CONSTRAINED,
            )
        ),
        maximum_context_tokens=32_000,
        metadata=(("region", "eu"),),
    )


def test_configuration_is_immutable_canonical_and_secret_free():
    configuration = _configuration()

    with pytest.raises(ValidationError):
        configuration.timeout_seconds = 1
    assert "AI_PROVIDER_KEY" in configuration.authentication_reference
    assert "credential" not in configuration.model_dump_json().casefold()


def test_configuration_rejects_noncanonical_metadata_and_secret_material():
    values = _configuration().model_dump()
    values["metadata"] = (("z", "1"), ("a", "2"))
    with pytest.raises(ValidationError, match="canonical"):
        AIProviderConfiguration.model_validate(values)
    values["metadata"] = (("header", "Bearer exposed"),)
    with pytest.raises(ValidationError, match="secret material"):
        AIProviderConfiguration.model_validate(values)


def test_retry_policy_is_adapter_configuration_not_client_behavior():
    source = Path(
        "src/pastila_scout/editor/generation/ai_provider_adapter/contracts.py"
    ).read_text(encoding="utf-8")
    client_section = source.split("class AIProviderClient(Protocol):", 1)[1].split(
        "class AIProviderAdapter(Protocol):", 1
    )[0]

    assert "retry_policy" not in client_section
    assert _configuration().retry_policy.maximum_attempts == 2


class Credentials:
    def resolve(self, authentication_reference):
        return SecretStr("not-inspectable")


class Client:
    def send(self, request, *, credential_provider):
        raise AssertionError("composition must not perform transport")


class Adapter:
    def __init__(self, **values):
        self.__dict__.update(values)
        self.configuration = values["configuration"]

    def revise(self, invocation):
        raise AssertionError("architecture-only adapter is not executable")


def test_composition_preserves_exact_dependencies_and_performs_no_io():
    configuration = _configuration()
    client = Client()
    credentials = Credentials()

    composition = compose_ai_provider_adapter(
        constructor=Adapter,
        configuration=configuration,
        client=client,
        credential_provider=credentials,
    )

    assert composition.configuration is configuration
    assert composition.client is client
    assert composition.credential_provider is credentials
    assert composition.adapter.configuration is configuration
    with pytest.raises(FrozenInstanceError):
        composition.client = Client()


def test_error_taxonomy_is_provider_neutral_and_complete():
    errors = (
        AIProviderAuthenticationError,
        AIProviderAuthorizationError,
        AIProviderTimeoutError,
        AIProviderRateLimitError,
        AIProviderTransportError,
        AIProviderMalformedResponseError,
        AIProviderSchemaViolationError,
        AIProviderUnavailableError,
        AIProviderUnsupportedCapabilityError,
        AIProviderInternalError,
    )
    assert all(issubclass(error, AIProviderAdapterError) for error in errors)


def test_production_package_has_no_concrete_provider_or_transport_dependency():
    root = Path("src/pastila_scout/editor/generation/ai_provider_adapter")
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in root.glob("*.py")
    ).casefold()
    forbidden = (
        "import openai",
        "import anthropic",
        "import google.generativeai",
        "import httpx",
        "import requests",
        "ollama",
        "azure.ai",
    )

    assert all(token not in source for token in forbidden)
    assert "PromptBuilder" not in source
    assert "GenerationPrompt" not in source


def test_frozen_layers_do_not_depend_on_ai_provider_adapter():
    frozen_root = Path("src/pastila_scout/editor")
    adapter_root = frozen_root / "generation" / "ai_provider_adapter"
    offenders = []
    for path in frozen_root.rglob("*.py"):
        if adapter_root in path.parents:
            continue
        if "ai_provider_adapter" in path.read_text(encoding="utf-8"):
            offenders.append(path)
    assert offenders == []


def test_part2b_evolves_one_runtime_without_versioned_duplicates():
    root = Path("src/pastila_scout/editor/generation/ai_provider_adapter")
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))

    assert "ProjectedAIProviderRequestV2" not in source
    assert "AIProviderInterpretationResultV2" not in source
    assert "AIProviderRuntimeV2" not in source
    assert source.count("class AIProviderAdapterRuntime:") == 1


def test_openai_hardening_remains_concrete_and_uses_frozen_extension_points():
    root = Path("src/pastila_scout/editor/generation/ai_provider_adapter")
    concrete = root / "openai"
    errors = (concrete / "errors.py").read_text(encoding="utf-8")
    client = (concrete / "client.py").read_text(encoding="utf-8")
    projector = (concrete / "projector.py").read_text(encoding="utf-8")
    composition = (concrete / "composition.py").read_text(encoding="utf-8")
    generic = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))

    assert "provider_timeout" in errors
    assert "provider_rate_limited" in errors
    assert "provider_transport_failed" in errors
    assert "ConflictError" in errors and "status_code == 408" in errors
    assert "WeakKeyDictionary" in client
    assert "expected_output_contract" in projector
    assert "editable_components" in projector
    assert "source_draft_data" not in projector
    assert (concrete / "reconstructor.py").is_file()
    assert "execution_observer" in composition
    assert "openai_" not in generic.casefold()
    assert "AIProviderAdapterRuntimeV2" not in generic
    assert "fallback" not in client.casefold()

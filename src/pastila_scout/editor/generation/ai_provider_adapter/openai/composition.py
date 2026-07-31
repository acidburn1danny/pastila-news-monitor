"""Composition root for the OpenAI Controlled Revision gateway."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pastila_scout.editor.generation.ai_provider_adapter import (
    AICredentialProvider,
    AIProviderAdapterError,
    AIProviderConfiguration,
    AIProviderExecutionObserver,
    AIProviderExecutionStatus,
    AIProviderRuntimeComposition,
    compose_ai_provider_runtime,
)
from pastila_scout.editor.generation.revision import (
    ControlledRevisionGatewayResult,
    ControlledRevisionInvocation,
)

from .client import OpenAIClientFactory, OpenAIProviderClient
from .errors import OpenAIExceptionNormalizer
from .interpreter import OpenAIControlledRevisionInterpreter
from .projector import OpenAIControlledRevisionProjector


class OpenAIControlledRevisionAdapter:
    """Expose the canonical provider runtime through the frozen gateway protocol."""

    def __init__(
        self,
        configuration: AIProviderConfiguration,
        runtime: Any,
    ) -> None:
        self.configuration = configuration
        self.runtime = runtime

    def revise(
        self, invocation: ControlledRevisionInvocation
    ) -> ControlledRevisionGatewayResult:
        """Execute once and expose no provider-specific type above this boundary."""

        result = self.runtime.execute(invocation)
        if result.status is not AIProviderExecutionStatus.SUCCESS:
            code = result.diagnostic.diagnostic_code if result.diagnostic else "failed"
            raise AIProviderAdapterError(f"AI provider execution failed: {code}")
        return result.gateway_result


@dataclass(frozen=True, slots=True)
class OpenAIControlledRevisionComposition:
    configuration: AIProviderConfiguration
    client: OpenAIProviderClient
    credential_provider: AICredentialProvider
    projector: OpenAIControlledRevisionProjector
    interpreter: OpenAIControlledRevisionInterpreter
    exception_normalizer: OpenAIExceptionNormalizer
    execution_observer: AIProviderExecutionObserver | None
    runtime_composition: AIProviderRuntimeComposition
    adapter: OpenAIControlledRevisionAdapter


def compose_openai_controlled_revision_adapter(
    *,
    configuration: AIProviderConfiguration,
    credential_provider: AICredentialProvider,
    client: OpenAIProviderClient | None = None,
    client_factory: OpenAIClientFactory | None = None,
    execution_observer: AIProviderExecutionObserver | None = None,
    sleeper: object | None = None,
    cancellation_token: object | None = None,
) -> OpenAIControlledRevisionComposition:
    """Construct the OpenAI gateway without resolving credentials or performing I/O."""

    if client is not None and client_factory is not None:
        raise ValueError("provide either an OpenAI client or client factory")
    client_options = {
        "authentication_reference": configuration.authentication_reference
    }
    if client_factory is not None:
        client_options["client_factory"] = client_factory
    transport = client or OpenAIProviderClient(**client_options)
    projector = OpenAIControlledRevisionProjector(configuration)
    interpreter = OpenAIControlledRevisionInterpreter()
    normalizer = OpenAIExceptionNormalizer()
    runtime_composition = compose_ai_provider_runtime(
        configuration=configuration,
        client=transport,
        credential_provider=credential_provider,
        projector=projector,
        interpreter=interpreter,
        exception_normalizer=normalizer,
        sleeper=sleeper,
        cancellation_token=cancellation_token,
        observer=execution_observer,
    )
    adapter = OpenAIControlledRevisionAdapter(
        configuration, runtime_composition.runtime
    )
    return OpenAIControlledRevisionComposition(
        configuration=configuration,
        client=transport,
        credential_provider=credential_provider,
        projector=projector,
        interpreter=interpreter,
        exception_normalizer=normalizer,
        execution_observer=execution_observer,
        runtime_composition=runtime_composition,
        adapter=adapter,
    )

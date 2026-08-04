"""Narrow provider-specific composition root for explicit provider-run execution."""

import os
from datetime import UTC, datetime
from hashlib import sha256
from importlib import import_module
from typing import NoReturn, Self

import httpx

from ..application_request_authority_v1 import (
    ApplicationProviderRequestV1,
    ApplicationRequestAuthorityV1,
)
from ..provider_execution_ollama_v1 import (
    OllamaExecutionConfigV1,
    OllamaHttpClientV1,
    OllamaProviderExecutorV1,
)
from ..provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from ..provider_runtime_openai_v2 import (
    OpenAIRuntimeComposerV2,
    OpenAIRuntimeConfigV2,
)
from ..provider_runtime_openai_v2.composition import _mint_factory_handoff
from ..provider_selection_v1 import ProviderChoiceV1
from .errors import ProviderRunCLIError
from .execution import execute_provider_run
from .rendering import render_provider_run

_TIMEOUT_SECONDS = 30.0


class _EnvironmentCredentialSource:
    __slots__ = ()

    def get_api_key(self) -> str:
        return os.environ.get("OPENAI_API_KEY", "")

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("provider-run credential sources cannot be serialized")

    def __repr__(self) -> str:
        return "_EnvironmentCredentialSource(<private>)"


class _OfficialSDKFactory:
    __slots__ = ()

    def create_client(
        self,
        *,
        api_key: str,
        max_retries: int,
        request_timeout_seconds: float,
    ) -> object:
        raw_client = None
        try:
            module = import_module("openai")
            raw_client = module.OpenAI(
                api_key=api_key,
                max_retries=max_retries,
                timeout=request_timeout_seconds,
            )
            facade = _OpenAIClientFacade(raw_client)
            return _mint_factory_handoff(facade)
        except Exception:  # noqa: BLE001 - SDK and handoff share no base error
            cleanup_failed = False
            if raw_client is not None:
                try:
                    raw_client.close()
                except Exception:  # noqa: BLE001 - safe pre-handoff cleanup
                    cleanup_failed = True
            if cleanup_failed:
                raise RuntimeError("OpenAI SDK cleanup failed") from None
            raise RuntimeError("OpenAI SDK construction failed") from None
        finally:
            del api_key

    def close_client(self, client: object) -> None:
        client.close()

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("provider-run SDK factories cannot be serialized")

    def __repr__(self) -> str:
        return "_OfficialSDKFactory(<private>)"


class _OpenAIClientFacade:
    """Materialize the SDK's lazy Responses resource for sealed ownership."""

    def __init__(self, raw_client: object) -> None:
        self._raw_client = raw_client
        self.responses = raw_client.responses

    def close(self) -> None:
        self._raw_client.close()

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("provider-run SDK client facades cannot be serialized")

    def __repr__(self) -> str:
        return "_OpenAIClientFacade(<private>)"


def run_provider_command(provider_text: str, prompt: str) -> int:
    """Compose, execute, render, and clean up one explicit provider invocation."""
    try:
        provider = ProviderChoiceV1(provider_text)
        requested_at = datetime.now(UTC)
        reference_hash = sha256(requested_at.isoformat().encode("utf-8")).hexdigest()
        application = ApplicationProviderRequestV1(
            provider,
            prompt,
            f"cli-provider-run-v1:{reference_hash}",
            requested_at,
            TimeoutPolicyV2(timeout_seconds=_TIMEOUT_SECONDS),
            CancellationTokenV2(cancellation_requested=False),
        )
        provider_request = ApplicationRequestAuthorityV1().build(application)
        if provider is ProviderChoiceV1.OPENAI:
            result = _run_openai(provider, provider_request)
        else:
            result = _run_ollama(provider, provider_request)
        exit_code, lines = render_provider_run(provider, result)
    except Exception:  # noqa: BLE001 - CLI never exposes lower failures
        error = ProviderRunCLIError("Provider run error: execution failed")
        error.__suppress_context__ = True
        print(str(error))
        return 2
    for line in lines:
        print(line)
    return exit_code


def _run_openai(provider, provider_request):
    base_composer = OpenAIRuntimeComposerV2(
        OpenAIRuntimeConfigV2(
            model="gpt-4.1-mini",
            enabled=True,
            max_retries=0,
            request_timeout_seconds=_TIMEOUT_SECONDS,
        ),
        credential_source=_EnvironmentCredentialSource(),
        sdk_factory=_OfficialSDKFactory(),
    )
    runtime = _load_openai_bridged_composer()(base_composer).compose()
    try:
        return execute_provider_run(
            provider=provider,
            provider_request=provider_request,
            selected_executor=runtime.executor,
        )
    finally:
        runtime.close()


def _run_ollama(provider, provider_request):
    with httpx.Client() as raw_client:
        executor = OllamaProviderExecutorV1(
            OllamaHttpClientV1(raw_client),
            OllamaExecutionConfigV1(
                model="qwen3:14b", base_url="http://localhost:11434"
            ),
        )
        return execute_provider_run(
            provider=provider,
            provider_request=provider_request,
            selected_executor=executor,
        )


def _load_openai_bridged_composer():
    package = "pastila_scout.provider_runtime_openai_" + "bridged_v2"
    module = import_module(package)
    return vars(module)["OpenAIBridgedRuntimeComposerV2"]


__all__ = ("run_provider_command",)

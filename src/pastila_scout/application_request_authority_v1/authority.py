"""Construct one authoritative provider-neutral execution request."""

import unicodedata
from dataclasses import dataclass
from typing import NoReturn, Self

from pastila_scout.provider_execution_v2 import (
    ExecutionContextV2,
    ProviderExecutionRequestV2,
)
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.provider_v2 import (
    ProviderMessageInputV2,
    ProviderRequestIntentV2,
    ProviderRequestUnitInputV2,
    build_provider_request_envelope,
)

from ..provider_adapters_v2.ollama import OllamaProviderAdapter
from ..provider_adapters_v2.openai import OpenAIProviderAdapter
from .canonical import application_request_seals, canonical_application_prompt
from .errors import ApplicationRequestAuthorityError
from .models import ApplicationProviderRequestV1


@dataclass(frozen=True, slots=True)
class ApplicationRequestAuthorityV1:
    """Stateless application authority with no execution capability."""

    def build(
        self, request: ApplicationProviderRequestV1
    ) -> ProviderExecutionRequestV2:
        """Build and reconstruct exactly one provider-neutral request."""
        built = _construct(request)
        del request
        del self
        if type(built) is not ProviderExecutionRequestV2:
            del built
            _raise_error("application provider request construction failed")
        return built

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("application request authorities cannot be serialized")

    def __repr__(self) -> str:
        return "ApplicationRequestAuthorityV1()"


def _descriptor(choice: ProviderChoiceV1):
    if choice is ProviderChoiceV1.OPENAI:
        return OpenAIProviderAdapter.descriptor
    if choice is ProviderChoiceV1.OLLAMA:
        return OllamaProviderAdapter.descriptor
    _raise_error("invalid application provider request")


def _construct(request: object) -> ProviderExecutionRequestV2 | None:
    try:
        if type(request) is not ApplicationProviderRequestV1:
            return None
        source = request.__copy__()
        canonical_prompt = canonical_application_prompt(source.prompt)
        descriptor = _descriptor(source.provider)
        (
            plan_reference,
            plan_identity,
            plan_fingerprint,
            draft_reference,
            draft_fingerprint,
            unit_reference,
        ) = application_request_seals(source.request_reference, canonical_prompt)
        intent = ProviderRequestIntentV2(
            execution_plan_reference=plan_reference,
            execution_plan_identity=plan_identity,
            execution_plan_fingerprint=plan_fingerprint,
            draft_reference=draft_reference,
            draft_fingerprint=draft_fingerprint,
            request_units=(
                ProviderRequestUnitInputV2(
                    source_request_reference=unit_reference,
                    ordinal=0,
                    messages=(
                        ProviderMessageInputV2(
                            role="generation", content=canonical_prompt, ordinal=0
                        ),
                    ),
                ),
            ),
        )
        envelope = build_provider_request_envelope(intent, descriptor)
        context = ExecutionContextV2(
            request_id=f"application-request-v1:{plan_fingerprint}",
            requested_at=source.requested_at,
            cancellation=source.cancellation,
        )
        candidate = ProviderExecutionRequestV2(
            provider=descriptor,
            request_intent=intent,
            request_envelope=envelope,
            context=context,
            timeout_policy=source.timeout_policy,
        )
        built = ProviderExecutionRequestV2.model_validate(
            candidate.model_dump(mode="python", warnings=False), strict=True
        )
        lower_prompt = built.request_intent.request_units[0].messages[0].content
        if lower_prompt != canonical_prompt or not unicodedata.is_normalized(
            "NFC", lower_prompt
        ):
            return None
        return built
    except Exception:  # noqa: BLE001 - all lower details remain private
        return None


def _raise_error(message: str) -> NoReturn:
    error = ApplicationRequestAuthorityError(message)
    error.__suppress_context__ = True
    raise error


__all__ = ("ApplicationRequestAuthorityV1",)

"""Strict immutable application input for one provider-neutral request."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NoReturn

from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.provider_v2.canonical import semantic_sha256

from .errors import ApplicationRequestAuthorityError

MAX_PROMPT_CHARACTERS = 200_000


@dataclass(frozen=True, slots=True, init=False, repr=False)
class ApplicationProviderRequestV1:
    """Complete explicit application intent without runtime dependencies."""

    provider: ProviderChoiceV1
    prompt: str
    request_reference: str
    requested_at: datetime
    timeout_policy: TimeoutPolicyV2
    cancellation: CancellationTokenV2
    _seal: str

    def __init__(
        self,
        provider: ProviderChoiceV1,
        prompt: str,
        request_reference: str,
        requested_at: datetime,
        timeout_policy: TimeoutPolicyV2,
        cancellation: CancellationTokenV2,
    ) -> None:
        state, message = _validated_state(
            provider,
            prompt,
            request_reference,
            requested_at,
            timeout_policy,
            cancellation,
        )
        if message is not None or state is None:
            del (
                self,
                provider,
                prompt,
                request_reference,
                requested_at,
                timeout_policy,
                cancellation,
                state,
            )
            _raise_error(message or "invalid application provider request")
        (
            valid_provider,
            valid_prompt,
            valid_reference,
            valid_requested_at,
            valid_timeout,
            valid_cancellation,
            valid_seal,
        ) = state
        object.__setattr__(self, "provider", valid_provider)
        object.__setattr__(self, "prompt", valid_prompt)
        object.__setattr__(self, "request_reference", valid_reference)
        object.__setattr__(self, "requested_at", valid_requested_at)
        object.__setattr__(self, "timeout_policy", valid_timeout)
        object.__setattr__(self, "cancellation", valid_cancellation)
        object.__setattr__(self, "_seal", valid_seal)

    def __repr__(self) -> str:
        valid = _reconstruct(self)
        return (
            "ApplicationProviderRequestV1("
            f"provider={valid.provider!r}, "
            f"prompt=<redacted {len(valid.prompt)} characters>, "
            f"request_reference={valid.request_reference!r}, "
            f"requested_at={valid.requested_at!r}, "
            f"timeout_policy={valid.timeout_policy!r}, "
            f"cancellation={valid.cancellation!r})"
        )

    def __copy__(self) -> ApplicationProviderRequestV1:
        return _reconstruct(self)

    def __deepcopy__(self, memo: dict[int, object]) -> ApplicationProviderRequestV1:
        del memo
        return self.__copy__()

    def __reduce__(
        self,
    ) -> tuple[type[ApplicationProviderRequestV1], tuple[object, ...]]:
        valid = _reconstruct(self)
        return (
            ApplicationProviderRequestV1,
            (
                valid.provider,
                valid.prompt,
                valid.request_reference,
                valid.requested_at,
                valid.timeout_policy,
                valid.cancellation,
            ),
        )


def _validated_state(
    provider: object,
    prompt: object,
    request_reference: object,
    requested_at: object,
    timeout_policy: object,
    cancellation: object,
) -> tuple[tuple[object, ...] | None, str | None]:
    if type(provider) is not ProviderChoiceV1:
        return None, "invalid application provider request"
    if (
        type(prompt) is not str
        or not prompt.strip()
        or prompt != prompt.strip()
        or len(prompt) > MAX_PROMPT_CHARACTERS
    ):
        return None, "invalid application provider request"
    if (
        type(request_reference) is not str
        or not request_reference
        or request_reference != request_reference.strip()
        or len(request_reference) > 120
    ):
        return None, "invalid application provider request"
    if (
        type(requested_at) is not datetime
        or requested_at.tzinfo is None
        or requested_at.utcoffset() is None
    ):
        return None, "invalid application provider request"
    try:
        valid_timeout = TimeoutPolicyV2.model_validate(
            timeout_policy.model_dump(mode="python", warnings=False), strict=True
        )
        valid_cancellation = CancellationTokenV2.model_validate(
            cancellation.model_dump(mode="python", warnings=False), strict=True
        )
    except Exception:  # noqa: BLE001 - lower validation remains private
        return None, "invalid application provider request"
    return (
        (
            provider,
            prompt,
            request_reference,
            requested_at,
            valid_timeout,
            valid_cancellation,
            _application_seal(
                provider,
                prompt,
                request_reference,
                requested_at,
                valid_timeout,
                valid_cancellation,
            ),
        ),
        None,
    )


def _reconstruct(value: object) -> ApplicationProviderRequestV1:
    if type(value) is not ApplicationProviderRequestV1:
        _raise_error("invalid application provider request")
    try:
        fields = tuple(
            object.__getattribute__(value, name)
            for name in (
                "provider",
                "prompt",
                "request_reference",
                "requested_at",
                "timeout_policy",
                "cancellation",
            )
        )
        retained_seal = object.__getattribute__(value, "_seal")
    except AttributeError:
        del value
        _raise_error("invalid application provider request")
    del value
    rebuilt = ApplicationProviderRequestV1(*fields)
    if retained_seal != object.__getattribute__(rebuilt, "_seal"):
        del fields, retained_seal, rebuilt
        _raise_error("invalid application provider request")
    return rebuilt


def _application_seal(
    provider: ProviderChoiceV1,
    prompt: str,
    request_reference: str,
    requested_at: datetime,
    timeout_policy: TimeoutPolicyV2,
    cancellation: CancellationTokenV2,
) -> str:
    return semantic_sha256(
        {
            "domain": "module-3.6-application-provider-request-v1-seal",
            "provider": provider.value,
            "prompt": prompt,
            "request_reference": request_reference,
            "requested_at": requested_at.isoformat(),
            "timeout_seconds": timeout_policy.timeout_seconds,
            "cancellation_requested": cancellation.cancellation_requested,
        }
    )


def _raise_error(message: str) -> NoReturn:
    error = ApplicationRequestAuthorityError(message)
    error.__suppress_context__ = True
    raise error


__all__ = ("MAX_PROMPT_CHARACTERS", "ApplicationProviderRequestV1")

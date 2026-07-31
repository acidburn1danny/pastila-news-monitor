"""Client-injected OpenAI executor without SDK or transport ownership."""

from dataclasses import dataclass, field
from inspect import signature
from types import FunctionType

from pydantic import ValidationError

from pastila_scout.provider_execution_v2 import (
    ExecutionConfigurationError,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)

from .errors import OpenAIExecutionBoundaryError
from .interface import OpenAIExecutionClientV2
from .mapping import build_openai_execution_request, project_openai_execution_response
from .models import OpenAIExecutionConfigV2, OpenAIExecutionResponseV2


@dataclass(frozen=True, slots=True)
class OpenAIProviderExecutorV2:
    """Orchestrate one execution through an explicitly injected client."""

    client: OpenAIExecutionClientV2
    config: OpenAIExecutionConfigV2
    _authorized_function: FunctionType = field(init=False, repr=False, compare=False)
    _invocation_kind: str = field(init=False, repr=False, compare=False)
    _receiver: object = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        authority = _validated_client_authority(self.client)
        if authority is None:
            raise ExecutionConfigurationError("invalid OpenAI execution client")
        try:
            config = OpenAIExecutionConfigV2.model_validate(self.config)
        except (TypeError, ValueError, ValidationError) as error:
            raise ExecutionConfigurationError(
                "invalid OpenAI execution configuration"
            ) from error
        object.__setattr__(self, "config", config)
        function, invocation_kind, receiver = authority
        object.__setattr__(self, "_authorized_function", function)
        object.__setattr__(self, "_invocation_kind", invocation_kind)
        object.__setattr__(self, "_receiver", receiver)

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        """Execute exactly once unless validation or cancellation prevents dispatch."""

        authority = _reconstruct_request(request)
        if authority.context.cancellation.cancellation_requested:
            return _failure_result(
                authority,
                ExecutionOutcomeV2.CANCELLED,
                "openai-pre-dispatch-cancelled",
                "OpenAI execution was cancelled before dispatch.",
            )
        try:
            client_request = build_openai_execution_request(authority, self.config)
        except OpenAIExecutionBoundaryError as error:
            raise ExecutionConfigurationError(
                "invalid OpenAI execution authority"
            ) from error
        try:
            raw_response = self._invoke_authorized(client_request)
        except (
            Exception  # noqa: BLE001 - injected clients have no shared exception type
        ):
            return _failure_result(
                authority,
                ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
                "openai-client-contract-failure",
                "The injected OpenAI client failed.",
            )
        try:
            response = OpenAIExecutionResponseV2.model_validate(raw_response)
        except (TypeError, ValueError, ValidationError):
            return _failure_result(
                authority,
                ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
                "openai-malformed-response",
                "The injected OpenAI client returned an invalid response.",
            )
        try:
            result = project_openai_execution_response(response, authority)
            return ProviderExecutionResultV2.model_validate(result)
        except (OpenAIExecutionBoundaryError, TypeError, ValueError, ValidationError):
            return _failure_result(
                authority,
                ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
                "openai-response-projection-failure",
                "The OpenAI response could not be projected.",
            )

    def _invoke_authorized(self, request: object) -> object:
        if self._invocation_kind == "static":
            return self._authorized_function(request)
        return self._authorized_function(self._receiver, request)


def _reconstruct_request(
    request: ProviderExecutionRequestV2,
) -> ProviderExecutionRequestV2:
    try:
        return ProviderExecutionRequestV2.model_validate(request)
    except (TypeError, ValueError, ValidationError) as error:
        raise ExecutionConfigurationError(
            "invalid provider execution request"
        ) from error


def _validated_client_authority(
    value: object,
) -> tuple[FunctionType, str, object] | None:
    client_type = type(value)
    if type(client_type) is not type:
        return None
    try:
        hierarchy = type.__getattribute__(client_type, "__mro__")
        namespaces = tuple(
            type.__getattribute__(owner, "__dict__") for owner in hierarchy
        )
        if _has_custom_attribute_lookup(namespaces):
            return None
        lifecycle = _static_lifecycle(namespaces)
        function, invocation_kind, receiver, bound_arguments = _static_callable_shape(
            lifecycle, client_type, value
        )
        callable_shape = _metadata_free_clone(function)
        signature(callable_shape, follow_wrapped=False).bind(*bound_arguments, object())
    except (AttributeError, TypeError, ValueError):
        return None
    return function, invocation_kind, receiver


def _has_custom_attribute_lookup(namespaces: tuple[object, ...]) -> bool:
    for namespace in namespaces:
        if "__getattr__" in namespace:
            return True
        if "__getattribute__" in namespace:
            return namespace["__getattribute__"] is not object.__getattribute__
    return False


def _static_lifecycle(namespaces: tuple[object, ...]) -> object:
    for namespace in namespaces:
        if "complete" in namespace:
            return namespace["complete"]
    raise AttributeError("missing lifecycle method")


def _static_callable_shape(
    lifecycle: object,
    client_type: type[object],
    value: object,
) -> tuple[FunctionType, str, object, tuple[object, ...]]:
    if type(lifecycle) is staticmethod:
        function = lifecycle.__func__
        invocation_kind = "static"
        receiver: object = None
        arguments: tuple[object, ...] = ()
    elif type(lifecycle) is classmethod:
        function = lifecycle.__func__
        invocation_kind = "class"
        receiver = client_type
        arguments = (client_type,)
    elif type(lifecycle) is FunctionType:
        function = lifecycle
        invocation_kind = "instance"
        receiver = value
        arguments = (value,)
    else:
        raise TypeError("unsupported lifecycle descriptor")
    if type(function) is not FunctionType:
        raise TypeError("unsupported lifecycle callable")
    return function, invocation_kind, receiver, arguments


def _metadata_free_clone(function: FunctionType) -> FunctionType:
    clone = FunctionType(
        function.__code__,
        function.__globals__,
        function.__name__,
        function.__defaults__,
        function.__closure__,
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def _failure_result(
    request: ProviderExecutionRequestV2,
    outcome: ExecutionOutcomeV2,
    code: str,
    message: str,
) -> ProviderExecutionResultV2:
    return ProviderExecutionResultV2(
        request_id=request.context.request_id,
        provider_id=request.provider.provider_id,
        request_envelope_identity=request.request_envelope.identity,
        outcome=outcome,
        finished_at=request.context.requested_at,
        failure_code=code,
        failure_message=message,
    )


__all__ = ("OpenAIProviderExecutorV2",)

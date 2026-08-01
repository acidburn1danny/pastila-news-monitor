"""Operational injected OpenAI runtime composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from inspect import iscoroutinefunction, signature
from types import FunctionType, MappingProxyType
from weakref import ReferenceType, ref

from pydantic import ValidationError

from .errors import (
    OpenAIRuntimeConfigurationError,
    OpenAIRuntimeCredentialError,
    OpenAIRuntimeDependencyError,
    OpenAIRuntimeLifecycleError,
)
from .models import (
    OpenAIRuntimeCompositionV2,
    OpenAIRuntimeConfigV2,
    _OpenAIRuntimeLifecycleOwnerV2,
)


@dataclass(frozen=True, slots=True, init=False)
class _OpenAISDKFactoryResultV2:
    """Validated atomic handoff minted from exactly one raw client."""

    raw_client: object = field(repr=False)
    responses_resource: object = field(repr=False)
    close_function: FunctionType = field(repr=False)
    close_receiver: object = field(repr=False)
    ownership_identity: int
    client_reference: ReferenceType[object] = field(repr=False)

    def __copy__(self) -> _OpenAISDKFactoryResultV2:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> _OpenAISDKFactoryResultV2:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> object:
        raise TypeError("OpenAI SDK factory handoffs are not serializable")


@dataclass(frozen=True, slots=True)
class _OwnershipLease:
    identity: int
    client_reference: ReferenceType[object] = field(repr=False)


class _OwnershipState(Enum):
    LIVE = auto()
    TERMINAL_FAILED = auto()


@dataclass(frozen=True, slots=True)
class _OwnershipRecord:
    client_reference: ReferenceType[object] = field(repr=False)
    state: _OwnershipState


_OWNERSHIP_TRACKER: dict[int, _OwnershipRecord] = {}


def _mint_factory_handoff(raw_client: object) -> _OpenAISDKFactoryResultV2:
    """Mint one coherent handoff or leave ownership with the trusted factory."""

    responses_resource = _static_instance_field(raw_client, "responses")
    close_function = _static_method_authority(raw_client, "close", mode="raw_closer")
    if responses_resource is None or close_function is None:
        raise TypeError("invalid OpenAI SDK factory handoff")
    if not _responses_authority_is_valid(responses_resource):
        raise TypeError("invalid OpenAI SDK factory handoff")
    try:
        client_reference = ref(raw_client)
    except TypeError as error:
        raise TypeError("OpenAI SDK clients must support weak references") from error
    handoff = object.__new__(_OpenAISDKFactoryResultV2)
    object.__setattr__(handoff, "raw_client", raw_client)
    object.__setattr__(handoff, "responses_resource", responses_resource)
    object.__setattr__(handoff, "close_function", close_function)
    object.__setattr__(handoff, "close_receiver", raw_client)
    object.__setattr__(handoff, "ownership_identity", id(raw_client))
    object.__setattr__(handoff, "client_reference", client_reference)
    return handoff


@dataclass(frozen=True, slots=True, init=False)
class OpenAIRuntimeComposerV2:
    """Validated plan for one independent injected runtime composition."""

    config: OpenAIRuntimeConfigV2
    _credential_source: object = field(repr=False)
    _sdk_factory: object = field(repr=False)
    _credential_function: FunctionType = field(repr=False)
    _factory_function: FunctionType = field(repr=False)

    def __init__(
        self,
        config: object,
        *,
        credential_source: object,
        sdk_factory: object,
    ) -> None:
        authority = _validate_config(config)
        if authority is None:
            raise OpenAIRuntimeConfigurationError("invalid OpenAI runtime config")
        credential_function = _static_method_authority(
            credential_source, "get_api_key", mode="source"
        )
        if credential_function is None:
            raise OpenAIRuntimeConfigurationError("invalid OpenAI credential source")
        factory_function = _static_method_authority(
            sdk_factory, "create_client", mode="factory"
        )
        if factory_function is None:
            raise OpenAIRuntimeConfigurationError("invalid OpenAI SDK factory")
        if not _has_static_method(sdk_factory, "close_client", mode="closer"):
            raise OpenAIRuntimeConfigurationError("invalid OpenAI SDK lifecycle")
        object.__setattr__(self, "config", authority)
        object.__setattr__(self, "_credential_source", credential_source)
        object.__setattr__(self, "_sdk_factory", sdk_factory)
        object.__setattr__(self, "_credential_function", credential_function)
        object.__setattr__(self, "_factory_function", factory_function)

    def compose(self) -> OpenAIRuntimeCompositionV2:
        """Build one owned runtime using the pinned injected dependencies."""

        outcome = _compose_isolated(self)
        del self
        return _return_or_raise_composition(outcome)


@dataclass(frozen=True, slots=True)
class _SafeCompositionFailure:
    category: str
    message: str


def _compose_isolated(
    composer: OpenAIRuntimeComposerV2,
) -> OpenAIRuntimeCompositionV2 | _SafeCompositionFailure:
    config = _validate_config(object.__getattribute__(composer, "config"))
    if config is None:
        return _SafeCompositionFailure("configuration", "invalid OpenAI runtime config")
    source = object.__getattribute__(composer, "_credential_source")
    source_function = object.__getattribute__(composer, "_credential_function")
    try:
        api_key = source_function(source)
    except Exception:  # noqa: BLE001 - injected sources share no exception type
        return _SafeCompositionFailure(
            "credential", "OpenAI credential retrieval failed"
        )
    del source
    del source_function
    if not _api_key_is_valid(api_key):
        del api_key
        return _SafeCompositionFailure("credential", "invalid OpenAI credential")
    factory = object.__getattribute__(composer, "_sdk_factory")
    factory_function = object.__getattribute__(composer, "_factory_function")
    try:
        factory_result = factory_function(
            factory,
            api_key=api_key,
            max_retries=0,
            request_timeout_seconds=config.request_timeout_seconds,
        )
    except Exception:  # noqa: BLE001 - injected factories share no exception type
        del api_key
        return _SafeCompositionFailure("dependency", "OpenAI SDK construction failed")
    del api_key
    del factory
    del factory_function
    claimed = _claim_factory_handoff(factory_result)
    del factory_result
    if claimed is None:
        return _SafeCompositionFailure(
            "dependency", "invalid OpenAI SDK factory result"
        )
    if type(claimed) is _SafeCompositionFailure:
        return claimed
    responses_resource, lifecycle = claimed
    try:
        from pastila_scout.provider_execution_openai_sdk_v2 import (
            OpenAISDKCapabilityV2,
            OpenAISDKClientV2,
        )
        from pastila_scout.provider_execution_openai_v2 import (
            OpenAIExecutionConfigV2,
            OpenAIProviderExecutorV2,
        )

        capability = OpenAISDKCapabilityV2(responses_resource, max_retries=0)
        del responses_resource
        sdk_client = OpenAISDKClientV2(capability)
        del capability
        execution_config = OpenAIExecutionConfigV2(model=config.model)
        executor = OpenAIProviderExecutorV2(client=sdk_client, config=execution_config)
        del execution_config
        result = OpenAIRuntimeCompositionV2(sdk_client, executor, lifecycle)
        del sdk_client
        del executor
        return result
    except Exception:  # noqa: BLE001 - assembly boundaries use distinct errors
        rollback = lifecycle._close_and_sanitize()
        del lifecycle
        if rollback.failed:
            return _SafeCompositionFailure(
                "lifecycle", "OpenAI runtime rollback failed"
            )
        return _SafeCompositionFailure("dependency", "OpenAI runtime assembly failed")


def _claim_factory_handoff(
    value: object,
) -> tuple[object, _OpenAIRuntimeLifecycleOwnerV2] | _SafeCompositionFailure | None:
    if type(value) is not _OpenAISDKFactoryResultV2:
        return None
    raw_client = object.__getattribute__(value, "raw_client")
    responses_resource = object.__getattribute__(value, "responses_resource")
    close_function = object.__getattribute__(value, "close_function")
    close_receiver = object.__getattribute__(value, "close_receiver")
    identity = object.__getattribute__(value, "ownership_identity")
    client_reference = object.__getattribute__(value, "client_reference")
    if (
        type(identity) is not int
        or identity != id(raw_client)
        or close_receiver is not raw_client
        or type(close_function) is not FunctionType
        or type(client_reference) is not ReferenceType
        or client_reference() is not raw_client
        or _static_instance_field(raw_client, "responses") is not responses_resource
        or _static_method_authority(raw_client, "close", mode="raw_closer")
        is not close_function
        or not _responses_authority_is_valid(responses_resource)
    ):
        return None
    existing = _OWNERSHIP_TRACKER.get(identity)
    if existing is not None:
        if existing.client_reference() is raw_client:
            if existing.state is _OwnershipState.TERMINAL_FAILED:
                return _SafeCompositionFailure(
                    "lifecycle", "OpenAI runtime client cleanup previously failed"
                )
            return _SafeCompositionFailure(
                "lifecycle", "OpenAI runtime client is already owned"
            )
        _OWNERSHIP_TRACKER.pop(identity, None)

    def discard_stale(reference: ReferenceType[object]) -> None:
        current = _OWNERSHIP_TRACKER.get(identity)
        if current is not None and current.client_reference is reference:
            _OWNERSHIP_TRACKER.pop(identity, None)

    tracked_reference = ref(raw_client, discard_stale)
    _OWNERSHIP_TRACKER[identity] = _OwnershipRecord(
        tracked_reference, _OwnershipState.LIVE
    )
    lease = _OwnershipLease(identity, tracked_reference)
    lifecycle = _OpenAIRuntimeLifecycleOwnerV2._from_pinned(
        close_function,
        close_receiver,
        _release_ownership_success,
        _mark_ownership_cleanup_failed,
        lease,
    )
    return responses_resource, lifecycle


def _release_ownership_success(lease: _OwnershipLease) -> None:
    current = _OWNERSHIP_TRACKER.get(lease.identity)
    if (
        current is not None
        and current.client_reference is lease.client_reference
        and current.state is _OwnershipState.LIVE
    ):
        _OWNERSHIP_TRACKER.pop(lease.identity, None)


def _mark_ownership_cleanup_failed(lease: _OwnershipLease) -> None:
    current = _OWNERSHIP_TRACKER.get(lease.identity)
    if (
        current is not None
        and current.client_reference is lease.client_reference
        and current.state is _OwnershipState.LIVE
    ):
        _OWNERSHIP_TRACKER[lease.identity] = _OwnershipRecord(
            lease.client_reference, _OwnershipState.TERMINAL_FAILED
        )


def _return_or_raise_composition(
    outcome: OpenAIRuntimeCompositionV2 | _SafeCompositionFailure,
) -> OpenAIRuntimeCompositionV2:
    if type(outcome) is OpenAIRuntimeCompositionV2:
        return outcome
    if outcome.category == "configuration":
        error = OpenAIRuntimeConfigurationError(outcome.message)
    elif outcome.category == "credential":
        error = OpenAIRuntimeCredentialError(outcome.message)
    elif outcome.category == "lifecycle":
        error = OpenAIRuntimeLifecycleError(outcome.message)
    else:
        error = OpenAIRuntimeDependencyError(outcome.message)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _validate_config(value: object) -> OpenAIRuntimeConfigV2 | None:
    try:
        return OpenAIRuntimeConfigV2.model_validate(value)
    except (TypeError, ValueError, ValidationError):
        return None


def _validate_api_key(value: object) -> None:
    """Validate a retrieved key without retaining or exposing its contents."""

    if not _api_key_is_valid(value):
        raise OpenAIRuntimeCredentialError("invalid OpenAI credential")


def _api_key_is_valid(value: object) -> bool:
    return (
        type(value) is str
        and bool(value)
        and bool(value.strip())
        and value == value.strip()
    )


def _static_instance_field(value: object, name: str) -> object | None:
    value_type = type(value)
    if type(value_type) is not type:
        return None
    hierarchy = type.__getattribute__(value_type, "__mro__")
    namespaces = tuple(type.__getattribute__(owner, "__dict__") for owner in hierarchy)
    if any(type(namespace) is not MappingProxyType for namespace in namespaces):
        return None
    if any(
        name in namespace
        or "__getattr__" in namespace
        or (
            "__getattribute__" in namespace
            and namespace["__getattribute__"] is not object.__getattribute__
        )
        for namespace in namespaces
    ):
        return None
    try:
        namespace = object.__getattribute__(value, "__dict__")
    except AttributeError:
        return None
    if type(namespace) is not dict or name not in namespace:
        return None
    return namespace[name]


def _responses_authority_is_valid(value: object) -> bool:
    function = _static_method_authority(value, "create", mode="responses")
    return function is not None


def _has_static_method(value: object, name: str, *, mode: str) -> bool:
    return _static_method_authority(value, name, mode=mode) is not None


def _static_method_authority(
    value: object, name: str, *, mode: str
) -> FunctionType | None:
    value_type = type(value)
    if type(value_type) is not type:
        return None
    hierarchy = type.__getattribute__(value_type, "__mro__")
    namespaces = tuple(type.__getattribute__(owner, "__dict__") for owner in hierarchy)
    if any(type(namespace) is not MappingProxyType for namespace in namespaces):
        return None
    if any(
        "__getattr__" in namespace
        or (
            "__getattribute__" in namespace
            and namespace["__getattribute__"] is not object.__getattribute__
        )
        for namespace in namespaces
    ):
        return None
    for namespace in namespaces:
        if name not in namespace:
            continue
        function = namespace[name]
        if type(function) is not FunctionType:
            return None
        clone = FunctionType(
            function.__code__,
            function.__globals__,
            function.__name__,
            function.__defaults__,
            function.__closure__,
        )
        clone.__kwdefaults__ = function.__kwdefaults__
        if iscoroutinefunction(clone):
            return None
        try:
            bound = signature(clone, follow_wrapped=False)
            if mode == "source":
                bound.bind(value)
            elif mode == "factory":
                bound.bind(
                    value,
                    api_key="key",
                    max_retries=0,
                    request_timeout_seconds=1.0,
                )
            elif mode == "responses":
                bound.bind(
                    value,
                    model="model",
                    input=[],
                    timeout=1.0,
                    store=False,
                    stream=False,
                    background=False,
                )
            elif mode == "raw_closer":
                bound.bind(value)
            else:
                bound.bind(value, object())
        except (TypeError, ValueError):
            return None
        return function
    return None


__all__ = ("OpenAIRuntimeComposerV2",)

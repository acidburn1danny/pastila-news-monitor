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
    generation: object | None = field(default=None, repr=False)


class _OwnershipState(Enum):
    LIVE = auto()
    CLAIMED = auto()
    TERMINAL_FAILED = auto()


@dataclass(frozen=True, slots=True)
class _OwnershipRecord:
    client_reference: ReferenceType[object] = field(repr=False)
    state: _OwnershipState


_OWNERSHIP_TRACKER: dict[int, _OwnershipRecord] = {}


class _RuntimeRegistrationAuthority:
    """Sealed process-local provenance for one raw-client registration."""

    __slots__ = (
        "_callback",
        "_generation",
        "_owner",
        "_target_identity",
        "_target_reference",
    )

    def __copy__(self) -> _RuntimeRegistrationAuthority:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> _RuntimeRegistrationAuthority:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> object:
        del protocol
        raise TypeError("runtime registration authorities cannot be serialized")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise TypeError("runtime registration authorities are immutable")

    def __delattr__(self, name: str) -> None:
        del name
        raise TypeError("runtime registration authorities are immutable")

    def __repr__(self) -> str:
        return "_RuntimeRegistrationAuthority(<private>)"

    __str__ = __repr__


@dataclass(frozen=True, slots=True)
class _RuntimeRegistrationRecord:
    authority: _RuntimeRegistrationAuthority = field(repr=False)
    state: _OwnershipState


class _RuntimeValidatedClaim:
    """Opaque proof that the lower registry atomically accepted one claim."""

    __slots__ = ("_generation",)

    def __copy__(self) -> _RuntimeValidatedClaim:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> _RuntimeValidatedClaim:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> object:
        del protocol
        raise TypeError("runtime registration claims cannot be serialized")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise TypeError("runtime registration claims are immutable")

    def __delattr__(self, name: str) -> None:
        del name
        raise TypeError("runtime registration claims are immutable")

    def __repr__(self) -> str:
        return "_RuntimeValidatedClaim(<private>)"

    __str__ = __repr__


_RUNTIME_REGISTRATION_OWNER = object()
_RUNTIME_REGISTRATIONS: dict[object, _RuntimeRegistrationRecord] = {}
_RUNTIME_GENERATION_BY_TARGET_ID: dict[int, object] = {}


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
        try:
            return _return_or_raise_composition(outcome)
        except (KeyboardInterrupt, SystemExit, GeneratorExit) as error:
            error.__context__ = None
            error.__cause__ = None
            error.__suppress_context__ = True
            try:
                raise error from None
            finally:
                error.__context__ = None
                error.__cause__ = None
                error.__suppress_context__ = True


@dataclass(frozen=True, slots=True)
class _SafeCompositionFailure:
    category: str
    message: str


@dataclass(frozen=True, slots=True)
class _SafeBaseExceptionFailure:
    error: BaseException = field(repr=False)


def _compose_isolated(
    composer: OpenAIRuntimeComposerV2,
) -> OpenAIRuntimeCompositionV2 | _SafeCompositionFailure | _SafeBaseExceptionFailure:
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
    try:
        claimed = _claim_factory_handoff(factory_result)
    except BaseException as error:  # noqa: BLE001 - exact process signal is deferred
        del factory_result
        return _SafeBaseExceptionFailure(error)
    del factory_result
    if claimed is None:
        return _SafeCompositionFailure(
            "dependency", "invalid OpenAI SDK factory result"
        )
    if type(claimed) is _SafeCompositionFailure:
        return claimed
    responses_resource, lifecycle = claimed
    deferred_error: BaseException | None = None
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
        try:
            rollback = lifecycle._close_and_sanitize()
        except BaseException as cleanup_error:  # noqa: BLE001 - exact signal preserved
            lease = object.__getattribute__(lifecycle, "_transition_receiver")
            if type(lease) is _OwnershipLease:
                _terminalize_registration(lease)
            del lease
            del lifecycle
            deferred_error = cleanup_error
        else:
            del lifecycle
            if rollback.failed:
                return _SafeCompositionFailure(
                    "lifecycle", "OpenAI runtime rollback failed"
                )
            return _SafeCompositionFailure(
                "dependency", "OpenAI runtime assembly failed"
            )
    except BaseException as construction_error:  # noqa: BLE001 - exact signal deferred
        try:
            rollback = lifecycle._close_and_sanitize()
        except BaseException as cleanup_error:  # noqa: BLE001 - exact signal preserved
            lease = object.__getattribute__(lifecycle, "_transition_receiver")
            if type(lease) is _OwnershipLease:
                _terminalize_registration(lease)
            del lease
            del lifecycle
            deferred_error = cleanup_error
        else:
            del lifecycle
            if rollback.failed:
                return _SafeCompositionFailure(
                    "lifecycle", "OpenAI runtime rollback failed"
                )
            deferred_error = construction_error
    deferred_error.__context__ = None
    deferred_error.__cause__ = None
    deferred_error.__suppress_context__ = True
    deferred_error.__traceback__ = None
    return _SafeBaseExceptionFailure(deferred_error)


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

    generation = object()

    def discard_stale(reference: ReferenceType[object]) -> None:
        current_generation = _RUNTIME_GENERATION_BY_TARGET_ID.get(identity)
        current = _RUNTIME_REGISTRATIONS.get(generation)
        authority = (
            object.__getattribute__(current, "authority")
            if type(current) is _RuntimeRegistrationRecord
            else None
        )
        if (
            reference() is None
            and current_generation is generation
            and type(authority) is _RuntimeRegistrationAuthority
            and object.__getattribute__(authority, "_owner")
            is _RUNTIME_REGISTRATION_OWNER
            and object.__getattribute__(authority, "_generation") is generation
            and object.__getattribute__(authority, "_target_reference") is reference
            and object.__getattribute__(authority, "_callback") is discard_stale
        ):
            compatibility = _OWNERSHIP_TRACKER.get(identity)
            if (
                type(compatibility) is _OwnershipRecord
                and compatibility.client_reference is reference
            ):
                _OWNERSHIP_TRACKER.pop(identity, None)
            _RUNTIME_GENERATION_BY_TARGET_ID.pop(identity, None)
            _RUNTIME_REGISTRATIONS.pop(generation, None)

    tracked_reference = ref(raw_client, discard_stale)
    authority = object.__new__(_RuntimeRegistrationAuthority)
    object.__setattr__(authority, "_callback", discard_stale)
    object.__setattr__(authority, "_generation", generation)
    object.__setattr__(authority, "_owner", _RUNTIME_REGISTRATION_OWNER)
    object.__setattr__(authority, "_target_identity", identity)
    object.__setattr__(authority, "_target_reference", tracked_reference)
    registration = _RuntimeRegistrationRecord(authority, _OwnershipState.LIVE)
    if (
        generation in _RUNTIME_REGISTRATIONS
        or identity in _RUNTIME_GENERATION_BY_TARGET_ID
    ):
        return _SafeCompositionFailure(
            "lifecycle", "OpenAI runtime client is already owned"
        )
    try:
        _RUNTIME_REGISTRATIONS[generation] = registration
        _RUNTIME_GENERATION_BY_TARGET_ID[identity] = generation
        _OWNERSHIP_TRACKER[identity] = _OwnershipRecord(
            tracked_reference, _OwnershipState.LIVE
        )
    except BaseException:
        if _RUNTIME_GENERATION_BY_TARGET_ID.get(identity) is generation:
            _RUNTIME_GENERATION_BY_TARGET_ID.pop(identity, None)
        if _RUNTIME_REGISTRATIONS.get(generation) is registration:
            _RUNTIME_REGISTRATIONS.pop(generation, None)
        compatibility = _OWNERSHIP_TRACKER.get(identity)
        if (
            type(compatibility) is _OwnershipRecord
            and compatibility.client_reference is tracked_reference
        ):
            _OWNERSHIP_TRACKER.pop(identity, None)
        raise
    try:
        lease = _OwnershipLease(identity, tracked_reference, generation)
        lifecycle = _OpenAIRuntimeLifecycleOwnerV2._from_pinned(
            close_function,
            close_receiver,
            _release_ownership_success,
            _mark_ownership_cleanup_failed,
            lease,
        )
    except Exception:  # noqa: BLE001 - construction is an injected boundary
        rollback_failed = not _rollback_unpublished_registration(
            identity=identity,
            generation=generation,
            reference=tracked_reference,
            close_function=close_function,
            close_receiver=close_receiver,
        )
        if rollback_failed:
            return _SafeCompositionFailure(
                "lifecycle", "OpenAI runtime rollback failed"
            )
        return _SafeCompositionFailure("dependency", "OpenAI runtime assembly failed")
    except BaseException:
        rollback_succeeded = _rollback_unpublished_registration(
            identity=identity,
            generation=generation,
            reference=tracked_reference,
            close_function=close_function,
            close_receiver=close_receiver,
        )
        if not rollback_succeeded:
            return _SafeCompositionFailure(
                "lifecycle", "OpenAI runtime rollback failed"
            )
        raise
    return responses_resource, lifecycle


def _rollback_unpublished_registration(
    *,
    identity: int,
    generation: object,
    reference: ReferenceType[object],
    close_function: FunctionType,
    close_receiver: object,
) -> bool:
    """Close an unpublished target and reconcile its exact registration."""

    try:
        close_function(close_receiver)
    except Exception:  # noqa: BLE001 - raw clients share no exception type
        _terminalize_exact_registration(identity, generation, reference)
        return False
    except BaseException as cleanup_error:  # noqa: BLE001 - exact signal preserved
        _terminalize_exact_registration(identity, generation, reference)
        cleanup_error.__context__ = None
        cleanup_error.__cause__ = None
        cleanup_error.__suppress_context__ = True
        try:
            raise cleanup_error from None
        finally:
            cleanup_error.__context__ = None
            cleanup_error.__cause__ = None
            cleanup_error.__suppress_context__ = True
    _discard_exact_registration(identity, generation, reference)
    return True


def _discard_exact_registration(
    identity: int,
    generation: object,
    reference: ReferenceType[object],
) -> None:
    if _RUNTIME_GENERATION_BY_TARGET_ID.get(identity) is generation:
        _RUNTIME_GENERATION_BY_TARGET_ID.pop(identity, None)
    _RUNTIME_REGISTRATIONS.pop(generation, None)
    compatibility = _OWNERSHIP_TRACKER.get(identity)
    if (
        type(compatibility) is _OwnershipRecord
        and compatibility.client_reference is reference
    ):
        _OWNERSHIP_TRACKER.pop(identity, None)


def _terminalize_registration(lease: _OwnershipLease) -> bool:
    generation = lease.generation
    return generation is not None and _terminalize_exact_registration(
        lease.identity, generation, lease.client_reference
    )


def _terminalize_exact_registration(
    identity: int,
    generation: object,
    reference: ReferenceType[object],
) -> bool:
    """Establish an exact no-retry tombstone without invoking cleanup."""

    registration = _RUNTIME_REGISTRATIONS.get(generation)
    compatibility = _OWNERSHIP_TRACKER.get(identity)
    if (
        type(registration) is not _RuntimeRegistrationRecord
        or type(registration.authority) is not _RuntimeRegistrationAuthority
        or _RUNTIME_GENERATION_BY_TARGET_ID.get(identity) is not generation
        or type(compatibility) is not _OwnershipRecord
        or compatibility.client_reference is not reference
    ):
        return False
    authority = registration.authority
    callback = object.__getattribute__(authority, "_callback")
    if (
        object.__getattribute__(authority, "_owner") is not _RUNTIME_REGISTRATION_OWNER
        or object.__getattribute__(authority, "_generation") is not generation
        or object.__getattribute__(authority, "_target_identity") != identity
        or object.__getattribute__(authority, "_target_reference") is not reference
        or type(reference) is not ReferenceType
        or reference.__callback__ is not callback
        or registration.state
        not in {_OwnershipState.LIVE, _OwnershipState.TERMINAL_FAILED}
        or compatibility.state
        not in {_OwnershipState.LIVE, _OwnershipState.TERMINAL_FAILED}
    ):
        return False
    if registration.state is _OwnershipState.LIVE:
        _RUNTIME_REGISTRATIONS[generation] = _RuntimeRegistrationRecord(
            authority, _OwnershipState.TERMINAL_FAILED
        )
    if compatibility.state is _OwnershipState.LIVE:
        _OWNERSHIP_TRACKER[identity] = _OwnershipRecord(
            reference, _OwnershipState.TERMINAL_FAILED
        )
    return True


def _release_ownership_success(lease: _OwnershipLease) -> None:
    current = _OWNERSHIP_TRACKER.get(lease.identity)
    registration = _runtime_registration_for_lease(lease)
    if (
        current is not None
        and current.client_reference is lease.client_reference
        and current.state is _OwnershipState.LIVE
        and registration is not None
        and registration.state in {_OwnershipState.LIVE, _OwnershipState.CLAIMED}
    ):
        _OWNERSHIP_TRACKER.pop(lease.identity, None)
        _RUNTIME_GENERATION_BY_TARGET_ID.pop(lease.identity, None)
        _RUNTIME_REGISTRATIONS.pop(lease.generation, None)


def _mark_ownership_cleanup_failed(lease: _OwnershipLease) -> None:
    current = _OWNERSHIP_TRACKER.get(lease.identity)
    registration = _runtime_registration_for_lease(lease)
    if (
        current is not None
        and current.client_reference is lease.client_reference
        and current.state is _OwnershipState.LIVE
        and registration is not None
        and registration.state in {_OwnershipState.LIVE, _OwnershipState.CLAIMED}
    ):
        _OWNERSHIP_TRACKER[lease.identity] = _OwnershipRecord(
            lease.client_reference, _OwnershipState.TERMINAL_FAILED
        )
        _RUNTIME_REGISTRATIONS[lease.generation] = _RuntimeRegistrationRecord(
            registration.authority, _OwnershipState.TERMINAL_FAILED
        )


def _runtime_registration_for_lease(
    lease: _OwnershipLease,
) -> _RuntimeRegistrationRecord | None:
    generation = lease.generation
    if generation is None:
        return None
    registration = _RUNTIME_REGISTRATIONS.get(generation)
    if type(registration) is not _RuntimeRegistrationRecord:
        return None
    authority = registration.authority
    if type(authority) is not _RuntimeRegistrationAuthority:
        return None
    reference = object.__getattribute__(authority, "_target_reference")
    target = reference() if type(reference) is ReferenceType else None
    if (
        object.__getattribute__(authority, "_owner") is not _RUNTIME_REGISTRATION_OWNER
        or object.__getattribute__(authority, "_generation") is not generation
        or object.__getattribute__(authority, "_target_identity") != lease.identity
        or reference is not lease.client_reference
        or target is None
        or id(target) != lease.identity
        or reference.__callback__ is not object.__getattribute__(authority, "_callback")
        or _RUNTIME_GENERATION_BY_TARGET_ID.get(lease.identity) is not generation
    ):
        return None
    return registration


def _claim_runtime_registration_authority(
    *,
    composition: object,
    expected_sdk_client: object,
) -> _RuntimeValidatedClaim | None:
    """Atomically validate and claim one authentic lower-owned registration."""

    if type(composition) is not OpenAIRuntimeCompositionV2:
        return None
    try:
        from pastila_scout.provider_execution_openai_sdk_v2 import (
            OpenAISDKCapabilityV2,
            OpenAISDKClientV2,
        )
        from pastila_scout.provider_execution_openai_sdk_v2.client import (
            _validated_create_authority,
        )
        from pastila_scout.provider_execution_openai_v2 import (
            OpenAIExecutionConfigV2,
            OpenAIProviderExecutorV2,
        )
        from pastila_scout.provider_execution_openai_v2.executor import (
            _validated_client_authority,
        )

        sdk_client = object.__getattribute__(composition, "sdk_client")
        executor = object.__getattribute__(composition, "executor")
        lifecycle = object.__getattribute__(composition, "_lifecycle")
        if (
            type(sdk_client) is not OpenAISDKClientV2
            or sdk_client is not expected_sdk_client
            or type(executor) is not OpenAIProviderExecutorV2
            or object.__getattribute__(executor, "client") is not sdk_client
            or type(object.__getattribute__(executor, "config"))
            is not OpenAIExecutionConfigV2
            or type(lifecycle) is not _OpenAIRuntimeLifecycleOwnerV2
            or object.__getattribute__(lifecycle, "_closed") is not False
        ):
            return None
        capability = object.__getattribute__(sdk_client, "_sdk_capability")
        if type(capability) is not OpenAISDKCapabilityV2:
            return None
        capability_function = object.__getattribute__(capability, "_function")
        responses = object.__getattribute__(capability, "_receiver")
        capability_authority = _validated_create_authority(responses)
        executor_authority = _validated_client_authority(sdk_client)
        if (
            capability_authority is None
            or capability_authority[0] is not capability_function
            or capability_authority[1] is not responses
            or executor_authority is None
            or object.__getattribute__(executor, "_authorized_function")
            is not executor_authority[0]
            or object.__getattribute__(executor, "_invocation_kind")
            != executor_authority[1]
            or object.__getattribute__(executor, "_receiver")
            is not executor_authority[2]
        ):
            return None
        function = object.__getattribute__(lifecycle, "_function")
        receiver = object.__getattribute__(lifecycle, "_receiver")
        success = object.__getattribute__(lifecycle, "_success_function")
        failure = object.__getattribute__(lifecycle, "_failure_function")
        lease = object.__getattribute__(lifecycle, "_transition_receiver")
        if (
            type(lease) is not _OwnershipLease
            or success is not _release_ownership_success
            or failure is not _mark_ownership_cleanup_failed
            or _static_method_authority(receiver, "close", mode="raw_closer")
            is not function
            or _static_instance_field(receiver, "responses") is not responses
        ):
            return None
        registration = _runtime_registration_for_lease(lease)
        if registration is None or registration.state is not _OwnershipState.LIVE:
            return None
        authority = registration.authority
        reference = object.__getattribute__(authority, "_target_reference")
        callback = object.__getattribute__(authority, "_callback")
        compatibility = _OWNERSHIP_TRACKER.get(lease.identity)
        if (
            type(reference) is not ReferenceType
            or reference() is not receiver
            or reference.__callback__ is not callback
            or type(compatibility) is not _OwnershipRecord
            or compatibility.client_reference is not reference
            or compatibility.state is not _OwnershipState.LIVE
        ):
            return None
        generation = lease.generation
        _RUNTIME_REGISTRATIONS[generation] = _RuntimeRegistrationRecord(
            authority, _OwnershipState.CLAIMED
        )
        claim = object.__new__(_RuntimeValidatedClaim)
        object.__setattr__(claim, "_generation", generation)
        return claim
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def _return_or_raise_composition(
    outcome: (
        OpenAIRuntimeCompositionV2 | _SafeCompositionFailure | _SafeBaseExceptionFailure
    ),
) -> OpenAIRuntimeCompositionV2:
    if type(outcome) is OpenAIRuntimeCompositionV2:
        return outcome
    if type(outcome) is _SafeBaseExceptionFailure:
        error = outcome.error
        del outcome
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True
        error.__traceback__ = None
        try:
            raise error from None
        finally:
            error.__context__ = None
            error.__cause__ = None
            error.__suppress_context__ = True
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

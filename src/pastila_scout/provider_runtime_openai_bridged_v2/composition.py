"""Higher offline composition of verified OpenAI runtime and bridge contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from inspect import signature
from types import FunctionType, MappingProxyType
from typing import Never, Self
from weakref import ReferenceType, ref

from pydantic import ValidationError

from pastila_scout.provider_execution_openai_sdk_bridge_v2 import (
    OpenAIExecutionSDKBridgeClientV2,
)
from pastila_scout.provider_execution_openai_v2 import (
    OpenAIExecutionConfigV2,
    OpenAIProviderExecutorV2,
)
from pastila_scout.provider_runtime_openai_v2 import (
    OpenAIRuntimeComposerV2,
    OpenAIRuntimeCompositionV2,
    OpenAIRuntimeConfigV2,
)
from pastila_scout.provider_runtime_openai_v2.models import (
    _OpenAIRuntimeLifecycleOwnerV2,
)

from .errors import (
    OpenAIBridgedRuntimeConfigurationError,
    OpenAIBridgedRuntimeDependencyError,
    OpenAIBridgedRuntimeLifecycleError,
)
from .models import _SafeAssemblyFailure

_CONFIGURATION_MESSAGE = "invalid OpenAI bridged runtime configuration"
_DEPENDENCY_MESSAGE = "OpenAI bridged runtime dependency failure"
_LIFECYCLE_MESSAGE = "OpenAI bridged runtime lifecycle failure"
_COMPOSER_SERIALIZATION_MESSAGE = (
    "OpenAI bridged runtime composers cannot be serialized"
)
_COMPOSITION_SERIALIZATION_MESSAGE = (
    "OpenAI bridged runtime compositions cannot be serialized"
)
_TRUSTED_BASE_COMPOSE = type.__getattribute__(OpenAIRuntimeComposerV2, "__dict__")[
    "compose"
]
_TRUSTED_BASE_CLOSE = type.__getattribute__(OpenAIRuntimeCompositionV2, "__dict__")[
    "close"
]

if type(_TRUSTED_BASE_COMPOSE) is not FunctionType:
    raise TypeError("invalid trusted OpenAI runtime compose authority")
if type(_TRUSTED_BASE_CLOSE) is not FunctionType:
    raise TypeError("invalid trusted OpenAI runtime close authority")

_RESERVATION = object()
_LIVE_WRAPPERS: dict[int, object] = {}


class OpenAIBridgedRuntimeComposerV2:
    """Pinned higher composer over one exact verified base composer."""

    __slots__ = ("_base_compose_function", "_base_runtime_composer")

    def __init__(self, base_runtime_composer: object) -> None:
        if not _base_composer_is_valid(base_runtime_composer):
            del base_runtime_composer
            del self
            _raise_configuration_error()
        object.__setattr__(self, "_base_compose_function", _TRUSTED_BASE_COMPOSE)
        object.__setattr__(self, "_base_runtime_composer", base_runtime_composer)

    def compose(self) -> OpenAIBridgedRuntimeCompositionV2:
        """Compose one bridged runtime without executing a provider request."""

        function = object.__getattribute__(self, "_base_compose_function")
        receiver = object.__getattribute__(self, "_base_runtime_composer")
        del self
        outcome = _compose_isolated(function, receiver)
        del function
        del receiver
        return _return_or_raise_assembly(outcome)

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce__(self) -> Never:
        del self
        _raise_serialization_error(_COMPOSER_SERIALIZATION_MESSAGE)

    def __reduce_ex__(self, protocol: int) -> Never:
        del protocol
        del self
        _raise_serialization_error(_COMPOSER_SERIALIZATION_MESSAGE)

    def __getstate__(self) -> Never:
        del self
        _raise_serialization_error(_COMPOSER_SERIALIZATION_MESSAGE)

    def __setstate__(self, state: object) -> Never:
        del state
        del self
        _raise_serialization_error(_COMPOSER_SERIALIZATION_MESSAGE)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value, self
        _raise_frozen_error("OpenAI bridged runtime composers are immutable")

    def __delattr__(self, name: str) -> None:
        del name, self
        _raise_frozen_error("OpenAI bridged runtime composers are immutable")

    def __repr__(self) -> str:
        return "OpenAIBridgedRuntimeComposerV2()"

    __str__ = __repr__


class OpenAIBridgedRuntimeCompositionV2:
    """One executor with lifecycle delegated to an exact base composition."""

    __slots__ = (
        "__weakref__",
        "_base_close_function",
        "_base_composition",
        "_closed",
        "_tracker_identity",
        "executor",
    )

    def __init__(self, executor: object = None) -> None:
        del executor, self
        _raise_configuration_error()

    @property
    def closed(self) -> bool:
        return object.__getattribute__(self, "_closed")

    def close(self) -> None:
        """Delegate cleanup to the exact base composition at most once."""

        if object.__getattribute__(self, "_closed"):
            return
        object.__setattr__(self, "_closed", True)
        function = object.__getattribute__(self, "_base_close_function")
        base = object.__getattribute__(self, "_base_composition")
        identity = object.__getattribute__(self, "_tracker_identity")
        object.__setattr__(self, "_base_close_function", None)
        object.__setattr__(self, "_base_composition", None)
        try:
            failed = not _close_base_isolated(function, base)
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            _release_wrapper(identity, self)
            del identity, function, base, self
            raise
        _release_wrapper(identity, self)
        del identity, function, base, self
        if failed:
            _raise_lifecycle_error()
        return

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce__(self) -> Never:
        del self
        _raise_serialization_error(_COMPOSITION_SERIALIZATION_MESSAGE)

    def __reduce_ex__(self, protocol: int) -> Never:
        del protocol
        del self
        _raise_serialization_error(_COMPOSITION_SERIALIZATION_MESSAGE)

    def __getstate__(self) -> Never:
        del self
        _raise_serialization_error(_COMPOSITION_SERIALIZATION_MESSAGE)

    def __setstate__(self, state: object) -> Never:
        del state, self
        _raise_serialization_error(_COMPOSITION_SERIALIZATION_MESSAGE)

    def __setattr__(self, name: str, value: object) -> None:
        del name, value, self
        _raise_frozen_error("OpenAI bridged runtime compositions are immutable")

    def __delattr__(self, name: str) -> None:
        del name, self
        _raise_frozen_error("OpenAI bridged runtime compositions are immutable")

    def __repr__(self) -> str:
        return (
            "OpenAIBridgedRuntimeCompositionV2("
            "executor=<OpenAIProviderExecutorV2>, "
            f"closed={self.closed})"
        )

    __str__ = __repr__


def _compose_isolated(
    function: FunctionType, receiver: object
) -> OpenAIBridgedRuntimeCompositionV2 | _SafeAssemblyFailure:
    runtime_config = _reconstruct_runtime_config(receiver)
    if runtime_config is None:
        del function, receiver
        return _SafeAssemblyFailure("dependency")
    try:
        base = function(receiver)
    except Exception:  # noqa: BLE001 - verified lower boundary owns diagnostics
        del function, receiver
        return _SafeAssemblyFailure("dependency")
    except BaseException:
        del function, receiver
        raise
    del function, receiver
    validated = _validate_base_composition(base, runtime_config)
    del runtime_config
    if validated is None:
        del base
        return _SafeAssemblyFailure("dependency")
    sdk_client, config = validated
    identity = id(base)
    if not _reserve_wrapper(identity):
        del identity, sdk_client, config, base
        return _SafeAssemblyFailure("duplicate")
    try:
        from pastila_scout.provider_execution_openai_sdk_bridge_v2.bootstrap import (
            _bootstrap_bridge,
        )

        bridge = _bootstrap_bridge(sdk_client)
        del sdk_client
        executor = OpenAIProviderExecutorV2(client=bridge, config=config)
        del config
        if (
            type(bridge) is not OpenAIExecutionSDKBridgeClientV2
            or type(executor) is not OpenAIProviderExecutorV2
            or object.__getattribute__(executor, "client") is not bridge
            or object.__getattribute__(bridge, "_sdk_client")
            is not object.__getattribute__(base, "sdk_client")
        ):
            raise TypeError
        result = object.__new__(OpenAIBridgedRuntimeCompositionV2)
        object.__setattr__(result, "executor", executor)
        object.__setattr__(result, "_base_composition", base)
        object.__setattr__(result, "_base_close_function", _TRUSTED_BASE_CLOSE)
        object.__setattr__(result, "_tracker_identity", identity)
        object.__setattr__(result, "_closed", False)
        _activate_wrapper(identity, result)
        return result
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        try:
            _rollback_base(base)
        finally:
            _release_reservation(identity)
            del identity, base
        raise
    except Exception:  # noqa: BLE001 - assembly failures are fixed outcomes
        rollback = _rollback_base(base)
        _release_reservation(identity)
        del identity, base
        if not rollback:
            return _SafeAssemblyFailure("lifecycle")
        return _SafeAssemblyFailure("dependency")


def _validate_base_composition(
    value: object,
    runtime_config: OpenAIRuntimeConfigV2,
) -> tuple[object, OpenAIExecutionConfigV2] | None:
    if type(value) is not OpenAIRuntimeCompositionV2:
        return None
    try:
        from pastila_scout.provider_execution_openai_sdk_v2 import (
            OpenAISDKCapabilityV2,
            OpenAISDKClientV2,
        )
        from pastila_scout.provider_execution_openai_sdk_v2.client import (
            _validated_create_authority,
        )
        from pastila_scout.provider_execution_openai_v2.executor import (
            _validated_client_authority,
        )
        from pastila_scout.provider_runtime_openai_v2 import composition as base_runtime

        sdk_client = object.__getattribute__(value, "sdk_client")
        executor = object.__getattribute__(value, "executor")
        lifecycle = object.__getattribute__(value, "_lifecycle")
        if type(lifecycle) is not _OpenAIRuntimeLifecycleOwnerV2:
            return None
        if object.__getattribute__(lifecycle, "_closed") is not False:
            return None
        if type(sdk_client) is not OpenAISDKClientV2:
            return None
        capability = object.__getattribute__(sdk_client, "_sdk_capability")
        if type(capability) is not OpenAISDKCapabilityV2:
            return None
        capability_function = object.__getattribute__(capability, "_function")
        capability_receiver = object.__getattribute__(capability, "_receiver")
        capability_retries = object.__getattribute__(capability, "max_retries")
        if type(capability_retries) is not int or capability_retries != 0:
            return None
        capability_authority = _validated_create_authority(capability_receiver)
        if (
            capability_authority is None
            or capability_authority[0] is not capability_function
            or capability_authority[1] is not capability_receiver
        ):
            return None
        if type(executor) is not OpenAIProviderExecutorV2:
            return None
        if object.__getattribute__(executor, "client") is not sdk_client:
            return None
        executor_authority = _validated_client_authority(sdk_client)
        if executor_authority is None:
            return None
        if (
            object.__getattribute__(executor, "_authorized_function")
            is not executor_authority[0]
            or object.__getattribute__(executor, "_invocation_kind")
            != executor_authority[1]
            or object.__getattribute__(executor, "_receiver")
            is not executor_authority[2]
        ):
            return None
        config = object.__getattribute__(executor, "config")
        if type(config) is not OpenAIExecutionConfigV2:
            return None
        if not _execution_config_fields_are_exact(config):
            return None
        dumped = OpenAIExecutionConfigV2.model_dump(
            config, mode="python", warnings="error"
        )
        reconstructed = OpenAIExecutionConfigV2.model_validate(dumped, strict=True)
        if (
            type(reconstructed) is not OpenAIExecutionConfigV2
            or reconstructed.model != runtime_config.model
            or reconstructed.model != object.__getattribute__(config, "model")
            or reconstructed.temperature
            != object.__getattribute__(config, "temperature")
            or reconstructed.max_output_tokens
            != object.__getattribute__(config, "max_output_tokens")
            or reconstructed.stop_sequences
            != object.__getattribute__(config, "stop_sequences")
        ):
            return None
        cleanup_function = object.__getattribute__(lifecycle, "_function")
        cleanup_receiver = object.__getattribute__(lifecycle, "_receiver")
        success_function = object.__getattribute__(lifecycle, "_success_function")
        failure_function = object.__getattribute__(lifecycle, "_failure_function")
        lease = object.__getattribute__(lifecycle, "_transition_receiver")
        if (
            type(lease) is not base_runtime._OwnershipLease
            or type(object.__getattribute__(lease, "identity")) is not int
            or object.__getattribute__(lease, "identity") != id(cleanup_receiver)
            or type(object.__getattribute__(lease, "client_reference"))
            is not ReferenceType
            or object.__getattribute__(lease, "client_reference")()
            is not cleanup_receiver
            or success_function is not base_runtime._release_ownership_success
            or failure_function is not base_runtime._mark_ownership_cleanup_failed
            or base_runtime._static_method_authority(
                cleanup_receiver, "close", mode="raw_closer"
            )
            is not cleanup_function
            or base_runtime._static_instance_field(cleanup_receiver, "responses")
            is not capability_receiver
        ):
            return None
        ownership_record = base_runtime._OWNERSHIP_TRACKER.get(id(cleanup_receiver))
        if (
            type(ownership_record) is not base_runtime._OwnershipRecord
            or object.__getattribute__(ownership_record, "client_reference")
            is not object.__getattribute__(lease, "client_reference")
            or object.__getattribute__(ownership_record, "state")
            is not base_runtime._OwnershipState.LIVE
        ):
            return None
        current_close = type.__getattribute__(
            OpenAIRuntimeCompositionV2, "__dict__"
        ).get("close")
        if current_close is not _TRUSTED_BASE_CLOSE:
            return None
        return sdk_client, reconstructed
    except (AttributeError, KeyError, TypeError, ValueError, ValidationError):
        return None


def _reconstruct_runtime_config(value: object) -> OpenAIRuntimeConfigV2 | None:
    try:
        config = object.__getattribute__(value, "config")
        if type(config) is not OpenAIRuntimeConfigV2:
            return None
        dumped = OpenAIRuntimeConfigV2.model_dump(
            config, mode="python", warnings="error"
        )
        reconstructed = OpenAIRuntimeConfigV2.model_validate(dumped, strict=True)
        if type(reconstructed) is not OpenAIRuntimeConfigV2:
            return None
        return reconstructed
    except (AttributeError, TypeError, ValueError, ValidationError):
        return None


def _execution_config_fields_are_exact(config: OpenAIExecutionConfigV2) -> bool:
    model = object.__getattribute__(config, "model")
    temperature = object.__getattribute__(config, "temperature")
    max_output_tokens = object.__getattribute__(config, "max_output_tokens")
    stop_sequences = object.__getattribute__(config, "stop_sequences")
    return (
        type(model) is str
        and (temperature is None or type(temperature) in {int, float})
        and (max_output_tokens is None or type(max_output_tokens) is int)
        and type(stop_sequences) is tuple
        and all(type(item) is str for item in stop_sequences)
    )


def _base_composer_is_valid(value: object) -> bool:
    if type(value) is not OpenAIRuntimeComposerV2:
        return False
    try:
        namespace = type.__getattribute__(OpenAIRuntimeComposerV2, "__dict__")
        if type(namespace) is not MappingProxyType:
            return False
        function = namespace.get("compose")
        if type(function) is not FunctionType or function is not _TRUSTED_BASE_COMPOSE:
            return False
        clone = FunctionType(
            function.__code__,
            function.__globals__,
            function.__name__,
            function.__defaults__,
            function.__closure__,
        )
        clone.__kwdefaults__ = function.__kwdefaults__
        signature(clone, follow_wrapped=False).bind(value)
    except (AttributeError, KeyError, TypeError, ValueError):
        return False
    return True


def _reserve_wrapper(identity: int) -> bool:
    current = _LIVE_WRAPPERS.get(identity)
    if type(current) is ReferenceType and current() is None:
        _LIVE_WRAPPERS.pop(identity, None)
        current = None
    if current is not None:
        return False
    _LIVE_WRAPPERS[identity] = _RESERVATION
    return True


def _activate_wrapper(
    identity: int, composition: OpenAIBridgedRuntimeCompositionV2
) -> None:
    if _LIVE_WRAPPERS.get(identity) is not _RESERVATION:
        raise TypeError

    def discard(reference: ReferenceType[object]) -> None:
        if _LIVE_WRAPPERS.get(identity) is reference:
            _LIVE_WRAPPERS.pop(identity, None)

    _LIVE_WRAPPERS[identity] = ref(composition, discard)


def _release_reservation(identity: int) -> None:
    if _LIVE_WRAPPERS.get(identity) is _RESERVATION:
        _LIVE_WRAPPERS.pop(identity, None)


def _release_wrapper(
    identity: int, composition: OpenAIBridgedRuntimeCompositionV2
) -> None:
    current = _LIVE_WRAPPERS.get(identity)
    if type(current) is ReferenceType and current() is composition:
        _LIVE_WRAPPERS.pop(identity, None)


def _rollback_base(base: OpenAIRuntimeCompositionV2) -> bool:
    return _close_base_isolated(_TRUSTED_BASE_CLOSE, base)


def _close_base_isolated(function: object, base: object) -> bool:
    try:
        function(base)
    except Exception:  # noqa: BLE001 - lower cleanup diagnostics remain private
        return False
    return True


def _return_or_raise_assembly(
    outcome: OpenAIBridgedRuntimeCompositionV2 | _SafeAssemblyFailure,
) -> OpenAIBridgedRuntimeCompositionV2:
    if type(outcome) is OpenAIBridgedRuntimeCompositionV2:
        return outcome
    category = outcome.category
    del outcome
    if category == "lifecycle":
        _raise_lifecycle_error()
    _raise_dependency_error()


def _raise_configuration_error() -> Never:
    _raise_fixed(OpenAIBridgedRuntimeConfigurationError, _CONFIGURATION_MESSAGE)


def _raise_dependency_error() -> Never:
    _raise_fixed(OpenAIBridgedRuntimeDependencyError, _DEPENDENCY_MESSAGE)


def _raise_lifecycle_error() -> Never:
    _raise_fixed(OpenAIBridgedRuntimeLifecycleError, _LIFECYCLE_MESSAGE)


def _raise_fixed(error_type: type[Exception], message: str) -> Never:
    error = error_type(message)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_serialization_error(message: str) -> Never:
    error = TypeError(message)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_frozen_error(message: str) -> Never:
    error = FrozenInstanceError(message)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


__all__ = (
    "OpenAIBridgedRuntimeComposerV2",
    "OpenAIBridgedRuntimeCompositionV2",
)

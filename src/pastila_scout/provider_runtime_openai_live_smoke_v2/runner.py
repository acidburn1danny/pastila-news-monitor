"""Offline orchestration across the complete verified OpenAI execution chain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from importlib import import_module
from types import FunctionType, MappingProxyType
from typing import Never, Self

from pydantic import ValidationError

from pastila_scout.provider_execution_openai_sdk_bridge_v2 import (
    OpenAIExecutionSDKBridgeClientV2,
)
from pastila_scout.provider_execution_openai_v2 import (
    OpenAIExecutionConfigV2,
    OpenAIProviderExecutorV2,
)
from pastila_scout.provider_execution_openai_v2.executor import (
    _validated_client_authority,
)
from pastila_scout.provider_execution_v2 import (
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_runtime_openai_v2 import (
    OpenAIRuntimeComposerV2,
    OpenAIRuntimeCompositionV2,
    OpenAIRuntimeConfigV2,
)
from pastila_scout.provider_smoke_request_authority_v2 import (
    SmokeExecutionPlanV2,
    SmokeProviderExecutionRequestAuthorityV2,
    build_canonical_smoke_execution_plan,
)
from pastila_scout.provider_v2 import (
    ProviderFinishReasonV2,
    ProviderResultStatusV2,
)

from .errors import (
    OpenAILiveSmokeConfigurationError,
    OpenAILiveSmokeDependencyError,
    OpenAILiveSmokeLifecycleError,
)
from .models import OpenAILiveSmokeConfigurationV2, OpenAILiveSmokeResultV2

_BRIDGED_RUNTIME = import_module("pastila_scout.provider_runtime_openai_" "bridged_v2")
_BRIDGED_COMPOSITION = import_module(
    "pastila_scout.provider_runtime_openai_" "bridged_v2.composition"
)
OpenAIBridgedRuntimeComposerV2 = _BRIDGED_RUNTIME.OpenAIBridgedRuntimeComposerV2
OpenAIBridgedRuntimeCompositionV2 = _BRIDGED_RUNTIME.OpenAIBridgedRuntimeCompositionV2

_CONFIGURATION_MESSAGE = "invalid OpenAI live smoke configuration"
_CONFIRMATION_MESSAGE = (
    "explicit offline OpenAI smoke execution confirmation is required"
)
_DEPENDENCY_MESSAGE = "OpenAI live smoke dependency failure"
_LIFECYCLE_MESSAGE = "OpenAI live smoke lifecycle failure"
_SERIALIZATION_MESSAGE = "OpenAI live smoke runners cannot be serialized"
_EXPECTED_TEXT = "SMOKE_OK"

_TRUSTED_BUILD_PLAN = build_canonical_smoke_execution_plan
_TRUSTED_COMPOSE = type.__getattribute__(OpenAIBridgedRuntimeComposerV2, "__dict__")[
    "compose"
]
_TRUSTED_CONSTRUCT = type.__getattribute__(
    SmokeProviderExecutionRequestAuthorityV2, "__dict__"
)["construct"]
_TRUSTED_EXECUTE = type.__getattribute__(OpenAIProviderExecutorV2, "__dict__")[
    "execute"
]
_TRUSTED_BRIDGE_COMPLETE = type.__getattribute__(
    OpenAIExecutionSDKBridgeClientV2, "__dict__"
)["complete"]
_TRUSTED_CLOSE = type.__getattribute__(OpenAIBridgedRuntimeCompositionV2, "__dict__")[
    "close"
]
_TRUSTED_CLAIM = _BRIDGED_COMPOSITION._claim_bridged_registration_authority
_TRUSTED_CLAIM_TYPE = _BRIDGED_COMPOSITION._BridgedValidatedClaim

if not all(
    type(item) is FunctionType
    for item in (
        _TRUSTED_BUILD_PLAN,
        _TRUSTED_COMPOSE,
        _TRUSTED_CONSTRUCT,
        _TRUSTED_EXECUTE,
        _TRUSTED_BRIDGE_COMPLETE,
        _TRUSTED_CLOSE,
        _TRUSTED_CLAIM,
    )
):
    raise TypeError("invalid trusted OpenAI live smoke callable authority")


class _OutcomeCategory(Enum):
    SUCCESS = auto()
    INVALID = auto()
    UNCONFIRMED = auto()
    DEPENDENCY = auto()
    LIFECYCLE = auto()
    BASE_EXCEPTION = auto()


@dataclass(frozen=True, slots=True)
class _SafeOutcome:
    category: _OutcomeCategory
    value: object = None


class OpenAILiveSmokeRunnerV2:
    """Immutable holder of exact verified request and runtime authorities."""

    __slots__ = (
        "_claim_function",
        "_claim_type",
        "_compose_receiver",
        "_request_receiver",
        "_runtime_model",
    )

    def __init__(
        self,
        bridged_runtime_composer: OpenAIBridgedRuntimeComposerV2,
        request_authority: SmokeProviderExecutionRequestAuthorityV2,
    ) -> None:
        claim_authority = _claim_authority()
        runtime_model = _producing_runtime_model(bridged_runtime_composer)
        if (
            not _dependencies_are_exact(bridged_runtime_composer, request_authority)
            or claim_authority is None
            or runtime_model is None
        ):
            del bridged_runtime_composer, request_authority, self
            _raise_dependency_error()
        claim_function, claim_type = claim_authority
        object.__setattr__(self, "_claim_function", claim_function)
        object.__setattr__(self, "_claim_type", claim_type)
        object.__setattr__(self, "_compose_receiver", bridged_runtime_composer)
        object.__setattr__(self, "_request_receiver", request_authority)
        object.__setattr__(self, "_runtime_model", runtime_model)

    def run(
        self, configuration: OpenAILiveSmokeConfigurationV2
    ) -> OpenAILiveSmokeResultV2:
        """Run the complete live-shaped execution path entirely offline."""

        composer = object.__getattribute__(self, "_compose_receiver")
        authority = object.__getattribute__(self, "_request_receiver")
        claim_function = object.__getattribute__(self, "_claim_function")
        claim_type = object.__getattribute__(self, "_claim_type")
        runtime_model = object.__getattribute__(self, "_runtime_model")
        del self
        outcome = _execute_isolated(
            configuration,
            composer,
            authority,
            claim_function,
            claim_type,
            runtime_model,
        )
        del (
            configuration,
            composer,
            authority,
            claim_function,
            claim_type,
            runtime_model,
        )
        return _return_or_raise(outcome)

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce__(self) -> Never:
        del self
        _raise_serialization_error()

    def __reduce_ex__(self, protocol: int) -> Never:
        del protocol, self
        _raise_serialization_error()

    def __getstate__(self) -> Never:
        del self
        _raise_serialization_error()

    def __setstate__(self, state: object) -> Never:
        del state, self
        _raise_serialization_error()

    def __setattr__(self, name: str, value: object) -> Never:
        del name, value, self
        _raise_frozen_error()

    def __delattr__(self, name: str) -> Never:
        del name, self
        _raise_frozen_error()

    def __repr__(self) -> str:
        return "OpenAILiveSmokeRunnerV2()"

    __str__ = __repr__


def _dependencies_are_exact(composer: object, authority: object) -> bool:
    if (
        type(composer) is not OpenAIBridgedRuntimeComposerV2
        or type(authority) is not SmokeProviderExecutionRequestAuthorityV2
    ):
        return False
    try:
        composer_namespace = type.__getattribute__(
            OpenAIBridgedRuntimeComposerV2, "__dict__"
        )
        authority_namespace = type.__getattribute__(
            SmokeProviderExecutionRequestAuthorityV2, "__dict__"
        )
        return (
            type(composer_namespace) is MappingProxyType
            and type(authority_namespace) is MappingProxyType
            and composer_namespace.get("compose") is _TRUSTED_COMPOSE
            and authority_namespace.get("construct") is _TRUSTED_CONSTRUCT
            and type.__getattribute__(OpenAIProviderExecutorV2, "__dict__").get(
                "execute"
            )
            is _TRUSTED_EXECUTE
            and type.__getattribute__(OpenAIExecutionSDKBridgeClientV2, "__dict__").get(
                "complete"
            )
            is _TRUSTED_BRIDGE_COMPLETE
            and type.__getattribute__(
                OpenAIBridgedRuntimeCompositionV2, "__dict__"
            ).get("close")
            is _TRUSTED_CLOSE
        )
    except (AttributeError, TypeError):
        return False


def _claim_authority(
    _original_function: FunctionType = _TRUSTED_CLAIM,
    _original_type: type = _TRUSTED_CLAIM_TYPE,
) -> tuple[FunctionType, type] | None:
    """Return the clean-import claim authority only while local roots agree."""

    if (
        type(_original_function) is not FunctionType
        or type(_original_type) is not type
        or _TRUSTED_CLAIM is not _original_function
        or _TRUSTED_CLAIM_TYPE is not _original_type
    ):
        return None
    try:
        if (
            _BRIDGED_COMPOSITION._claim_bridged_registration_authority
            is not _original_function
            or _BRIDGED_COMPOSITION._BridgedValidatedClaim is not _original_type
        ):
            return None
    except (AttributeError, TypeError):
        return None
    return _original_function, _original_type


def _producing_runtime_model(composer: object) -> str | None:
    """Capture the model from the exact runtime composer that will produce runs."""

    if type(composer) is not OpenAIBridgedRuntimeComposerV2:
        return None
    try:
        base_composer = object.__getattribute__(composer, "_base_runtime_composer")
        if type(base_composer) is not OpenAIRuntimeComposerV2:
            return None
        config = object.__getattribute__(base_composer, "config")
        if type(config) is not OpenAIRuntimeConfigV2:
            return None
        payload = OpenAIRuntimeConfigV2.model_dump(
            config, mode="python", warnings="error"
        )
        rebuilt = OpenAIRuntimeConfigV2.model_validate(payload, strict=True)
        model = object.__getattribute__(rebuilt, "model")
        if type(model) is not str or not model or model != model.strip():
            return None
        return model
    except (AttributeError, TypeError, ValueError, ValidationError):
        return None


def _reconstruct_configuration(value: object) -> OpenAILiveSmokeConfigurationV2 | None:
    try:
        if type(value) is not OpenAILiveSmokeConfigurationV2:
            return None
        payload = OpenAILiveSmokeConfigurationV2.model_dump(
            value, mode="python", warnings="error"
        )
        rebuilt = OpenAILiveSmokeConfigurationV2.model_validate(payload, strict=True)
        if type(rebuilt) is not OpenAILiveSmokeConfigurationV2:
            return None
        return rebuilt
    except (AttributeError, TypeError, ValueError, ValidationError):
        return None


def _execute_isolated(
    configuration: object,
    composer: OpenAIBridgedRuntimeComposerV2,
    authority: SmokeProviderExecutionRequestAuthorityV2,
    claim_function: FunctionType,
    claim_type: type,
    runtime_model: str,
) -> _SafeOutcome:
    config = _reconstruct_configuration(configuration)
    del configuration
    if config is None:
        del composer, authority
        return _SafeOutcome(_OutcomeCategory.INVALID)
    if config.confirm_live is not True:
        del config, composer, authority
        return _SafeOutcome(_OutcomeCategory.UNCONFIRMED)
    try:
        plan = _TRUSTED_BUILD_PLAN()
        request = _TRUSTED_CONSTRUCT(
            authority,
            execution_plan=plan,
            execution_request_id=config.request_id,
            requested_at=config.requested_at,
            timeout_seconds=config.timeout_seconds,
        )
    except Exception:  # noqa: BLE001 - lower diagnostics are private
        del config, composer, authority
        return _SafeOutcome(_OutcomeCategory.DEPENDENCY)
    except BaseException as error:  # noqa: BLE001 - preserve control-flow identity
        del config, composer, authority
        return _base_exception_outcome(error)
    del authority
    request = _validated_request(request, plan, config)
    del plan, config
    if request is None:
        del composer
        return _SafeOutcome(_OutcomeCategory.DEPENDENCY)
    try:
        composition = _TRUSTED_COMPOSE(composer)
    except Exception:  # noqa: BLE001 - lower diagnostics are private
        del request, composer
        return _SafeOutcome(_OutcomeCategory.DEPENDENCY)
    except BaseException as error:  # noqa: BLE001 - preserve control-flow identity
        del request, composer
        return _base_exception_outcome(error)
    del composer
    if not _composition_is_exact(composition, runtime_model):
        del request, composition
        return _SafeOutcome(_OutcomeCategory.DEPENDENCY)
    executor = object.__getattribute__(composition, "executor")
    claim = claim_function(composition=composition, expected_executor=executor)
    del executor
    if type(claim) is not claim_type:
        del request, composition
        return _SafeOutcome(_OutcomeCategory.DEPENDENCY)
    del claim
    return _execute_and_close(request, composition)


def _validated_request(
    value: object,
    plan: SmokeExecutionPlanV2,
    config: OpenAILiveSmokeConfigurationV2,
) -> ProviderExecutionRequestV2 | None:
    if type(value) is not ProviderExecutionRequestV2:
        return None
    try:
        rebuilt = ProviderExecutionRequestV2.model_validate(
            value.model_dump(mode="python", warnings="error"), strict=True
        )
        intent = rebuilt.request_intent
        units = intent.request_units
        messages = units[0].messages if len(units) == 1 else ()
        context = rebuilt.context
        timeout = rebuilt.timeout_policy.timeout_seconds
        if (
            rebuilt.provider.provider_id != "openai"
            or intent.execution_plan_reference != plan.plan_reference
            or intent.execution_plan_identity != plan.plan_identity
            or intent.execution_plan_fingerprint != plan.plan_fingerprint
            or intent.draft_reference != plan.draft_reference
            or intent.draft_fingerprint != plan.draft_fingerprint
            or len(messages) != 1
            or messages[0].role != "generation"
            or messages[0].content != plan.request_units[0].messages[0].content
            or messages[0].ordinal != 0
            or context.request_id != config.request_id
            or context.requested_at != config.requested_at
            or context.requested_at.tzinfo is not config.requested_at.tzinfo
            or context.cancellation.cancellation_requested is not False
            or context.metadata != ()
            or type(timeout) is not type(config.timeout_seconds)
            or timeout != config.timeout_seconds
        ):
            return None
        return rebuilt
    except (AttributeError, IndexError, TypeError, ValueError, ValidationError):
        return None


def _composition_is_exact(value: object, runtime_model: str) -> bool:
    if type(value) is not OpenAIBridgedRuntimeCompositionV2:
        return False
    try:
        if object.__getattribute__(value, "_closed") is not False:
            return False
        executor = object.__getattribute__(value, "executor")
        if type(executor) is not OpenAIProviderExecutorV2:
            return False
        bridge = object.__getattribute__(executor, "client")
        if type(bridge) is not OpenAIExecutionSDKBridgeClientV2:
            return False
        authority = _validated_client_authority(bridge)
        if authority is None:
            return False
        function, invocation_kind, receiver = authority
        if (
            function is not _TRUSTED_BRIDGE_COMPLETE
            or invocation_kind != "instance"
            or receiver is not bridge
            or object.__getattribute__(executor, "_authorized_function") is not function
            or object.__getattribute__(executor, "_invocation_kind") != invocation_kind
            or object.__getattribute__(executor, "_receiver") is not bridge
        ):
            return False
        if not _execution_config_is_exact(object.__getattribute__(executor, "config")):
            return False
        config = object.__getattribute__(executor, "config")
        return (
            _bridge_authority(bridge) is not None
            and _execution_config_is_exact(config)
            and _runtime_model_is_coherent(value, config, runtime_model)
        )
    except (AttributeError, ImportError, KeyError, TypeError, ValueError):
        return False


def _execution_config_is_exact(value: object) -> bool:
    if type(value) is not OpenAIExecutionConfigV2:
        return False
    try:
        model = object.__getattribute__(value, "model")
        temperature = object.__getattribute__(value, "temperature")
        token_limit = object.__getattribute__(value, "max_output_tokens")
        stops = object.__getattribute__(value, "stop_sequences")
        if (
            type(model) is not str
            or (temperature is not None and type(temperature) not in {int, float})
            or (token_limit is not None and type(token_limit) is not int)
            or type(stops) is not tuple
            or any(type(item) is not str for item in stops)
        ):
            return False
        payload = OpenAIExecutionConfigV2.model_dump(
            value, mode="python", warnings="error"
        )
        rebuilt = OpenAIExecutionConfigV2.model_validate(payload, strict=True)
        return (
            type(rebuilt) is OpenAIExecutionConfigV2
            and rebuilt.model == model
            and type(rebuilt.model) is type(model)
            and rebuilt.temperature == temperature
            and type(rebuilt.temperature) is type(temperature)
            and rebuilt.max_output_tokens == token_limit
            and type(rebuilt.max_output_tokens) is type(token_limit)
            and rebuilt.stop_sequences == stops
            and type(rebuilt.stop_sequences) is type(stops)
        )
    except (AttributeError, TypeError, ValueError, ValidationError):
        return False


def _runtime_model_is_coherent(
    composition: OpenAIBridgedRuntimeCompositionV2,
    execution_config: OpenAIExecutionConfigV2,
    producing_runtime_model: str,
) -> bool:
    """Compare only the model owned by both runtime and execution contracts."""

    try:
        base = object.__getattribute__(composition, "_base_composition")
        if type(base) is not OpenAIRuntimeCompositionV2:
            return False
        base_executor = object.__getattribute__(base, "executor")
        if type(base_executor) is not OpenAIProviderExecutorV2:
            return False
        runtime_execution_config = object.__getattribute__(base_executor, "config")
        if not _execution_config_is_exact(runtime_execution_config):
            return False
        runtime_model = object.__getattribute__(runtime_execution_config, "model")
        execution_model = object.__getattribute__(execution_config, "model")
        return (
            type(producing_runtime_model) is str
            and type(runtime_model) is str
            and type(execution_model) is str
            and producing_runtime_model == runtime_model == execution_model
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _bridge_authority(bridge: OpenAIExecutionSDKBridgeClientV2) -> object | None:
    """Validate the operational bridge generation without invoking it."""

    try:
        from pastila_scout.provider_execution_openai_sdk_bridge_v2 import bootstrap

        generation = bootstrap._resolve_authority_generation()
        trusted = bootstrap._AUTHORITY_GENERATION
        sdk_client = object.__getattribute__(bridge, "_sdk_client")
        if (
            trusted is None
            or not bootstrap._generation_is_identical(generation, trusted)
            or not bootstrap._sdk_authority_is_valid(sdk_client, generation)
            or object.__getattribute__(bridge, "_complete_function")
            is not generation.complete_function
            or object.__getattribute__(bridge, "_mapper_function")
            is not generation.mapper_function
            or object.__getattribute__(bridge, "_sdk_request_type")
            is not generation.request_type
        ):
            return None
        return sdk_client
    except (AttributeError, ImportError, KeyError, TypeError, ValueError):
        return None


def _execute_and_close(
    request: ProviderExecutionRequestV2,
    composition: OpenAIBridgedRuntimeCompositionV2,
) -> _SafeOutcome:
    executor = object.__getattribute__(composition, "executor")
    execution_error: BaseException | None = None
    result: object = None
    try:
        result = _TRUSTED_EXECUTE(executor, request)
    except BaseException as error:  # noqa: BLE001 - control-flow policy is explicit
        execution_error = error
    valid_text = (
        _validated_result_text(result, request) if execution_error is None else None
    )
    del result, executor, request
    cleanup_error: BaseException | None = None
    try:
        _TRUSTED_CLOSE(composition)
    except BaseException as error:  # noqa: BLE001 - cleanup precedence is explicit
        cleanup_error = error
    del composition
    if cleanup_error is not None:
        if isinstance(cleanup_error, Exception):
            del cleanup_error, execution_error
            return _SafeOutcome(_OutcomeCategory.LIFECYCLE)
        del execution_error
        return _base_exception_outcome(cleanup_error)
    if execution_error is not None:
        if isinstance(execution_error, Exception):
            del execution_error
            return _SafeOutcome(_OutcomeCategory.DEPENDENCY)
        return _base_exception_outcome(execution_error)
    if valid_text is None:
        return _SafeOutcome(_OutcomeCategory.DEPENDENCY)
    return _SafeOutcome(_OutcomeCategory.SUCCESS, valid_text)


def _validated_result_text(
    value: object, request: ProviderExecutionRequestV2
) -> str | None:
    if type(value) is not ProviderExecutionResultV2:
        return None
    try:
        rebuilt = ProviderExecutionResultV2.model_validate(
            value.model_dump(mode="python", warnings="error"), strict=True
        )
        projection = rebuilt.provider_result
        if projection is None or len(projection.outputs) != 1:
            return None
        output = projection.outputs[0]
        expected_source = request.request_envelope.request_units[
            0
        ].source_request_reference
        if (
            rebuilt.request_id != request.context.request_id
            or rebuilt.provider_id != request.provider.provider_id
            or rebuilt.request_envelope_identity != request.request_envelope.identity
            or rebuilt.outcome is not ExecutionOutcomeV2.COMPLETED
            or rebuilt.failure_code is not None
            or rebuilt.failure_message is not None
            or projection.status is not ProviderResultStatusV2.SUCCESS
            or projection.failure_code is not None
            or output.ordinal != 0
            or output.source_request_reference != expected_source
            or output.finish_reason is not ProviderFinishReasonV2.COMPLETED
            or output.generated_text != _EXPECTED_TEXT
        ):
            return None
        return _EXPECTED_TEXT
    except (AttributeError, IndexError, TypeError, ValueError, ValidationError):
        return None


def _base_exception_outcome(error: BaseException) -> _SafeOutcome:
    error.__traceback__ = None
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True
    return _SafeOutcome(_OutcomeCategory.BASE_EXCEPTION, error)


def _return_or_raise(outcome: _SafeOutcome) -> OpenAILiveSmokeResultV2:
    category = outcome.category
    value = outcome.value
    del outcome
    if category is _OutcomeCategory.SUCCESS:
        return OpenAILiveSmokeResultV2(success=True, response_text=value)
    if category is _OutcomeCategory.BASE_EXCEPTION:
        error = value
        assert isinstance(error, BaseException)
        try:
            raise error from None
        finally:
            error.__context__ = None
            error.__cause__ = None
            error.__suppress_context__ = True
    if category is _OutcomeCategory.INVALID:
        _raise_fixed(OpenAILiveSmokeConfigurationError, _CONFIGURATION_MESSAGE)
    if category is _OutcomeCategory.UNCONFIRMED:
        _raise_fixed(OpenAILiveSmokeConfigurationError, _CONFIRMATION_MESSAGE)
    if category is _OutcomeCategory.LIFECYCLE:
        _raise_fixed(OpenAILiveSmokeLifecycleError, _LIFECYCLE_MESSAGE)
    _raise_dependency_error()


def _raise_dependency_error() -> Never:
    _raise_fixed(OpenAILiveSmokeDependencyError, _DEPENDENCY_MESSAGE)


def _raise_fixed(error_type: type[Exception], message: str) -> Never:
    error = error_type(message)
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_serialization_error() -> Never:
    _raise_fixed(TypeError, _SERIALIZATION_MESSAGE)


def _raise_frozen_error() -> Never:
    _raise_fixed(AttributeError, "OpenAI live smoke runners are immutable")


__all__ = ("OpenAILiveSmokeRunnerV2",)

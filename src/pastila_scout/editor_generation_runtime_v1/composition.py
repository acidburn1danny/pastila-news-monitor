"""Runtime session and provider-neutral Editor composition."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import math
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from types import FunctionType
from typing import TYPE_CHECKING, NoReturn, get_type_hints

from pastila_scout.editor_core_identities_v1 import (
    CORE_V1_1_MODEL_ID,
    CORE_V1_2_MODEL_ID,
)
if TYPE_CHECKING:
    import httpx

from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationRequestAuthorityV1,
    EditorGenerationRuntimeAuthorityV1,
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_generation_provider_adapter_v1 import (
    EditorNeutralLanguageModelProviderV1,
)
from pastila_scout.editor_request_fingerprint_authority_v1 import (
    EditorRequestFingerprintAuthorityV1,
)
from pastila_scout.provider_execution_openai_v2 import (
    OpenAIExecutionConfigV2,
    OpenAIProviderExecutorV2,
)
from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_runtime_openai_v2 import (
    OpenAIRuntimeComposerV2,
    OpenAIRuntimeCompositionV2,
)
from pastila_scout.provider_runtime_openai_v2.production import (
    _create_environment_openai_runtime_composer_v2,
)
from pastila_scout.provider_selection_v1 import (
    ProviderChoiceV1,
    ProviderExecutorRegistrationV1,
    ProviderSelectionConfigV1,
    ProviderSelectorV1,
)
from pastila_scout.scout_runtime_execution_v1 import ScoutRuntimeExecutionBridgeV1
from pastila_scout.scout_runtime_execution_v1.models import (
    ScoutRuntimeRequestV1,
    ScoutRuntimeResultV1,
)
from pastila_scout.scout_runtime_v1 import (
    ScoutCancellationV1,
    ScoutRuntimeCompositionV1,
    ScoutRuntimeConfigV1,
    ScoutRuntimeOptionsV1,
)
from pastila_scout.scout_workflow_execution_v1 import (
    LegacyScoutWorkflowExecutionV1,
    ScoutWorkflowExecutionV1,
)

from .errors import EditorGenerationRuntimeCompositionError
from .models import (
    EditorAdapterDependenciesV1,
    EditorOllamaRuntimeHandleV1,
    _EditorGenerationAttemptRecorderV1,
)
from .protocols import (
    EditorAdapterDependencyFactoryV1,
    EditorGenerationAttemptRecorderV1,
    EditorOllamaRuntimeFactoryV1,
    EditorOpenAIRuntimeComposerFactoryV1,
)

_FAILED = "Editor generation runtime composition failed."
_CLOSED = "Editor generation runtime session is closed."
_ALREADY_CLOSED = "Editor generation runtime session is already closed."


def _raise(message: str = _FAILED) -> NoReturn:
    error = EditorGenerationRuntimeCompositionError(message)
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


@dataclass(frozen=True, slots=True, repr=False)
class _NonOperationalProviderExecutorV2:
    provider: ProviderChoiceV1

    def __init__(self, *, provider: ProviderChoiceV1) -> None:
        if type(provider) is not ProviderChoiceV1:
            _raise()
        object.__setattr__(self, "provider", provider)

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        try:
            if type(self) is not _NonOperationalProviderExecutorV2:
                _raise("Non-operational provider registration was invoked incorrectly.")
            provider = object.__getattribute__(self, "provider")
            if (
                type(provider) is not ProviderChoiceV1
                or type(request) is not ProviderExecutionRequestV2
            ):
                _raise("Non-operational provider registration was invoked incorrectly.")
            authority = ProviderExecutionRequestV2.model_validate(
                request.model_dump(mode="python", warnings=False), strict=True
            )
            if authority.provider.provider_id != provider.value:
                _raise("Non-operational provider registration was invoked incorrectly.")
            result = ProviderExecutionResultV2(
                request_id=authority.context.request_id,
                provider_id=authority.provider.provider_id,
                request_envelope_identity=authority.request_envelope.identity,
                outcome=ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
                finished_at=authority.context.requested_at,
                failure_code="non-operational-provider-registration",
                failure_message="Non-operational provider registration was invoked.",
            )
            return ProviderExecutionResultV2.model_validate(
                result.model_dump(mode="python", warnings=False), strict=True
            )
        except EditorGenerationRuntimeCompositionError:
            raise
        except Exception:  # noqa: BLE001 - untrusted request state is isolated
            _raise("Non-operational provider registration was invoked incorrectly.")

    def __repr__(self) -> str:
        provider = _inert_provider(self)
        return f"_NonOperationalProviderExecutorV2(provider={provider.value!r})"

    def __copy__(self) -> _NonOperationalProviderExecutorV2:
        _inert_provider(self)
        return self

    def __deepcopy__(
        self, memo: dict[int, object]
    ) -> _NonOperationalProviderExecutorV2:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("Non-operational provider executor cannot be pickled.")


def _inert_provider(value: object) -> ProviderChoiceV1:
    try:
        if type(value) is not _NonOperationalProviderExecutorV2:
            _raise()
        provider = object.__getattribute__(value, "provider")
        if type(provider) is not ProviderChoiceV1:
            _raise()
        return provider
    except EditorGenerationRuntimeCompositionError:
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        _raise()


@dataclass(frozen=True, slots=True, init=False, eq=False, repr=False)
class _EditorScoutWorkflowFactoryV1:
    _legacy_workflow: LegacyScoutWorkflowExecutionV1

    def __init__(self, *, legacy_workflow: LegacyScoutWorkflowExecutionV1) -> None:
        if not _method(
            legacy_workflow,
            "execute",
            (
                (
                    "request",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    "ScoutRuntimeRequestV1",
                ),
            ),
            "ScoutRuntimeResultV1",
        ):
            _raise()
        object.__setattr__(self, "_legacy_workflow", legacy_workflow)

    def create(
        self, *, runtime_composition: ScoutRuntimeCompositionV1
    ) -> ScoutWorkflowExecutionV1:
        try:
            legacy = _workflow_factory_state(self)
            _runtime_composition_state(runtime_composition)
            bridge = ScoutRuntimeExecutionBridgeV1(runtime_composition)
            if (
                object.__getattribute__(bridge, "composition")
                is not runtime_composition
            ):
                _raise()
            workflow = ScoutWorkflowExecutionV1(legacy, bridge)
            if (
                object.__getattribute__(workflow, "legacy_workflow") is not legacy
                or object.__getattribute__(workflow, "runtime_bridge") is not bridge
            ):
                _raise()
            return workflow
        except EditorGenerationRuntimeCompositionError:
            raise
        except Exception:  # noqa: BLE001 - frozen boundary failures are isolated
            _raise()

    def __repr__(self) -> str:
        _workflow_factory_state(self)
        return "_EditorScoutWorkflowFactoryV1(legacy_workflow=<injected>)"

    def __eq__(self, other: object) -> bool:
        _workflow_factory_state(self)
        return self is other

    def __copy__(self) -> _EditorScoutWorkflowFactoryV1:
        _workflow_factory_state(self)
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> _EditorScoutWorkflowFactoryV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("Editor Scout workflow factory cannot be pickled.")


def _workflow_factory_state(value: object) -> object:
    try:
        if type(value) is not _EditorScoutWorkflowFactoryV1:
            _raise()
        legacy = object.__getattribute__(value, "_legacy_workflow")
        if not _method(
            legacy,
            "execute",
            (
                (
                    "request",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    "ScoutRuntimeRequestV1",
                ),
            ),
            "ScoutRuntimeResultV1",
        ):
            _raise()
        return legacy
    except EditorGenerationRuntimeCompositionError:
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        _raise()


@dataclass(frozen=True, slots=True, init=False, eq=False, repr=False)
class EditorGenerationRuntimeSessionV1:
    _workflow: ScoutWorkflowExecutionV1
    _runtime_authority: EditorGenerationRuntimeAuthorityV1
    _adapter: EditorNeutralLanguageModelProviderV1
    _attempt_recorder: object
    _operation_reference: str
    _lifecycle: object
    _closed: bool

    def __init__(
        self,
        workflow,
        runtime_authority,
        adapter,
        attempt_recorder,
        operation_reference,
        lifecycle,
    ) -> None:
        valid = (
            type(workflow) is not ScoutWorkflowExecutionV1
            or type(runtime_authority) is not EditorGenerationRuntimeAuthorityV1
            or type(adapter) is not EditorNeutralLanguageModelProviderV1
            or not _text(operation_reference, 120)
            or not _method(attempt_recorder, "snapshot", (), tuple)
            or not _method(lifecycle, "close", (), type(None))
        )
        if valid:
            del (
                self,
                workflow,
                runtime_authority,
                adapter,
                attempt_recorder,
                operation_reference,
                lifecycle,
            )
            _raise()
        for name, value in (
            ("_workflow", workflow),
            ("_runtime_authority", runtime_authority),
            ("_adapter", adapter),
            ("_attempt_recorder", attempt_recorder),
            ("_operation_reference", operation_reference),
            ("_lifecycle", lifecycle),
            ("_closed", False),
        ):
            object.__setattr__(self, name, value)

    @property
    def workflow(self) -> ScoutWorkflowExecutionV1:
        status, value = _read_session(self, "_workflow", require_open=True)
        del self
        if status:
            _raise(_CLOSED if status == 1 else _FAILED)
        return value

    @property
    def runtime_authority(self) -> EditorGenerationRuntimeAuthorityV1:
        status, value = _read_session(self, "_runtime_authority", require_open=True)
        del self
        if status:
            _raise(_CLOSED if status == 1 else _FAILED)
        return value

    @property
    def adapter(self) -> EditorNeutralLanguageModelProviderV1:
        status, value = _read_session(self, "_adapter", require_open=True)
        del self
        if status:
            _raise(_CLOSED if status == 1 else _FAILED)
        return value

    @property
    def attempt_recorder(self) -> EditorGenerationAttemptRecorderV1:
        status, value = _read_session(self, "_attempt_recorder", require_open=True)
        del self
        if status:
            _raise(_CLOSED if status == 1 else _FAILED)
        return value

    @property
    def operation_reference(self) -> str:
        status, value = _read_session(self, "_operation_reference")
        del self
        if status:
            _raise()
        return value

    @property
    def is_closed(self) -> bool:
        status, value = _read_session(self, "_closed")
        del self
        if status:
            _raise()
        return value

    def close(self) -> None:
        status = _close_session(self)
        del self
        if status == 1:
            _raise(_ALREADY_CLOSED)
        if status != 0:
            _raise()

    def __repr__(self) -> str:
        return f"EditorGenerationRuntimeSessionV1(closed={self.is_closed})"

    def __copy__(self) -> EditorGenerationRuntimeSessionV1:
        _session_value(self, "_closed")
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> EditorGenerationRuntimeSessionV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("Editor generation runtime session cannot be pickled.")


def _session_value(session: object, name: str):
    try:
        if type(session) is not EditorGenerationRuntimeSessionV1:
            _raise()
        value = object.__getattribute__(session, name)
        closed = object.__getattribute__(session, "_closed")
        if type(closed) is not bool:
            _raise()
        return value
    except EditorGenerationRuntimeCompositionError:
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        _raise()


def _session_authority(session: object, name: str):
    if _session_value(session, "_closed"):
        _raise(_CLOSED)
    return _session_value(session, name)


def _read_session(
    session: object, name: str, *, require_open: bool = False
) -> tuple[int, object]:
    """Read session state without propagating a frame that retains the session."""
    try:
        if type(session) is not EditorGenerationRuntimeSessionV1:
            return 2, None
        closed = object.__getattribute__(session, "_closed")
        if type(closed) is not bool:
            return 2, None
        if require_open and closed:
            return 1, None
        return 0, object.__getattribute__(session, name)
    except Exception:  # noqa: BLE001 - authority-bearing frame never propagates
        return 2, None


def _close_session(session: object) -> int:
    """Close owned resources and reduce every failure to a neutral status."""
    try:
        if type(session) is not EditorGenerationRuntimeSessionV1:
            return 2
        closed = object.__getattribute__(session, "_closed")
        if type(closed) is not bool:
            return 2
        if closed:
            return 1
        lifecycle = object.__getattribute__(session, "_lifecycle")
        object.__setattr__(session, "_closed", True)
        lifecycle.close()
        return 0
    except Exception:  # noqa: BLE001 - authority-bearing frame never propagates
        return 2


@dataclass(frozen=True, slots=True, init=False, eq=False, repr=False)
class EditorGenerationRuntimeSessionFactoryV1:
    _openai_factory: object
    _ollama_factory: object
    _legacy_workflow: object
    _adapter_factory: object
    _fingerprint: EditorRequestFingerprintAuthorityV1

    def __init__(
        self,
        *,
        openai_composer_factory: EditorOpenAIRuntimeComposerFactoryV1,
        ollama_session_factory: EditorOllamaRuntimeFactoryV1,
        legacy_workflow: LegacyScoutWorkflowExecutionV1,
        adapter_dependency_factory: EditorAdapterDependencyFactoryV1,
        fingerprint_authority: EditorRequestFingerprintAuthorityV1,
    ) -> None:
        valid = _factory_dependencies(
            openai_composer_factory,
            ollama_session_factory,
            legacy_workflow,
            adapter_dependency_factory,
            fingerprint_authority,
        )
        if not valid:
            del (
                self,
                openai_composer_factory,
                ollama_session_factory,
                legacy_workflow,
                adapter_dependency_factory,
                fingerprint_authority,
            )
            _raise()
        values = (
            openai_composer_factory,
            ollama_session_factory,
            legacy_workflow,
            adapter_dependency_factory,
            fingerprint_authority,
        )
        for name, value in zip(_FACTORY_FIELDS, values, strict=True):
            object.__setattr__(self, name, value)

    def open(
        self,
        options: EditorGenerationRuntimeOptionsV1,
        *,
        operation_reference: str,
    ) -> EditorGenerationRuntimeSessionV1:
        session = _open_session(self, options, operation_reference)
        del self, options, operation_reference
        if session is None:
            _raise()
        return session

    def __repr__(self) -> str:
        _factory_state(self)
        return "EditorGenerationRuntimeSessionFactoryV1(<injected dependencies>)"

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        return all(
            a is b
            for a, b in zip(_factory_state(self), _factory_state(other), strict=True)
        )

    def __copy__(self) -> EditorGenerationRuntimeSessionFactoryV1:
        values = _factory_state(self)
        return type(self)(
            openai_composer_factory=values[0],
            ollama_session_factory=values[1],
            legacy_workflow=values[2],
            adapter_dependency_factory=values[3],
            fingerprint_authority=values[4],
        )

    def __deepcopy__(
        self, memo: dict[int, object]
    ) -> EditorGenerationRuntimeSessionFactoryV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("Editor generation runtime session factory cannot be pickled.")


def _open_session(
    factory: object,
    requested_options: object,
    operation_reference: object,
) -> EditorGenerationRuntimeSessionV1 | None:
    """Build a session atomically without propagating authority-bearing frames."""
    lifecycle = None
    try:
        dependencies = _factory_state(factory)
        options = copy.copy(requested_options)
        if type(options) is not EditorGenerationRuntimeOptionsV1 or not _text(
            operation_reference, 120
        ):
            return None
        selected, lifecycle = _selected_runtime(
            options, dependencies[0], dependencies[1]
        )
        selected_registration = ProviderExecutorRegistrationV1(
            options.provider, selected
        )
        other = (
            ProviderChoiceV1.OLLAMA
            if options.provider is ProviderChoiceV1.OPENAI
            else ProviderChoiceV1.OPENAI
        )
        inert = _NonOperationalProviderExecutorV2(provider=other)
        inert_registration = ProviderExecutorRegistrationV1(other, inert)
        registrations = tuple(
            selected_registration if choice is options.provider else inert_registration
            for choice in (ProviderChoiceV1.OPENAI, ProviderChoiceV1.OLLAMA)
        )
        registrations = tuple(
            ProviderExecutorRegistrationV1(item.provider, item.executor)
            for item in registrations
        )
        selector = ProviderSelectorV1(
            ProviderSelectionConfigV1(options.provider), registrations
        )
        if selector.executor is not selected:
            raise TypeError
        candidate = ScoutRuntimeCompositionV1(
            selector,
            ScoutRuntimeConfigV1("editor-generation-runtime-config-v1"),
            ScoutRuntimeOptionsV1("editor-generation-runtime-options-v1"),
            ScoutCancellationV1(False),
        )
        runtime_composition = copy.copy(candidate)
        if (
            runtime_composition is candidate
            or object.__getattribute__(runtime_composition, "selector") is not selector
        ):
            raise TypeError
        del candidate
        workflow_factory = _EditorScoutWorkflowFactoryV1(
            legacy_workflow=dependencies[2]
        )
        workflow = workflow_factory.create(runtime_composition=runtime_composition)
        runtime_authority = _runtime_authority(options, operation_reference)
        adapter_dependencies = dependencies[3].create(
            operation_reference=operation_reference
        )
        if type(adapter_dependencies) is not EditorAdapterDependenciesV1:
            raise TypeError
        adapter_dependencies = copy.copy(adapter_dependencies)
        adapter = EditorNeutralLanguageModelProviderV1(
            provider=options.provider,
            workflow=workflow,
            runtime_authority=runtime_authority,
            fingerprint_authority=dependencies[4],
            request_authority=EditorGenerationRequestAuthorityV1(),
            requested_at_factory=adapter_dependencies.clock,
            cancellation_source=adapter_dependencies.cancellation_source,
            request_reference_factory=adapter_dependencies.reference_factory,
            attempt_recorder=adapter_dependencies.attempt_recorder,
        )
        return EditorGenerationRuntimeSessionV1(
            workflow,
            runtime_authority,
            adapter,
            adapter_dependencies.attempt_recorder,
            operation_reference,
            lifecycle,
        )
    except Exception:  # noqa: BLE001 - reduced after reverse-order rollback
        if lifecycle is not None:
            try:
                lifecycle.close()
            except Exception:  # noqa: BLE001, S110 - cleanup failure is contained
                pass
        return None


_FACTORY_FIELDS = (
    "_openai_factory",
    "_ollama_factory",
    "_legacy_workflow",
    "_adapter_factory",
    "_fingerprint",
)


def _factory_state(value: object) -> tuple[object, ...]:
    try:
        if type(value) is not EditorGenerationRuntimeSessionFactoryV1:
            _raise()
        values = tuple(object.__getattribute__(value, name) for name in _FACTORY_FIELDS)
        if not _factory_dependencies(*values):
            _raise()
        return values
    except EditorGenerationRuntimeCompositionError:
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        _raise()


def _factory_dependencies(openai, ollama, legacy, adapter, fingerprint) -> bool:
    return (
        _method(
            openai,
            "create",
            (
                ("model_identifier", inspect.Parameter.KEYWORD_ONLY, str),
                ("timeout_seconds", inspect.Parameter.KEYWORD_ONLY, int | float),
            ),
            OpenAIRuntimeComposerV2,
        )
        and _method(
            ollama,
            "open",
            (
                (
                    "options",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    EditorGenerationRuntimeOptionsV1,
                ),
            ),
            EditorOllamaRuntimeHandleV1,
        )
        and _method(
            legacy,
            "execute",
            (
                (
                    "request",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    "ScoutRuntimeRequestV1",
                ),
            ),
            "ScoutRuntimeResultV1",
        )
        and _method(
            adapter,
            "create",
            (("operation_reference", inspect.Parameter.KEYWORD_ONLY, str),),
            EditorAdapterDependenciesV1,
        )
        and type(fingerprint) is EditorRequestFingerprintAuthorityV1
    )


def _selected_runtime(options, openai_factory, ollama_factory):
    if options.provider is ProviderChoiceV1.OPENAI:
        composer = openai_factory.create(
            model_identifier=options.model_identifier,
            timeout_seconds=options.timeout_policy.timeout_seconds,
        )
        if type(composer) is not OpenAIRuntimeComposerV2:
            _raise()
        composition = composer.compose()
        if type(composition) is not OpenAIRuntimeCompositionV2:
            _raise()
        executor = OpenAIProviderExecutorV2(
            client=composition.sdk_client,
            config=OpenAIExecutionConfigV2(
                model=options.model_identifier,
                temperature=options.temperature,
                max_output_tokens=options.max_output_tokens,
                stop_sequences=options.stop_sequences,
            ),
        )
        return executor, composition
    handle = ollama_factory.open(options)
    if type(handle) is not EditorOllamaRuntimeHandleV1:
        _raise()
    return handle.executor, handle.lifecycle


def _runtime_authority(options, reference):
    payload = {
        "options": {
            "provider": options.provider.value,
            "model_identifier": options.model_identifier,
            "model_revision": options.model_revision,
            "temperature": {
                "type": "int" if type(options.temperature) is int else "float",
                "value": options.temperature,
            },
            "top_p": {
                "type": "int" if type(options.top_p) is int else "float",
                "value": options.top_p,
            },
            "max_output_tokens": options.max_output_tokens,
            "seed": options.seed,
            "stop_sequences": options.stop_sequences,
            "structured_output_mode": options.structured_output_mode,
            "timeout_seconds": {
                "type": (
                    "int"
                    if type(options.timeout_policy.timeout_seconds) is int
                    else "float"
                ),
                "value": options.timeout_policy.timeout_seconds,
            },
        },
        "runtime_reference": reference,
    }
    canonical = json.dumps(
        _canonical(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    result = EditorGenerationRuntimeAuthorityV1(
        options, reference, hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    )
    return copy.copy(result)


def _canonical(value):
    if value is None or type(value) in {bool, int}:
        return value
    if type(value) is str:
        return unicodedata.normalize("NFC", value)
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is tuple:
        return [_canonical(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {_canonical(key): _canonical(item) for key, item in value.items()}
    raise TypeError


def _runtime_composition_state(value):
    if type(value) is not ScoutRuntimeCompositionV1:
        _raise()
    selector = object.__getattribute__(value, "selector")
    config = object.__getattribute__(value, "config")
    options = object.__getattribute__(value, "options")
    cancellation = object.__getattribute__(value, "cancellation")
    if (
        type(selector) is not ProviderSelectorV1
        or type(config) is not ScoutRuntimeConfigV1
        or config.configuration_identity != "editor-generation-runtime-config-v1"
        or type(options) is not ScoutRuntimeOptionsV1
        or options.options_identity != "editor-generation-runtime-options-v1"
        or type(cancellation) is not ScoutCancellationV1
        or cancellation.cancellation_requested
    ):
        _raise()


def _method(value, name, expected, returns) -> bool:
    try:
        if (
            inspect.getattr_static(type(value), "__getattribute__")
            is not object.__getattribute__
            or inspect.getattr_static(type(value), "__getattr__", None) is not None
        ):
            return False
        try:
            state = object.__getattribute__(value, "__dict__")
        except AttributeError:
            state = {}
        if type(state) is not dict or name in state:
            return False
        descriptor = inspect.getattr_static(type(value), name)
        if (
            type(descriptor) is not FunctionType
            or hasattr(descriptor, "__signature__")
            or hasattr(descriptor, "__wrapped__")
        ):
            return False
        signature = inspect.signature(descriptor, follow_wrapped=False)
        hints = get_type_hints(descriptor)
        parameters = tuple(signature.parameters.values())
        if len(parameters) != len(expected) + 1 or parameters[0].name != "self":
            return False
        for parameter, spec in zip(parameters[1:], expected, strict=True):
            actual = hints.get(parameter.name)
            expected_type = spec[2]
            if isinstance(expected_type, str):
                if getattr(actual, "__name__", None) != expected_type:
                    return False
            elif actual != expected_type:
                return False
            if (
                parameter.name != spec[0]
                or parameter.kind is not spec[1]
                or parameter.default is not inspect.Parameter.empty
            ):
                return False
        actual_return = hints.get("return")
        if isinstance(returns, str):
            return getattr(actual_return, "__name__", None) == returns
        if returns is tuple:
            return getattr(actual_return, "__origin__", None) is tuple
        return actual_return == returns
    except Exception:  # noqa: BLE001 - static validation fails closed
        return False


def _text(value, maximum):
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= maximum
        and unicodedata.is_normalized("NFC", value)
    )


_PRIVATE_PICKLE_ERROR = (
    "Editor application runtime composition values cannot be pickled."
)


class _PrivateStatelessV1:
    __slots__ = ()

    def __init_subclass__(cls, **kwargs):
        del kwargs
        if cls.__base__ is not _PrivateStatelessV1:
            raise TypeError("Editor runtime composition values cannot be subclassed.")

    def __repr__(self) -> str:
        _require_exact_stateless(self)
        return f"{type(self).__name__}()"

    def __eq__(self, other: object) -> bool:
        _require_exact_stateless(self)
        return type(other) is type(self)

    def __copy__(self):
        _require_exact_stateless(self)
        return type(self)()

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol):
        del self, protocol
        raise TypeError(_PRIVATE_PICKLE_ERROR)


def _require_exact_stateless(value: object) -> None:
    if type(value).__base__ is not _PrivateStatelessV1:
        _raise()


class _OpenAIComposerFactoryV1(_PrivateStatelessV1):
    __slots__ = ()

    def create(
        self, *, model_identifier: str, timeout_seconds: int | float  # noqa: PYI041
    ) -> OpenAIRuntimeComposerV2:
        _require_exact_stateless(self)
        try:
            result = _create_environment_openai_runtime_composer_v2(
                model_identifier=model_identifier,
                timeout_seconds=timeout_seconds,
            )
        except (TypeError, ValueError):
            _raise()
        if type(result) is not OpenAIRuntimeComposerV2:
            _raise()
        return result


class _OllamaRuntimeLifecycleV1:
    __slots__ = ("_client", "_closed")

    def __init__(self, client: httpx.Client) -> None:
        if type(client) is not _httpx_client_type():
            _raise()
        object.__setattr__(self, "_client", client)
        object.__setattr__(self, "_closed", False)

    def close(self) -> None:
        try:
            if type(self) is not _OllamaRuntimeLifecycleV1:
                _raise()
            client = object.__getattribute__(self, "_client")
            closed = object.__getattribute__(self, "_closed")
            if (
                type(client) is not _httpx_client_type()
                or type(closed) is not bool
                or closed
            ):
                _raise()
            client.close()
            object.__setattr__(self, "_closed", True)
        except EditorGenerationRuntimeCompositionError:
            raise
        except Exception:  # noqa: BLE001 - client details remain private
            _raise()

    def __repr__(self) -> str:
        _ollama_lifecycle_state(self)
        return "_OllamaRuntimeLifecycleV1(<owned client>)"

    def __eq__(self, other: object) -> bool:
        _ollama_lifecycle_state(self)
        return self is other

    def __copy__(self):
        _ollama_lifecycle_state(self)
        raise TypeError("Editor Ollama runtime lifecycle cannot be copied.")

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol):
        del self, protocol
        raise TypeError(_PRIVATE_PICKLE_ERROR)


def _ollama_lifecycle_state(value: object) -> tuple[object, bool]:
    try:
        if type(value) is not _OllamaRuntimeLifecycleV1:
            _raise()
        client = object.__getattribute__(value, "_client")
        closed = object.__getattribute__(value, "_closed")
        if type(client) is not _httpx_client_type() or type(closed) is not bool:
            _raise()
        return client, closed
    except EditorGenerationRuntimeCompositionError:
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        _raise()


class _OllamaRuntimeSessionFactoryV1(_PrivateStatelessV1):
    __slots__ = ()

    def open(
        self, options: EditorGenerationRuntimeOptionsV1
    ) -> EditorOllamaRuntimeHandleV1:
        _require_exact_stateless(self)
        client = None
        try:
            if type(options) is not EditorGenerationRuntimeOptionsV1:
                _raise()
            if options.model_identifier == CORE_V1_2_MODEL_ID:
                experimental_v1_2 = import_module(
                    "pastila_scout.experimental_core_v1_2"
                )
                project_root = Path(
                    getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3])
                )
                executor = experimental_v1_2.ExperimentalCoreV12Executor(
                    project_root=project_root,
                    max_output_tokens=options.max_output_tokens,
                )
                client = _httpx_client_type()()
                lifecycle = _OllamaRuntimeLifecycleV1(client)
                return EditorOllamaRuntimeHandleV1(executor, lifecycle)
            if options.model_identifier == CORE_V1_1_MODEL_ID:
                experimental = import_module("pastila_scout.experimental_core_v1_1")
                project_root = Path(__file__).resolve().parents[3]
                executor = experimental.ExperimentalCoreV11Executor(
                    project_root=project_root
                )
                client = _httpx_client_type()()
                lifecycle = _OllamaRuntimeLifecycleV1(client)
                return EditorOllamaRuntimeHandleV1(executor, lifecycle)
            ollama = import_module("pastila_scout.provider_execution_ollama_v1")
            client = _httpx_client_type()()
            executor = ollama.OllamaProviderExecutorV1(
                ollama.OllamaHttpClientV1(client),
                ollama.OllamaExecutionConfigV1(
                    model=options.model_identifier,
                    base_url="http://localhost:11434",
                    temperature=options.temperature,
                    max_output_tokens=options.max_output_tokens,
                    stop_sequences=options.stop_sequences,
                ),
            )
            lifecycle = _OllamaRuntimeLifecycleV1(client)
            return EditorOllamaRuntimeHandleV1(executor, lifecycle)
        except EditorGenerationRuntimeCompositionError:
            if client is not None:
                client.close()
            raise
        except Exception:  # noqa: BLE001 - construction details remain private
            if client is not None:
                try:
                    client.close()
                except Exception:  # noqa: BLE001, S110 - unpublished cleanup
                    pass
            _raise()


def _httpx_client_type() -> type:
    module = import_module("httpx")
    return module.Client


class _EditorRuntimeClockV1(_PrivateStatelessV1):
    __slots__ = ()

    def now(self) -> datetime:
        _require_exact_stateless(self)
        return datetime.now(timezone.utc)  # noqa: UP017 - normative spelling


class _EditorRuntimeCancellationSourceV1(_PrivateStatelessV1):
    __slots__ = ()

    def snapshot(self) -> CancellationTokenV2:
        _require_exact_stateless(self)
        return CancellationTokenV2(cancellation_requested=False)


class _EditorAttemptReferenceFactoryV1:
    __slots__ = ("_operation_reference",)

    def __init__(self, *, operation_reference: str) -> None:
        if not _text(operation_reference, 120):
            _raise()
        object.__setattr__(self, "_operation_reference", operation_reference)

    def create(self, *, prompt_fingerprint: str, attempt_number: int) -> str:
        operation_reference = _attempt_reference_state(self)
        fingerprint = (
            prompt_fingerprint.removeprefix("sha256:")
            if type(prompt_fingerprint) is str
            else prompt_fingerprint
        )
        if (
            type(fingerprint) is not str
            or len(fingerprint) != 64
            or any(
                character not in "0123456789abcdef" for character in fingerprint
            )
            or type(attempt_number) is not int
            or attempt_number < 1
        ):
            _raise()
        payload = (
            operation_reference + "\0" + fingerprint + "\0" + str(attempt_number)
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"editor-attempt-v1-{attempt_number}-{digest[:32]}"

    def __repr__(self) -> str:
        _attempt_reference_state(self)
        return "_EditorAttemptReferenceFactoryV1(<operation reference>)"

    def __eq__(self, other: object) -> bool:
        left = _attempt_reference_state(self)
        return type(other) is type(self) and left == _attempt_reference_state(other)

    def __copy__(self):
        return type(self)(operation_reference=_attempt_reference_state(self))

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol):
        del self, protocol
        raise TypeError(_PRIVATE_PICKLE_ERROR)


def _attempt_reference_state(value: object) -> str:
    try:
        if type(value) is not _EditorAttemptReferenceFactoryV1:
            _raise()
        reference = object.__getattribute__(value, "_operation_reference")
        if not _text(reference, 120):
            _raise()
        return reference
    except EditorGenerationRuntimeCompositionError:
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        _raise()


class _EditorAdapterDependenciesFactoryV1(_PrivateStatelessV1):
    __slots__ = ()

    def create(self, *, operation_reference: str) -> EditorAdapterDependenciesV1:
        _require_exact_stateless(self)
        return EditorAdapterDependenciesV1(
            _EditorRuntimeClockV1(),
            _EditorRuntimeCancellationSourceV1(),
            _EditorAttemptReferenceFactoryV1(operation_reference=operation_reference),
            _EditorGenerationAttemptRecorderV1(),
        )


class _FailClosedLegacyWorkflowV1(_PrivateStatelessV1):
    __slots__ = ()

    def execute(self, request: ScoutRuntimeRequestV1) -> ScoutRuntimeResultV1:
        del request
        _require_exact_stateless(self)
        _raise()


def _create_editor_generation_runtime_session_factory_v1() -> (
    EditorGenerationRuntimeSessionFactoryV1
):
    return EditorGenerationRuntimeSessionFactoryV1(
        openai_composer_factory=_OpenAIComposerFactoryV1(),
        ollama_session_factory=_OllamaRuntimeSessionFactoryV1(),
        legacy_workflow=_FailClosedLegacyWorkflowV1(),
        adapter_dependency_factory=_EditorAdapterDependenciesFactoryV1(),
        fingerprint_authority=EditorRequestFingerprintAuthorityV1(),
    )


__all__ = (
    "EditorGenerationRuntimeSessionFactoryV1",
    "EditorGenerationRuntimeSessionV1",
)

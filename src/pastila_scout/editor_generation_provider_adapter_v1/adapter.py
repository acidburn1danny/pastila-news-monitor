"""Provider-neutral LanguageModelProvider adapter."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import math
from dataclasses import dataclass
from datetime import datetime
from types import FunctionType
from typing import NoReturn, TypeVar, get_type_hints

from pydantic import BaseModel

from pastila_scout.editor.generation.models import (
    CallToActionGenerationResult,
    ClosingGenerationResult,
    LanguageGenerationConfig,
    OpeningGenerationResult,
    StoryAuthoredContentResult,
    StoryGenerationResult,
    TransitionGenerationResult,
)
from pastila_scout.editor.generation.prompt import GenerationPrompt
from pastila_scout.editor.generation.provider import (
    ProviderResponseError,
    ProviderStructuredOutputError,
    ProviderTimeoutError,
)
from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationRequestAuthorityV1,
    EditorGenerationRuntimeAuthorityV1,
)
from pastila_scout.editor_request_fingerprint_authority_v1 import (
    EditorRequestFingerprintAuthorityV1,
)
from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ExecutionOutcomeV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.provider_v2 import ProviderFinishReasonV2, ProviderResultStatusV2
from pastila_scout.scout_runtime_execution_v1 import (
    ScoutRuntimeRequestV1,
    ScoutRuntimeResultV1,
)
from pastila_scout.scout_workflow_execution_v1 import ScoutWorkflowExecutionV1

from .application_request import _EditorGenerationApplicationRequestBuilderV1
from .errors import EditorGenerationProviderAdapterError, ProviderCancellationError
from .models import EditorGenerationAttemptObservationV1
from .parsing import validate_generated_model
from .protocols import (
    EditorGenerationAttemptRecorderV1,
    EditorGenerationCancellationSourceV1,
    EditorGenerationClockV1,
    EditorGenerationReferenceFactoryV1,
)

T = TypeVar("T", bound=BaseModel)
_SAFE = "Editor generation provider adapter failed."
_PROVIDER = "Provider execution failed."
_TIMEOUT = "Provider execution timed out."
_CANCELLED = "Provider execution was cancelled."
_ALLOWED = (
    StoryAuthoredContentResult,
    StoryGenerationResult,
    TransitionGenerationResult,
    OpeningGenerationResult,
    ClosingGenerationResult,
    CallToActionGenerationResult,
)


def _raise_adapter() -> NoReturn:
    error = EditorGenerationProviderAdapterError(_SAFE)
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


def _raise_provider(kind: str) -> NoReturn:
    mapping = {
        "timeout": (ProviderTimeoutError, _TIMEOUT),
        "cancelled": (ProviderCancellationError, _CANCELLED),
        "provider": (ProviderResponseError, _PROVIDER),
        "internal": (ProviderResponseError, _PROVIDER),
    }
    cls, message = mapping[kind]
    error = cls(message)
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorNeutralLanguageModelProviderV1:
    provider_identifier: str
    _provider: ProviderChoiceV1
    _workflow: ScoutWorkflowExecutionV1
    _runtime: EditorGenerationRuntimeAuthorityV1
    _fingerprint: EditorRequestFingerprintAuthorityV1
    _request: EditorGenerationRequestAuthorityV1
    _clock: EditorGenerationClockV1
    _cancellation: EditorGenerationCancellationSourceV1
    _references: EditorGenerationReferenceFactoryV1
    _recorder: EditorGenerationAttemptRecorderV1

    def __init__(
        self,
        *,
        provider: ProviderChoiceV1,
        workflow: ScoutWorkflowExecutionV1,
        runtime_authority: EditorGenerationRuntimeAuthorityV1,
        fingerprint_authority: EditorRequestFingerprintAuthorityV1,
        request_authority: EditorGenerationRequestAuthorityV1,
        requested_at_factory: EditorGenerationClockV1,
        cancellation_source: EditorGenerationCancellationSourceV1,
        request_reference_factory: EditorGenerationReferenceFactoryV1,
        attempt_recorder: EditorGenerationAttemptRecorderV1,
    ) -> None:
        dependencies = (
            provider,
            workflow,
            runtime_authority,
            fingerprint_authority,
            request_authority,
            requested_at_factory,
            cancellation_source,
            request_reference_factory,
            attempt_recorder,
        )
        if not _dependencies(*dependencies):
            del self, dependencies, provider, workflow, runtime_authority
            del fingerprint_authority, request_authority, requested_at_factory
            del cancellation_source, request_reference_factory, attempt_recorder
            _raise_adapter()
        values = (provider.value, *dependencies)
        for name, value in zip(_FIELDS, values, strict=True):
            object.__setattr__(self, name, value)

    def generate_structured(
        self,
        *,
        prompt: GenerationPrompt,
        output_schema: type[T],
        config: LanguageGenerationConfig,
    ) -> T:
        outcome, value = _generate(self, prompt, output_schema, config)
        del self, prompt, output_schema, config
        if outcome == "structured":
            error = value
            del outcome, value
            raise error from None
        if outcome != "success":
            del value
            _raise_provider(outcome)
        return value

    def __repr__(self) -> str:
        _state(self)
        return "EditorNeutralLanguageModelProviderV1(<injected authorities>)"

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        left, right = _state(self), _state(other)
        return all(first is second for first, second in zip(left, right, strict=True))

    def __copy__(self) -> EditorNeutralLanguageModelProviderV1:
        values = _state(self)
        return type(self)(
            provider=values[0],
            workflow=values[1],
            runtime_authority=values[2],
            fingerprint_authority=values[3],
            request_authority=values[4],
            requested_at_factory=values[5],
            cancellation_source=values[6],
            request_reference_factory=values[7],
            attempt_recorder=values[8],
        )

    def __deepcopy__(
        self, memo: dict[int, object]
    ) -> EditorNeutralLanguageModelProviderV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorNeutralLanguageModelProviderV1 does not support pickle")


_FIELDS = (
    "provider_identifier",
    "_provider",
    "_workflow",
    "_runtime",
    "_fingerprint",
    "_request",
    "_clock",
    "_cancellation",
    "_references",
    "_recorder",
)


def _state(value: object) -> tuple[object, ...]:
    try:
        if type(value) is not EditorNeutralLanguageModelProviderV1:
            raise TypeError
        values = tuple(object.__getattribute__(value, name) for name in _FIELDS)
        if values[0] != values[1].value or not _dependencies(*values[1:]):
            raise TypeError
        return values[1:]
    except Exception:  # noqa: BLE001
        _raise_adapter()


def _dependencies(
    provider,
    workflow,
    runtime,
    fingerprint,
    request,
    clock,
    cancellation,
    references,
    recorder,
) -> bool:
    if (
        type(provider) is not ProviderChoiceV1
        or type(workflow) is not ScoutWorkflowExecutionV1
        or type(runtime) is not EditorGenerationRuntimeAuthorityV1
        or type(fingerprint) is not EditorRequestFingerprintAuthorityV1
        or type(request) is not EditorGenerationRequestAuthorityV1
    ):
        return False
    try:
        rebuilt = copy.copy(runtime)
        if rebuilt != runtime or rebuilt.options.provider is not provider:
            return False
    except Exception:  # noqa: BLE001
        return False
    return (
        _method(clock, "now", (), datetime)
        and _method(cancellation, "snapshot", (), CancellationTokenV2)
        and _method(
            references,
            "create",
            (
                ("prompt_fingerprint", inspect.Parameter.KEYWORD_ONLY, str),
                ("attempt_number", inspect.Parameter.KEYWORD_ONLY, int),
            ),
            str,
        )
        and _method(
            recorder,
            "record",
            (
                (
                    "observation",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    EditorGenerationAttemptObservationV1,
                ),
            ),
            type(None),
        )
        and _method(
            recorder, "snapshot", (), tuple[EditorGenerationAttemptObservationV1, ...]
        )
    )


def _method(value, name, expected, returns) -> bool:
    try:
        custom_getattribute = inspect.getattr_static(type(value), "__getattribute__")
        custom_getattr = inspect.getattr_static(type(value), "__getattr__", None)
        if (
            custom_getattribute is not object.__getattribute__
            or custom_getattr is not None
        ):
            return False
        try:
            instance_state = object.__getattribute__(value, "__dict__")
        except AttributeError:
            instance_state = {}
        if type(instance_state) is not dict:
            return False
        if name in instance_state:
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
        return (
            all(
                parameter.name == spec[0]
                and parameter.kind is spec[1]
                and parameter.default is inspect.Parameter.empty
                and hints.get(parameter.name) == spec[2]
                for parameter, spec in zip(parameters[1:], expected, strict=True)
            )
            and hints.get("return") == returns
        )
    except Exception:  # noqa: BLE001
        return False


def _generate(adapter, prompt, schema, config):
    try:
        (
            provider,
            workflow,
            runtime,
            fingerprint,
            authority,
            clock,
            cancellation_source,
            references,
            recorder,
        ) = _state(adapter)
        prompt = _prompt(prompt)
        config = _config(config)
        if schema not in _ALLOWED or not _matches(provider, runtime, config):
            return "internal", None
        schema_json, schema_hash = _schema(schema)
        history = _history(recorder.snapshot())
        attempt = len(history) + 1
        reference = references.create(
            prompt_fingerprint=prompt.prompt_fingerprint, attempt_number=attempt
        )
        if not _text(reference, 120) or reference in {
            item.request_reference for item in history
        }:
            return "internal", None
        requested_at = clock.now()
        if (
            type(requested_at) is not datetime
            or requested_at.tzinfo is None
            or requested_at.utcoffset() is None
        ):
            return "internal", None
        cancellation = cancellation_source.snapshot()
        if type(cancellation) is not CancellationTokenV2:
            return "internal", None
        cancellation = CancellationTokenV2.model_validate(
            cancellation.model_dump(mode="python", warnings=False), strict=True
        )
        application = _EditorGenerationApplicationRequestBuilderV1(fingerprint).build(
            provider=provider,
            prompt=prompt.text,
            request_reference=reference,
            requested_at=requested_at,
            options=runtime.options,
            output_schema_name=schema.__name__,
            output_schema_canonical_json=schema_json,
            output_schema_fingerprint=schema_hash,
            cancellation=cancellation,
        )
        lower = authority.build(application, runtime)
        if cancellation.cancellation_requested:
            _record(
                recorder,
                attempt,
                prompt.prompt_fingerprint,
                application,
                lower,
                ExecutionOutcomeV2.CANCELLED,
                None,
            )
            return "cancelled", None
        result = copy.copy(
            workflow.execute_provider_neutral(ScoutRuntimeRequestV1(True, lower))
        )
        if type(result) is not ScoutRuntimeResultV1:
            return "internal", None
        execution = result.provider_result
        if type(execution) is not ProviderExecutionResultV2 or not _lineage(
            execution, lower
        ):
            return "internal", None
        _record(
            recorder,
            attempt,
            prompt.prompt_fingerprint,
            application,
            lower,
            execution.outcome,
            execution,
        )
        if execution.outcome is ExecutionOutcomeV2.TIMEOUT:
            return "timeout", None
        if execution.outcome is ExecutionOutcomeV2.CANCELLED:
            return "cancelled", None
        if execution.outcome is ExecutionOutcomeV2.PROVIDER_FAILURE:
            return "provider", None
        if execution.outcome is not ExecutionOutcomeV2.COMPLETED:
            return "internal", None
        projection = execution.provider_result
        if (
            projection is None
            or projection.status is not ProviderResultStatusV2.SUCCESS
            or len(projection.outputs) != 1
        ):
            return "internal", None
        output = projection.outputs[0]
        source = lower.request_envelope.request_units[0].source_request_reference
        if (
            output.ordinal != 0
            or output.source_request_reference != source
            or output.finish_reason is not ProviderFinishReasonV2.COMPLETED
        ):
            return "internal", None
        generated_text = output.generated_text
        try:
            model = validate_generated_model(generated_text, schema)
        except ProviderStructuredOutputError as error:
            return "structured", error
        return "success", model
    except Exception:  # noqa: BLE001
        return "internal", None


def _prompt(value):
    if type(value) is not GenerationPrompt:
        raise TypeError
    return GenerationPrompt.model_validate(
        value.model_dump(mode="python", warnings=False), strict=True
    )


def _config(value):
    if type(value) is not LanguageGenerationConfig:
        raise TypeError
    return LanguageGenerationConfig.model_validate(
        value.model_dump(mode="python", warnings=False), strict=True
    )


def _matches(provider, runtime, config) -> bool:
    options = runtime.options
    pairs = (
        (config.temperature, options.temperature),
        (config.top_p, options.top_p),
        (config.timeout_seconds, options.timeout_policy.timeout_seconds),
    )
    return (
        config.provider == provider.value
        and options.provider is provider
        and config.model_identifier == options.model_identifier
        and config.model_revision == options.model_revision
        and all(type(left) is type(right) and left == right for left, right in pairs)
        and config.max_output_tokens == options.max_output_tokens
        and config.seed == options.seed
        and config.structured_output_mode is options.structured_output_mode
        and options.stop_sequences == ()
    )


def _schema(model):
    value = model.model_json_schema()
    _json(value)
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _json(value):
    if value is None or type(value) in {bool, int, str}:
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _json(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _json(item)
        return
    raise TypeError


def _history(value):
    if type(value) is not tuple:
        raise TypeError
    result = tuple(copy.copy(item) for item in value)
    if tuple(item.attempt_number for item in result) != tuple(
        range(1, len(result) + 1)
    ):
        raise TypeError
    if len({item.request_reference for item in result}) != len(result):
        raise TypeError
    return result


def _text(value, maximum):
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= maximum
    )


def _lineage(result, request):
    return (
        result.request_id == request.context.request_id
        and result.provider_id == request.provider.provider_id
        and result.request_envelope_identity == request.request_envelope.identity
    )


def _record(recorder, number, prompt_hash, application, lower, outcome, execution):
    projection = execution.provider_result if execution is not None else None
    output = (
        projection.outputs[0]
        if projection is not None and len(projection.outputs) == 1
        else None
    )
    recorder.record(
        EditorGenerationAttemptObservationV1(
            number,
            prompt_hash,
            application.request_reference,
            application.request_fingerprint,
            lower.context.request_id,
            lower.request_envelope.identity,
            lower.provider.provider_id,
            outcome,
            output.source_request_reference if output is not None else None,
            output.finish_reason if output is not None else None,
            (
                execution.failure_code
                if execution is not None
                else "cancelled-before-dispatch"
            ),
        )
    )


__all__ = ("EditorNeutralLanguageModelProviderV1",)

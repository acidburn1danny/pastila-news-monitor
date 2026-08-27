"""Provider-blind operational coordinator for Editor generation."""

from __future__ import annotations

import copy
import inspect
import logging
from dataclasses import dataclass
from itertools import pairwise
from types import FunctionType
from typing import NoReturn, get_type_hints

from pastila_scout.editor.generation.controlled_generator import (
    ControlledGenerationError,
    ControlledGenerator,
)
from pastila_scout.editor.generation.manifest import GenerationManifest
from pastila_scout.editor.generation.models import (
    ControlledGenerationResult,
    EpisodeDraft,
    GenerationComponentType,
    GenerationTrace,
    LanguageGenerationConfig,
)
from pastila_scout.editor.generation.provider import LanguageModelProvider
from pastila_scout.editor.generation.semantic_draft_v2 import (
    ControlledSemanticGenerationResultV2,
    PastilaEditorSemanticDraftV2,
    SemanticGenerationStateV2,
)
from pastila_scout.editor.generation.state import EpisodeGenerationState
from pastila_scout.editor_generation_authority_v1.canonical import (
    canonical_value,
    semantic_fingerprint,
)
from pastila_scout.editor_generation_execution_v1 import (
    EditorGenerationExecutionRequestV1,
)
from pastila_scout.editor_generation_execution_v1.models import (
    reconstruct_execution_request,
)
from pastila_scout.editor_generation_provider_adapter_v1 import (
    EditorGenerationAttemptObservationV1,
)
from pastila_scout.editor_generation_runtime_v1 import (
    EditorGenerationRuntimeCompositionError,
    EditorGenerationRuntimeSessionFactoryV1,
    EditorGenerationRuntimeSessionV1,
)
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2

from .errors import EditorOperationalExecutionConfigurationError
from .models import (
    CANCELLED_LIFECYCLE,
    COMPLETED_LIFECYCLE,
    CONTROLLED_RESULT_FAILURE_LIFECYCLE,
    GENERATION_FAILURE_LIFECYCLE,
    INVALID_REQUEST_LIFECYCLE,
    RUNTIME_FAILURE_LIFECYCLE,
    EditorOperationalGenerationFailureCodeV1,
    EditorOperationalGenerationStatusV1,
    EditorOperationalResultV1,
    make_failure,
    result_fingerprint,
)
from .protocols import _EditorControlledGeneratorFactoryV1

_LOGGER = logging.getLogger(__name__)


def _raise_configuration() -> NoReturn:
    error = EditorOperationalExecutionConfigurationError(
        "Editor operational execution configuration is invalid."
    )
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorOperationalExecutionCoordinatorV1:
    _session_factory: object
    _generator_factory: object

    def __init__(
        self,
        *,
        session_factory: EditorGenerationRuntimeSessionFactoryV1,
        generator_factory: _EditorControlledGeneratorFactoryV1,
    ) -> None:
        valid = _dependencies(session_factory, generator_factory)
        if not valid:
            del self, session_factory, generator_factory, valid
            _raise_configuration()
        object.__setattr__(self, "_session_factory", session_factory)
        object.__setattr__(self, "_generator_factory", generator_factory)

    def execute(
        self, request: EditorGenerationExecutionRequestV1
    ) -> EditorOperationalResultV1:
        valid_state, session_factory, generator_factory = _read_state(self)
        if not valid_state:
            del self, request, valid_state, session_factory, generator_factory
            _raise_configuration()
        try:
            valid = reconstruct_execution_request(request)
        except Exception:  # noqa: BLE001 - caller details collapse here
            del self, request, valid_state, session_factory, generator_factory
            return _failure_result(
                None, EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST
            )
        del self, request, valid_state
        status, result = _execute(valid, session_factory, generator_factory)
        del valid, session_factory, generator_factory
        if status == "configuration":
            del status, result
            _raise_configuration()
        del status
        return result

    def __repr__(self) -> str:
        valid, session, generator = _read_state(self)
        if not valid:
            del self, valid, session, generator
            _raise_configuration()
        del self, valid, session, generator
        return "EditorOperationalExecutionCoordinatorV1(<injected dependencies>)"

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        left_valid, left_session, left_generator = _read_state(self)
        right_valid, right_session, right_generator = _read_state(other)
        if not left_valid or not right_valid:
            del self, other, left_valid, left_session, left_generator
            del right_valid, right_session, right_generator
            _raise_configuration()
        result = left_session is right_session and left_generator is right_generator
        del self, other, left_valid, left_session, left_generator
        del right_valid, right_session, right_generator
        return result

    def __copy__(self):
        valid, session, generator = _read_state(self)
        if not valid:
            del self, valid, session, generator
            _raise_configuration()
        cls = type(self)
        del self, valid
        return cls(session_factory=session, generator_factory=generator)

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol):
        valid, session, generator = _read_state(self)
        if not valid:
            del self, protocol, valid, session, generator
            _raise_configuration()
        del self, protocol, valid, session, generator
        raise TypeError(
            "EditorOperationalExecutionCoordinatorV1 does not support pickle"
        )


def _execute(request, session_factory, generator_factory):
    session = None
    generated = None
    terminal_error = None
    attempts = ()
    provenance_valid = False
    try:
        session = session_factory.open(
            request.runtime_options,
            operation_reference=request.request_reference,
        )
        if type(session) is not EditorGenerationRuntimeSessionV1:
            raise EditorGenerationRuntimeCompositionError()
    except Exception:  # noqa: BLE001 - runtime details remain private
        return (
            "result",
            _failure_result(
                request,
                EditorOperationalGenerationFailureCodeV1.RUNTIME_COMPOSITION_FAILED,
            ),
        )
    dependency_failed = False
    try:
        generator = generator_factory.create(
            provider=session.adapter,
            config=request.generation_configuration,
        )
        if type(generator) is not ControlledGenerator:
            raise TypeError
        generated = generator.generate(
            scout_input=request.plan.source_input,
            selection_profile=request.plan.selection_profile,
            episode_context=request.plan.episode_context,
            flow_result=request.flow_result,
            editorial_blueprint=request.editorial_blueprint,
            commentary_blueprint=request.commentary_blueprint,
            voice_plan=request.voice_plan,
            static_cta_content="",
            teleprompter_profile=None,
        )
    except ControlledGenerationError as exc:
        terminal_error = str(exc)[:4000]
        _LOGGER.error(
            "Editor controlled generation failed: %s",
            terminal_error,
        )
    except Exception:  # noqa: BLE001 - injected failure becomes neutral status
        dependency_failed = True
    try:
        recorder = session.attempt_recorder
        snapshot = recorder.snapshot()
        attempts = _validate_provenance(
            snapshot,
            request.provider.value,
            generated,
            terminal_error,
        )
        provenance_valid = True
    except Exception:  # noqa: BLE001 - malformed provenance is suppressed
        attempts = ()
        provenance_valid = False
    if dependency_failed:
        candidate = None
    else:
        try:
            candidate = _classify(
                request, generated, terminal_error, attempts, provenance_valid
            )
        except Exception:  # noqa: BLE001 - package-owned classification boundary
            candidate = _failure_result(
                request,
                EditorOperationalGenerationFailureCodeV1.INTERNAL_EXECUTION_FAILURE,
                attempts=attempts if provenance_valid else (),
            )
    try:
        session.close()
    except Exception:  # noqa: BLE001 - cleanup has final precedence
        return (
            "result",
            _failure_result(
                request,
                EditorOperationalGenerationFailureCodeV1.CLEANUP_FAILED,
                attempts=attempts if provenance_valid else (),
                cleanup_failed=True,
            ),
        )
    if dependency_failed:
        return "configuration", None
    return "result", candidate


def _classify(request, generated, terminal_error, attempts, valid):
    if not valid:
        return _failure_result(
            request,
            EditorOperationalGenerationFailureCodeV1.ATTEMPT_PROVENANCE_INVALID,
        )
    terminal = attempts[-1].outcome if attempts else None
    if terminal is ExecutionOutcomeV2.CANCELLED:
        return _failure_result(
            request,
            EditorOperationalGenerationFailureCodeV1.CANCELLED,
            attempts=attempts,
        )
    if _timeout_exhausted(attempts):
        return _failure_result(
            request,
            EditorOperationalGenerationFailureCodeV1.TIMEOUT_EXHAUSTED,
            attempts=attempts,
        )
    if terminal is ExecutionOutcomeV2.PROVIDER_FAILURE:
        return _failure_result(
            request,
            EditorOperationalGenerationFailureCodeV1.PROVIDER_FAILED,
            attempts=attempts,
        )
    if terminal_error is not None:
        return _failure_result(
            request,
            EditorOperationalGenerationFailureCodeV1.CONTROLLED_GENERATION_FAILED,
            attempts=attempts,
        )
    try:
        result = _reconstruct_controlled(generated)
        _validate_trace(result.trace, attempts, request.provider.value)
    except Exception:  # noqa: BLE001 - controlled result details remain private
        return _failure_result(
            request,
            EditorOperationalGenerationFailureCodeV1.CONTROLLED_RESULT_INVALID,
            attempts=attempts,
            controlled_result=True,
        )
    try:
        return _completed_result(request, result, attempts)
    except Exception:  # noqa: BLE001 - finite result-construction boundary
        return _failure_result(
            request,
            EditorOperationalGenerationFailureCodeV1.INTERNAL_EXECUTION_FAILURE,
            attempts=attempts,
        )


def _validate_provenance(snapshot, provider, generated, terminal_error):
    if type(snapshot) is not tuple:
        raise TypeError
    values = tuple(copy.copy(item) for item in snapshot)
    if any(type(item) is not EditorGenerationAttemptObservationV1 for item in values):
        raise TypeError
    if tuple(item.attempt_number for item in values) != tuple(
        range(1, len(values) + 1)
    ):
        raise TypeError
    if len({item.request_reference for item in values}) != len(values):
        raise TypeError
    identities = {
        tuple(object.__getattribute__(item, name) for name in item.__dataclass_fields__)
        for item in values
    }
    if len(identities) != len(values) or any(
        item.provider_id != provider for item in values
    ):
        raise TypeError
    groups = _groups(values)
    for index, group in enumerate(groups):
        last = index == len(groups) - 1
        if len(group) == 2:
            if group[0].outcome is not ExecutionOutcomeV2.TIMEOUT:
                raise TypeError
        elif len(group) != 1:
            raise TypeError
        terminal = group[-1].outcome
        if not last and terminal is not ExecutionOutcomeV2.COMPLETED:
            raise TypeError
        if (
            last
            and terminal is ExecutionOutcomeV2.TIMEOUT
            and terminal_error is None
        ):
            raise TypeError
    if generated is not None and not values:
        raise TypeError
    return values


def _groups(attempts):
    groups = []
    for item in attempts:
        if groups and groups[-1][0].prompt_fingerprint == item.prompt_fingerprint:
            groups[-1].append(item)
        else:
            groups.append([item])
    return tuple(tuple(group) for group in groups)


def _timeout_exhausted(attempts):
    return (
        len(attempts) >= 2
        and attempts[-2].prompt_fingerprint == attempts[-1].prompt_fingerprint
        and attempts[-2].outcome is ExecutionOutcomeV2.TIMEOUT
        and attempts[-1].outcome is ExecutionOutcomeV2.TIMEOUT
    )


def _validate_trace(trace, attempts, provider):
    nodes = trace.attempts
    provider_nodes = []
    for node in nodes:
        if node.provider_identifier == provider:
            provider_nodes.append(node)
        elif not (
            node.provider_identifier == "deterministic-local"
            and node.component_type
            in {
                GenerationComponentType.ASSEMBLY,
                GenerationComponentType.TELEPROMPTER_FORMATTING,
            }
        ):
            raise TypeError
    collapsed = tuple(group[-1].prompt_fingerprint for group in _groups(attempts))
    if collapsed != tuple(node.prompt_fingerprint for node in provider_nodes):
        raise TypeError


def _reconstruct_controlled(value):
    result_type = type(value)
    if result_type is ControlledGenerationResult:
        draft_model = EpisodeDraft
        state_model = EpisodeGenerationState
    elif result_type is ControlledSemanticGenerationResultV2:
        draft_model = PastilaEditorSemanticDraftV2
        state_model = SemanticGenerationStateV2
    else:
        raise TypeError
    if (
        type(value.draft) is not draft_model
        or type(value.trace) is not GenerationTrace
        or type(value.manifest) is not GenerationManifest
        or type(value.final_state) is not state_model
    ):
        raise TypeError
    draft = draft_model.model_validate(
        value.draft.model_dump(mode="python", warnings=False), strict=True
    )
    trace = GenerationTrace.model_validate(
        value.trace.model_dump(mode="python", warnings=False), strict=True
    )
    manifest = GenerationManifest.model_validate(
        value.manifest.model_dump(mode="python", warnings=False), strict=True
    )
    final_state = state_model.model_validate(
        value.final_state.model_dump(mode="python", warnings=False), strict=True
    )
    return result_type(
        draft=draft,
        trace=trace,
        manifest=manifest,
        final_state=final_state,
    )


def _completed_result(request, generated, attempts):
    prefix = _lineage(request)
    timeout_count = sum(
        1
        for left, right in pairwise(attempts)
        if left.outcome is ExecutionOutcomeV2.TIMEOUT
        and left.prompt_fingerprint == right.prompt_fingerprint
    )
    values = (
        *prefix,
        EditorOperationalGenerationStatusV1.COMPLETED,
        COMPLETED_LIFECYCLE,
        generated.draft,
        generated.trace,
        generated.manifest,
        generated.final_state.revision,
        attempts,
        len(attempts),
        timeout_count,
        None,
        False,
    )
    return EditorOperationalResultV1(*values, result_fingerprint(values))


def _failure_result(
    request, code, *, attempts=(), cleanup_failed=False, controlled_result=False
):
    failure = make_failure(code)
    if request is None:
        lineage = ("", "", "", "", "")
    else:
        lineage = _lineage(request)
    status = (
        EditorOperationalGenerationStatusV1.CANCELLED
        if code is EditorOperationalGenerationFailureCodeV1.CANCELLED
        else EditorOperationalGenerationStatusV1.FAILED
    )
    if code is EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST:
        lifecycle = INVALID_REQUEST_LIFECYCLE
    elif code is EditorOperationalGenerationFailureCodeV1.RUNTIME_COMPOSITION_FAILED:
        lifecycle = RUNTIME_FAILURE_LIFECYCLE
    elif controlled_result:
        lifecycle = CONTROLLED_RESULT_FAILURE_LIFECYCLE
    elif status is EditorOperationalGenerationStatusV1.CANCELLED:
        lifecycle = CANCELLED_LIFECYCLE
    else:
        lifecycle = GENERATION_FAILURE_LIFECYCLE
    if code is EditorOperationalGenerationFailureCodeV1.ATTEMPT_PROVENANCE_INVALID:
        attempts = ()
    timeout_count = sum(
        1
        for left, right in pairwise(attempts)
        if left.outcome is ExecutionOutcomeV2.TIMEOUT
        and left.prompt_fingerprint == right.prompt_fingerprint
    )
    values = (
        *lineage,
        status,
        lifecycle,
        None,
        None,
        None,
        None,
        attempts,
        len(attempts),
        timeout_count,
        failure,
        cleanup_failed,
    )
    return EditorOperationalResultV1(*values, result_fingerprint(values))


def _lineage(request):
    return (
        request.plan.source_report_id,
        request.plan.source_report_fingerprint,
        semantic_fingerprint(canonical_value(request.preparation)),
        request.request_reference,
        request.request_fingerprint,
    )


def _method(value, name, parameters, returns):
    try:
        value_type = type(value)
        if (
            value_type.__getattribute__ is not object.__getattribute__
            or "__getattr__" in value_type.__dict__
        ):
            return False
        if hasattr(value, "__dict__") and name in object.__getattribute__(
            value, "__dict__"
        ):
            return False
        descriptor = inspect.getattr_static(value_type, name)
        if (
            type(descriptor) is not FunctionType
            or hasattr(descriptor, "__signature__")
            or hasattr(descriptor, "__wrapped__")
        ):
            return False
        signature = inspect.signature(descriptor, follow_wrapped=False)
        hints = get_type_hints(descriptor)
        actual = tuple(signature.parameters.values())
        return (
            len(actual) == len(parameters) + 1
            and actual[0].name == "self"
            and all(
                item.name == expected[0]
                and item.kind is expected[1]
                and item.default is inspect.Parameter.empty
                and hints.get(item.name) == expected[2]
                for item, expected in zip(actual[1:], parameters, strict=True)
            )
            and hints.get("return") == returns
        )
    except Exception:  # noqa: BLE001
        return False


def _dependencies(session, generator):
    return _method(
        session,
        "open",
        (
            (
                "options",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                __import__(
                    "pastila_scout.editor_generation_authority_v1",
                    fromlist=["EditorGenerationRuntimeOptionsV1"],
                ).EditorGenerationRuntimeOptionsV1,
            ),
            ("operation_reference", inspect.Parameter.KEYWORD_ONLY, str),
        ),
        EditorGenerationRuntimeSessionV1,
    ) and _method(
        generator,
        "create",
        (
            ("provider", inspect.Parameter.KEYWORD_ONLY, LanguageModelProvider),
            ("config", inspect.Parameter.KEYWORD_ONLY, LanguageGenerationConfig),
        ),
        ControlledGenerator,
    )


def _read_state(value):
    try:
        if type(value) is not EditorOperationalExecutionCoordinatorV1:
            return False, None, None
        session = object.__getattribute__(value, "_session_factory")
        generator = object.__getattribute__(value, "_generator_factory")
        if not _dependencies(session, generator):
            return False, None, None
        return True, session, generator
    except Exception:  # noqa: BLE001 - copied-invalid dependency state is isolated
        return False, None, None


__all__ = ("EditorOperationalExecutionCoordinatorV1",)

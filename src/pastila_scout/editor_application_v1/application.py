"""Application-owned orchestration for one operational Editor execution."""

from __future__ import annotations

import copy
import inspect
import stat
from dataclasses import dataclass
from functools import partial
from types import FunctionType
from typing import NoReturn, get_type_hints

from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.identity import verify_scout_input_identity
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor.blueprint_builder import EditorialBlueprintBuilder
from pastila_scout.editor.commentary_builder import CommentaryBlueprintBuilder
from pastila_scout.editor.engine import EditorialSelectionResult
from pastila_scout.editor.flow_optimizer import EpisodeFlowOptimizer
from pastila_scout.editor.voice_builder import VoiceModelBuilder
from pastila_scout.editor_generation_execution_request_authority_v1 import (
    EditorGenerationExecutionRequestAuthorityError,
    EditorGenerationExecutionRequestAuthorityV1,
)
from pastila_scout.editor_generation_execution_v1 import (
    EditorGenerationExecutionRequestV1,
)
from pastila_scout.editor_operational_execution_v1 import (
    EditorOperationalExecutionCoordinatorV1,
    EditorOperationalGenerationFailureCodeV1,
    EditorOperationalGenerationStatusV1,
    EditorOperationalResultV1,
)
from pastila_scout.editor_operational_v1 import (
    EditorGenerationPlanV1,
    EditorOperationalCoordinatorV1,
    EditorOperationalPreparationResultV1,
)

from .configuration import EditorApplicationGenerationConfigurationAuthorityV1
from .errors import (
    EditorApplicationConfigurationError,
    EditorApplicationCoordinatorError,
    EditorApplicationExportError,
    EditorApplicationSerializationError,
    raise_configuration_error,
)
from .export import EditorAtomicExporterV1
from .models import (
    EditorApplicationExitCodeV1,
    EditorApplicationFailureCodeV1,
    EditorApplicationLifecycleStateV1,
    EditorApplicationRequestV1,
    EditorApplicationResultV1,
    EditorApplicationStatusV1,
    EditorOutputDestinationV1,
    EditorOverwritePolicyV1,
    make_application_failure,
    reconstruct_application_request,
    reconstruct_application_result,
    reconstruct_generation_configuration,
    reconstruct_output_destination,
)
from .protocols import (
    _EditorArtifactDependencyV1,
    _EditorDeterministicArtifactsV1,
    _EditorExecutionRequestAuthorityDependencyV1,
    _EditorExporterDependencyV1,
    _EditorOperationalExecutionDependencyV1,
    _EditorPreparationDependencyV1,
    _EditorSerializerDependencyV1,
)
from .serialization import (
    EditorOperationalResultSerializerV1,
    EditorSerializedOperationalResultV1,
)

_ACCEPTED_FAILED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.FAILED,
)
_VALIDATED_FAILED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.FAILED,
)
_PREPARED_FAILED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.PREPARED,
    EditorApplicationLifecycleStateV1.FAILED,
)
_EXECUTED_FAILED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.PREPARED,
    EditorApplicationLifecycleStateV1.EXECUTED,
    EditorApplicationLifecycleStateV1.FAILED,
)
_SERIALIZED_FAILED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.PREPARED,
    EditorApplicationLifecycleStateV1.EXECUTED,
    EditorApplicationLifecycleStateV1.SERIALIZED,
    EditorApplicationLifecycleStateV1.FAILED,
)
_INITIAL_CANCELLED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.CANCELLED,
)
_EXECUTED_CANCELLED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.PREPARED,
    EditorApplicationLifecycleStateV1.EXECUTED,
    EditorApplicationLifecycleStateV1.CANCELLED,
)
_COMPLETED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.PREPARED,
    EditorApplicationLifecycleStateV1.EXECUTED,
    EditorApplicationLifecycleStateV1.SERIALIZED,
    EditorApplicationLifecycleStateV1.EXPORTED,
    EditorApplicationLifecycleStateV1.COMPLETED,
)


class _CompletedApplicationCandidateIntegrityError(Exception):
    __slots__ = ()


@dataclass(frozen=True, slots=True, repr=False)
class _CompletedApplicationCandidateStateV1:
    operational_result: EditorOperationalResultV1
    destination: EditorOutputDestinationV1
    serialized: EditorSerializedOperationalResultV1


@dataclass(frozen=True, slots=True, repr=False, eq=False, init=False)
class EditorApplicationCoordinatorV1:
    _preparation: object
    _artifacts: object
    _execution_request_authority: object
    _operational_execution: object
    _serializer: object
    _exporter: object
    _identity: tuple[int, ...]

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Editor application coordinators cannot be subclassed")

    def __init__(
        self,
        *,
        preparation: _EditorPreparationDependencyV1,
        artifacts: _EditorArtifactDependencyV1,
        execution_request_authority: _EditorExecutionRequestAuthorityDependencyV1,
        operational_execution: _EditorOperationalExecutionDependencyV1,
        serializer: _EditorSerializerDependencyV1,
        exporter: _EditorExporterDependencyV1,
    ) -> None:
        dependencies = (
            preparation,
            artifacts,
            execution_request_authority,
            operational_execution,
            serializer,
            exporter,
        )
        if not _valid_dependencies(dependencies):
            del self, dependencies, preparation, artifacts
            del execution_request_authority, operational_execution, serializer, exporter
            raise_configuration_error()
        for name, value in zip(
            (
                "_preparation",
                "_artifacts",
                "_execution_request_authority",
                "_operational_execution",
                "_serializer",
                "_exporter",
            ),
            dependencies,
            strict=True,
        ):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_identity", tuple(id(item) for item in dependencies))

    def execute(
        self, *, request: EditorApplicationRequestV1
    ) -> EditorApplicationResultV1:
        dependencies = _validated_dependencies(self)
        try:
            valid_request = reconstruct_application_request(request)
        except EditorApplicationConfigurationError:
            request_code = _request_failure_code(request)
            del self, request, dependencies
            return _failure(
                None,
                _ACCEPTED_FAILED,
                None,
                request_code,
                EditorApplicationExitCodeV1.INVALID_INPUT,
            )
        del request
        reference = valid_request.operation_reference
        destination_status = _destination_status(valid_request.destination)
        if destination_status is not None:
            del self, dependencies
            return _failure(
                reference,
                _VALIDATED_FAILED,
                None,
                destination_status,
                EditorApplicationExitCodeV1.INVALID_INPUT,
            )
        if valid_request.cancellation.cancellation_requested:
            del self, dependencies
            return _cancelled(reference, _INITIAL_CANCELLED, None)
        (
            preparation_dependency,
            artifact_dependency,
            authority,
            execution,
            serializer,
            exporter,
        ) = dependencies
        try:
            preparation = preparation_dependency.prepare(
                scout_input=valid_request.scout_input,
                selection_profile=valid_request.selection_profile,
                episode_context=valid_request.episode_context,
            )
            preparation = copy.copy(preparation)
        except Exception:  # noqa: BLE001 - dependency defect is not an outcome
            del self, valid_request, dependencies, preparation_dependency
            del artifact_dependency, authority, execution, serializer, exporter
            _raise_coordinator_error()
        if (
            type(preparation) is not EditorOperationalPreparationResultV1
            or preparation.plan is None
        ):
            del self, dependencies
            return _failure(
                reference,
                _VALIDATED_FAILED,
                None,
                EditorApplicationFailureCodeV1.PREPARATION_FAILED,
                EditorApplicationExitCodeV1.EXECUTION_FAILED,
            )
        try:
            artifacts = artifact_dependency.build(plan=preparation.plan)
            artifacts = copy.copy(artifacts)
            artifacts = _reconstruct_artifacts(artifacts, preparation.plan)
        except (TypeError, ValueError):
            del self, dependencies, artifact_dependency
            return _failure(
                reference,
                _VALIDATED_FAILED,
                None,
                EditorApplicationFailureCodeV1.PREPARATION_FAILED,
                EditorApplicationExitCodeV1.EXECUTION_FAILED,
            )
        except Exception:  # noqa: BLE001 - unenumerated artifact defect
            del self, dependencies, artifact_dependency
            _raise_coordinator_error()
        materialized = None
        try:
            materialized = (
                EditorApplicationGenerationConfigurationAuthorityV1()._materialize(
                    configuration=valid_request.generation_configuration
                )
            )
            execution_request = authority.construct(
                preparation=preparation,
                plan=preparation.plan,
                flow_result=artifacts.flow_result,
                editorial_blueprint=artifacts.editorial_blueprint,
                commentary_blueprint=artifacts.commentary_blueprint,
                voice_plan=artifacts.voice_plan,
                generation_configuration=materialized.generation_configuration,
                runtime_options=materialized.runtime_options,
                provider=valid_request.generation_configuration.provider,
                requested_at=valid_request.requested_at,
                request_reference=reference,
                cancellation=valid_request.cancellation,
            )
        except EditorGenerationExecutionRequestAuthorityError:
            del self, dependencies, materialized
            return _failure(
                reference,
                _PREPARED_FAILED,
                None,
                EditorApplicationFailureCodeV1.EXECUTION_REQUEST_CONSTRUCTION_FAILED,
                EditorApplicationExitCodeV1.EXECUTION_FAILED,
            )
        except Exception:  # noqa: BLE001 - unenumerated authority defect
            del self, dependencies, materialized
            _raise_coordinator_error()
        try:
            execution_request = copy.copy(execution_request)
        except Exception:  # noqa: BLE001 - malformed authority output
            del self, dependencies, execution_request
            return _failure(
                reference,
                _PREPARED_FAILED,
                None,
                EditorApplicationFailureCodeV1.EXECUTION_REQUEST_CONSTRUCTION_FAILED,
                EditorApplicationExitCodeV1.EXECUTION_FAILED,
            )
        if type(execution_request) is not EditorGenerationExecutionRequestV1:
            del self, dependencies, execution_request
            return _failure(
                reference,
                _PREPARED_FAILED,
                None,
                EditorApplicationFailureCodeV1.EXECUTION_REQUEST_CONSTRUCTION_FAILED,
                EditorApplicationExitCodeV1.EXECUTION_FAILED,
            )
        operational = None
        try:
            operational = execution.execute(request=execution_request)
            operational = copy.copy(operational)
        except Exception:  # noqa: BLE001 - unenumerated execution defect
            del self, dependencies, execution_request, operational
            _raise_coordinator_error()
        if operational.status is EditorOperationalGenerationStatusV1.CANCELLED:
            del self, dependencies
            return _cancelled(reference, _EXECUTED_CANCELLED, operational)
        if operational.status is not EditorOperationalGenerationStatusV1.COMPLETED:
            if (
                operational.failure is not None
                and operational.failure.code
                is EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST
            ):
                del self, dependencies, execution_request, operational
                return _failure(
                    reference,
                    _EXECUTED_FAILED,
                    None,
                    EditorApplicationFailureCodeV1.INVALID_EXECUTION_REQUEST,
                    EditorApplicationExitCodeV1.EXECUTION_FAILED,
                )
            exit_code = _operational_exit(operational)
            del self, dependencies
            return _failure(
                reference,
                _EXECUTED_FAILED,
                operational,
                EditorApplicationFailureCodeV1.OPERATIONAL_EXECUTION_FAILED,
                exit_code,
            )
        try:
            serialized = serializer.serialize(result=operational)
        except EditorApplicationSerializationError:
            del self, dependencies
            return _failure(
                reference,
                _EXECUTED_FAILED,
                operational,
                EditorApplicationFailureCodeV1.SERIALIZATION_FAILED,
                EditorApplicationExitCodeV1.OUTPUT_FAILED,
            )
        except Exception:  # noqa: BLE001 - unenumerated serializer defect
            del self, dependencies
            _raise_coordinator_error()
        state = _CompletedApplicationCandidateStateV1(
            operational, valid_request.destination, serialized
        )
        try:
            completed = _reconstruct_completed_application_candidate(state=state)
        except _CompletedApplicationCandidateIntegrityError:
            del self, dependencies, state, serialized
            return _failure(
                reference,
                _SERIALIZED_FAILED,
                operational,
                EditorApplicationFailureCodeV1.INTERNAL_APPLICATION_FAILURE,
                EditorApplicationExitCodeV1.CLEANUP_OR_INTERNAL_FAILURE,
            )
        try:
            exporter.publish(
                payload=serialized.payload, destination=valid_request.destination
            )
        except EditorApplicationExportError:
            del self, dependencies, serialized, completed
            return _failure(
                reference,
                _SERIALIZED_FAILED,
                operational,
                EditorApplicationFailureCodeV1.EXPORT_FAILED,
                EditorApplicationExitCodeV1.OUTPUT_FAILED,
            )
        except Exception:  # noqa: BLE001 - unenumerated exporter defect
            del self, dependencies, serialized, completed
            _raise_coordinator_error()
        return completed

    def __repr__(self) -> str:
        _validated_dependencies(self)
        return "EditorApplicationCoordinatorV1(dependencies=<injected>)"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _validated_dependencies(
            self
        ) == _validated_dependencies(other)

    def __copy__(self) -> EditorApplicationCoordinatorV1:
        values = _validated_dependencies(self)
        return EditorApplicationCoordinatorV1(
            preparation=values[0],
            artifacts=values[1],
            execution_request_authority=values[2],
            operational_execution=values[3],
            serializer=values[4],
            exporter=values[5],
        )

    def __deepcopy__(self, memo: dict[int, object]) -> EditorApplicationCoordinatorV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        _validated_dependencies(self)
        del self, protocol
        raise TypeError("EditorApplicationCoordinatorV1 does not support pickle")


def _reconstruct_completed_application_candidate(
    *, state: _CompletedApplicationCandidateStateV1
) -> EditorApplicationResultV1:
    if type(state) is not _CompletedApplicationCandidateStateV1:
        raise _CompletedApplicationCandidateIntegrityError from None
    try:
        operational = copy.copy(object.__getattribute__(state, "operational_result"))
        destination = reconstruct_output_destination(
            object.__getattribute__(state, "destination")
        )
        serialized = copy.copy(object.__getattribute__(state, "serialized"))
    except (
        EditorApplicationConfigurationError,
        EditorApplicationSerializationError,
        TypeError,
        ValueError,
    ):
        raise _CompletedApplicationCandidateIntegrityError from None
    if type(serialized) is not EditorSerializedOperationalResultV1:
        raise _CompletedApplicationCandidateIntegrityError from None
    if (
        operational.status is not EditorOperationalGenerationStatusV1.COMPLETED
        or operational.cleanup_failed
    ):
        raise _CompletedApplicationCandidateIntegrityError from None
    try:
        result = EditorApplicationResultV1(
            operational.execution_request_reference,
            EditorApplicationStatusV1.COMPLETED,
            _COMPLETED,
            operational,
            destination.path,
            serialized.payload_sha256,
            True,
            True,
            None,
            EditorApplicationExitCodeV1.COMPLETED,
        )
        return reconstruct_application_result(result)
    except EditorApplicationConfigurationError:
        raise _CompletedApplicationCandidateIntegrityError from None


def _failure(
    reference, lifecycle, operational, code, exit_code
) -> EditorApplicationResultV1:
    try:
        result = EditorApplicationResultV1(
            reference,
            EditorApplicationStatusV1.FAILED,
            lifecycle,
            operational,
            None,
            None,
            False,
            False,
            make_application_failure(code),
            exit_code,
        )
        return reconstruct_application_result(result)
    except EditorApplicationConfigurationError:
        _raise_coordinator_error()


def _cancelled(reference, lifecycle, operational) -> EditorApplicationResultV1:
    try:
        return reconstruct_application_result(
            EditorApplicationResultV1(
                reference,
                EditorApplicationStatusV1.CANCELLED,
                lifecycle,
                operational,
                None,
                None,
                False,
                False,
                make_application_failure(EditorApplicationFailureCodeV1.CANCELLED),
                EditorApplicationExitCodeV1.CANCELLED,
            )
        )
    except EditorApplicationConfigurationError:
        _raise_coordinator_error()


def _operational_exit(result: EditorOperationalResultV1) -> EditorApplicationExitCodeV1:
    if result.cleanup_failed:
        return EditorApplicationExitCodeV1.CLEANUP_OR_INTERNAL_FAILURE
    if (
        result.failure
        and result.failure.code
        is EditorOperationalGenerationFailureCodeV1.TIMEOUT_EXHAUSTED
    ):
        return EditorApplicationExitCodeV1.TIMEOUT
    return EditorApplicationExitCodeV1.EXECUTION_FAILED


def _destination_status(
    destination: EditorOutputDestinationV1,
) -> EditorApplicationFailureCodeV1 | None:
    try:
        valid = reconstruct_output_destination(destination)
        if valid.overwrite_policy is not EditorOverwritePolicyV1.FAIL_IF_EXISTS:
            return EditorApplicationFailureCodeV1.INVALID_DESTINATION
        parent = valid.path.parent.lstat()
        if not stat.S_ISDIR(parent.st_mode) or stat.S_ISLNK(parent.st_mode):
            return EditorApplicationFailureCodeV1.INVALID_DESTINATION
        try:
            valid.path.lstat()
        except FileNotFoundError:
            return None
        return EditorApplicationFailureCodeV1.DESTINATION_EXISTS
    except Exception:  # noqa: BLE001 - filesystem validation boundary
        return EditorApplicationFailureCodeV1.INVALID_DESTINATION


def _request_failure_code(value: object) -> EditorApplicationFailureCodeV1:
    if type(value) is not EditorApplicationRequestV1:
        return EditorApplicationFailureCodeV1.INVALID_APPLICATION_REQUEST
    try:
        source = object.__getattribute__(value, "scout_input")
        if type(source) is not ScoutEditorInputV1:
            raise TypeError
        source = ScoutEditorInputV1.model_validate(
            source.model_dump(mode="python", warnings=False), strict=True
        )
        verify_scout_input_identity(source)
    except Exception:  # noqa: BLE001 - finite request-field classification
        return EditorApplicationFailureCodeV1.INVALID_SCOUT_INPUT
    try:
        profile = object.__getattribute__(value, "selection_profile")
        if type(profile) is not SelectionProfileV1:
            raise TypeError
        SelectionProfileV1.model_validate(
            profile.model_dump(mode="python", warnings=False), strict=True
        )
    except Exception:  # noqa: BLE001 - finite request-field classification
        return EditorApplicationFailureCodeV1.INVALID_SELECTION_PROFILE
    try:
        context = object.__getattribute__(value, "episode_context")
        if type(context) is not EpisodeContextV1:
            raise TypeError
        EpisodeContextV1.model_validate(
            context.model_dump(mode="python", warnings=False), strict=True
        )
    except Exception:  # noqa: BLE001 - finite request-field classification
        return EditorApplicationFailureCodeV1.INVALID_EPISODE_CONTEXT
    try:
        reconstruct_generation_configuration(
            object.__getattribute__(value, "generation_configuration")
        )
    except Exception:  # noqa: BLE001 - finite request-field classification
        return EditorApplicationFailureCodeV1.INVALID_GENERATION_CONFIGURATION
    try:
        reconstruct_output_destination(object.__getattribute__(value, "destination"))
    except Exception:  # noqa: BLE001 - finite request-field classification
        return EditorApplicationFailureCodeV1.INVALID_DESTINATION
    return EditorApplicationFailureCodeV1.INVALID_APPLICATION_REQUEST


def _reconstruct_artifacts(
    value: object, plan: EditorGenerationPlanV1
) -> _EditorDeterministicArtifactsV1:
    if (
        type(value) is not _EditorDeterministicArtifactsV1
        or type(plan) is not EditorGenerationPlanV1
    ):
        raise TypeError
    if (
        value.editorial_blueprint.flow_order != plan.selected_event_ids
        or value.commentary_blueprint.flow_order != plan.selected_event_ids
        or value.voice_plan.flow_order != plan.selected_event_ids
    ):
        raise TypeError
    return value


_METHODS = ("prepare", "build", "construct", "execute", "serialize", "publish")
_PROTOCOLS = (
    _EditorPreparationDependencyV1,
    _EditorArtifactDependencyV1,
    _EditorExecutionRequestAuthorityDependencyV1,
    _EditorOperationalExecutionDependencyV1,
    _EditorSerializerDependencyV1,
    _EditorExporterDependencyV1,
)


def _valid_dependencies(values: tuple[object, ...]) -> bool:
    return len(values) == 6 and all(
        _valid_method(value, method, protocol)
        for value, method, protocol in zip(values, _METHODS, _PROTOCOLS, strict=True)
    )


def _valid_method(value: object, name: str, protocol: type) -> bool:
    value_type = type(value)
    if (
        value_type.__getattribute__ is not object.__getattribute__
        or "__getattr__" in value_type.__dict__
        or name in getattr(value, "__dict__", {})
    ):
        return False
    try:
        descriptor = inspect.getattr_static(value_type, name)
        expected = inspect.getattr_static(protocol, name)
    except AttributeError:
        return False
    if (
        type(descriptor) is not FunctionType
        or isinstance(descriptor, partial)
        or hasattr(descriptor, "__signature__")
        or hasattr(descriptor, "__wrapped__")
        or bool(getattr(descriptor, "__isabstractmethod__", False))
    ):
        return False
    try:
        actual = tuple(
            (item.name, item.kind, item.default)
            for item in inspect.signature(
                descriptor, follow_wrapped=False
            ).parameters.values()
        )
        normative = tuple(
            (item.name, item.kind, item.default)
            for item in inspect.signature(
                expected, follow_wrapped=False
            ).parameters.values()
        )
        return actual == normative and get_type_hints(descriptor) == get_type_hints(
            expected
        )
    except (NameError, TypeError, ValueError):
        return False


def _validated_dependencies(value: object) -> tuple[object, ...]:
    if type(value) is not EditorApplicationCoordinatorV1:
        raise_configuration_error()
    try:
        dependencies = tuple(
            object.__getattribute__(value, name)
            for name in (
                "_preparation",
                "_artifacts",
                "_execution_request_authority",
                "_operational_execution",
                "_serializer",
                "_exporter",
            )
        )
        identity = object.__getattribute__(value, "_identity")
    except Exception:  # noqa: BLE001 - copied-invalid retained state
        raise_configuration_error()
    if not _valid_dependencies(dependencies) or identity != tuple(
        id(item) for item in dependencies
    ):
        raise_configuration_error()
    return dependencies


class _EditorPreparationAdapterV1:
    __slots__ = ("_coordinator",)

    def __init__(self, coordinator: EditorOperationalCoordinatorV1) -> None:
        self._coordinator = coordinator

    def prepare(
        self,
        *,
        scout_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
    ) -> EditorOperationalPreparationResultV1:
        return self._coordinator.prepare(
            scout_input, selection_profile, episode_context
        )


class _EditorOperationalExecutionAdapterV1:
    __slots__ = ("_coordinator",)

    def __init__(self, coordinator: EditorOperationalExecutionCoordinatorV1) -> None:
        self._coordinator = coordinator

    def execute(
        self, *, request: EditorGenerationExecutionRequestV1
    ) -> EditorOperationalResultV1:
        return self._coordinator.execute(request)


class _EditorArtifactPreparerV1:
    __slots__ = ("_commentary", "_editorial", "_flow", "_voice")

    def __init__(self) -> None:
        self._flow, self._editorial, self._commentary, self._voice = (
            EpisodeFlowOptimizer(),
            EditorialBlueprintBuilder(),
            CommentaryBlueprintBuilder(),
            VoiceModelBuilder(),
        )

    def build(self, *, plan: EditorGenerationPlanV1) -> _EditorDeterministicArtifactsV1:
        selection = EditorialSelectionResult(
            plan.selection_output, plan.selection_trace
        )
        flow = self._flow.optimize(
            plan.source_input, plan.selection_profile, plan.episode_context, selection
        )
        editorial = self._editorial.build(
            plan.source_input, plan.selection_profile, plan.episode_context, flow
        ).blueprint
        commentary = self._commentary.build(
            plan.source_input,
            plan.selection_profile,
            plan.episode_context,
            flow,
            editorial,
        ).blueprint
        voice = self._voice.build(
            plan.source_input,
            plan.selection_profile,
            plan.episode_context,
            flow,
            editorial,
            commentary,
        ).plan
        return _EditorDeterministicArtifactsV1(flow, editorial, commentary, voice)


def _compose_editor_application_coordinator_v1(
    *,
    preparation_coordinator: EditorOperationalCoordinatorV1,
    operational_execution_coordinator: EditorOperationalExecutionCoordinatorV1,
) -> EditorApplicationCoordinatorV1:
    return EditorApplicationCoordinatorV1(
        preparation=_EditorPreparationAdapterV1(preparation_coordinator),
        artifacts=_EditorArtifactPreparerV1(),
        execution_request_authority=EditorGenerationExecutionRequestAuthorityV1(),
        operational_execution=_EditorOperationalExecutionAdapterV1(
            operational_execution_coordinator
        ),
        serializer=EditorOperationalResultSerializerV1(),
        exporter=EditorAtomicExporterV1(),
    )


def _raise_coordinator_error() -> NoReturn:
    error = EditorApplicationCoordinatorError()
    try:
        raise error from None
    except EditorApplicationCoordinatorError as published:
        Exception.__setattr__(published, "__context__", None)
        raise


__all__ = ("EditorApplicationCoordinatorV1",)

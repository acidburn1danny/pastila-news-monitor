"""Stateless public authority for aggregate Editor execution requests."""

from __future__ import annotations

import copy
import hmac
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NoReturn, Self

from pydantic import BaseModel

from pastila_scout.contracts.editor_output import (
    EditorAgentOutputV1,
    validate_editor_output_against_input,
)
from pastila_scout.editor.blueprint_models import EditorialBlueprint
from pastila_scout.editor.commentary_models import EpisodeCommentaryBlueprint
from pastila_scout.editor.flow_models import FlowDecisionTrace, FlowOptimizationResult
from pastila_scout.editor.generation.models import LanguageGenerationConfig
from pastila_scout.editor.voice_models import EpisodeVoicePlan
from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_generation_execution_v1 import (
    EditorGenerationExecutionRequestV1,
)
from pastila_scout.editor_operational_v1 import (
    EditorGenerationPlanV1,
    EditorOperationalPreparationResultV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .canonical import request_fingerprint, request_projection
from .errors import EditorGenerationExecutionRequestAuthorityError

_FIELD_NAMES = (
    "preparation",
    "plan",
    "flow_result",
    "editorial_blueprint",
    "commentary_blueprint",
    "voice_plan",
    "generation_configuration",
    "runtime_options",
    "provider",
    "requested_at",
    "request_reference",
    "cancellation",
)
_FIELD_TYPES = (
    EditorOperationalPreparationResultV1,
    EditorGenerationPlanV1,
    FlowOptimizationResult,
    EditorialBlueprint,
    EpisodeCommentaryBlueprint,
    EpisodeVoicePlan,
    LanguageGenerationConfig,
    EditorGenerationRuntimeOptionsV1,
    ProviderChoiceV1,
    datetime,
    str,
    CancellationTokenV2,
)


class _Status(Enum):
    INVALID_EXACT_INPUT_TYPE = "invalid_exact_input_type"
    INVALID_REQUEST_STATE = "invalid_request_state"
    INVALID_PREPARATION = "invalid_preparation"
    INVALID_GENERATION_PLAN = "invalid_generation_plan"
    INVALID_FLOW_RESULT = "invalid_flow_result"
    INVALID_EDITORIAL_BLUEPRINT = "invalid_editorial_blueprint"
    INVALID_COMMENTARY_BLUEPRINT = "invalid_commentary_blueprint"
    INVALID_VOICE_PLAN = "invalid_voice_plan"
    INVALID_GENERATION_CONFIGURATION = "invalid_generation_configuration"
    INVALID_RUNTIME_OPTIONS = "invalid_runtime_options"
    INVALID_PROVIDER = "invalid_provider"
    INVALID_REQUESTED_TIMESTAMP = "invalid_requested_timestamp"
    INVALID_REQUEST_REFERENCE = "invalid_request_reference"
    INVALID_CANCELLATION = "invalid_cancellation"
    INVALID_CONFIGURATION_PARITY = "invalid_configuration_parity"
    INVALID_LINEAGE = "invalid_lineage"
    CANONICALIZATION_FAILED = "canonicalization_failed"
    FROZEN_CONSTRUCTION_FAILED = "frozen_construction_failed"
    FROZEN_RECONSTRUCTION_FAILED = "frozen_reconstruction_failed"
    FINGERPRINT_MISMATCH = "fingerprint_mismatch"
    SEMANTIC_PARITY_FAILED = "semantic_parity_failed"
    INTERNAL_AUTHORITY_FAILURE = "internal_authority_failure"


def _raise_public() -> NoReturn:
    error = EditorGenerationExecutionRequestAuthorityError(
        "Editor generation execution request authority is invalid."
    )
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


def _pydantic(value: object, expected: type[BaseModel]):
    if type(value) is not expected:
        return None
    try:
        return expected.model_validate(
            value.model_dump(mode="python", warnings=False), strict=True
        )
    except Exception:  # noqa: BLE001 - reduced at this single boundary
        return None


def _copied(value: object, expected: type):
    if type(value) is not expected:
        return None
    try:
        rebuilt = copy.copy(value)
    except Exception:  # noqa: BLE001 - reduced at this single boundary
        return None
    return rebuilt if type(rebuilt) is expected else None


def _flow(value: object):
    if type(value) is not FlowOptimizationResult:
        return None
    try:
        if type(value.output) is not EditorAgentOutputV1:
            return None
        output = EditorAgentOutputV1.model_validate(
            value.output.model_dump(mode="python", warnings=False), strict=True
        )
        trace = _pydantic(value.trace, FlowDecisionTrace)
        if trace is None:
            return None
        return FlowOptimizationResult(output, trace)
    except Exception:  # noqa: BLE001 - reduced at this single boundary
        return None


def _options(value: object):
    return _copied(value, EditorGenerationRuntimeOptionsV1)


def _timestamp(value: object):
    try:
        return (
            value
            if type(value) is datetime
            and value.tzinfo is not None
            and value.utcoffset() is not None
            else None
        )
    except Exception:  # noqa: BLE001 - reduced at this single boundary
        return None


def _reference(value: object):
    return (
        value
        if type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= 120
        else None
    )


def _reconstruct_values(values):
    rebuilders = (
        (_copied, EditorOperationalPreparationResultV1),
        (_copied, EditorGenerationPlanV1),
        (_flow, None),
        (_pydantic, EditorialBlueprint),
        (_pydantic, EpisodeCommentaryBlueprint),
        (_pydantic, EpisodeVoicePlan),
        (_pydantic, LanguageGenerationConfig),
        (_options, None),
        (lambda value: value if type(value) is ProviderChoiceV1 else None, None),
        (_timestamp, None),
        (_reference, None),
        (_pydantic, CancellationTokenV2),
    )
    statuses = tuple(_Status)[2:14]
    rebuilt = []
    for value, (operation, expected), status in zip(
        values, rebuilders, statuses, strict=True
    ):
        candidate = (
            operation(value, expected) if expected is not None else operation(value)
        )
        if candidate is None:
            return status, None
        rebuilt.append(candidate)
    return None, tuple(rebuilt)


def _configuration_is_valid(configuration, options, provider) -> bool:
    try:
        return (
            configuration.provider == provider.value
            and provider is options.provider
            and configuration.model_identifier == options.model_identifier
            and configuration.model_revision == options.model_revision
            and type(configuration.temperature) is type(options.temperature)
            and configuration.temperature == options.temperature
            and type(configuration.top_p) is type(options.top_p)
            and configuration.top_p == options.top_p
            and configuration.max_output_tokens == options.max_output_tokens
            and configuration.seed is options.seed
            and configuration.structured_output_mode is options.structured_output_mode
            and type(configuration.timeout_seconds)
            is type(options.timeout_policy.timeout_seconds)
            and configuration.timeout_seconds == options.timeout_policy.timeout_seconds
            and options.stop_sequences == ()
        )
    except Exception:  # noqa: BLE001 - reduced at this single boundary
        return False


def _lineage_is_valid(plan, flow, editorial, commentary, voice) -> bool:
    try:
        validate_editor_output_against_input(
            flow.output,
            plan.source_input,
            selection_profile=plan.selection_profile,
            episode_context=plan.episode_context,
        )
        if flow.output.episode_proposal is None:
            return False
        order = tuple(
            item.event_id for item in flow.output.episode_proposal.episode_flow
        )
        source_ids = {item.event_id for item in plan.source_input.ranked_events}
        return (
            editorial.source_report_id == plan.source_report_id
            and commentary.source_report_id == plan.source_report_id
            and voice.source_report_id == plan.source_report_id
            and editorial.flow_order == order
            and commentary.flow_order == order
            and voice.flow_order == order
            and set(order).issubset(source_ids)
        )
    except Exception:  # noqa: BLE001 - reduced at this single boundary
        return False


def _canonical(values):
    try:
        projection = request_projection(values)
        fingerprint = request_fingerprint(projection)
        return None, fingerprint
    except Exception:  # noqa: BLE001 - canonicalization boundary only
        return _Status.CANONICALIZATION_FAILED, None


def _frozen_construct(values, fingerprint):
    return EditorGenerationExecutionRequestV1(*values, fingerprint)


def _semantic_match(request, values, fingerprint) -> bool:
    try:
        return (
            type(request) is EditorGenerationExecutionRequestV1
            and all(
                object.__getattribute__(request, name) == expected
                for name, expected in zip(_FIELD_NAMES, values, strict=True)
            )
            and object.__getattribute__(request, "request_fingerprint") == fingerprint
        )
    except Exception:  # noqa: BLE001 - parity boundary only
        return False


def _construct(values):
    if (
        type(values) is not tuple
        or len(values) != len(_FIELD_TYPES)
        or any(
            type(value) is not expected
            for value, expected in zip(values, _FIELD_TYPES, strict=True)
        )
    ):
        return _Status.INVALID_EXACT_INPUT_TYPE, None
    status, rebuilt = _reconstruct_values(values)
    if status is not None:
        return status, None
    if not _configuration_is_valid(rebuilt[6], rebuilt[7], rebuilt[8]):
        return _Status.INVALID_CONFIGURATION_PARITY, None
    if rebuilt[0].plan != rebuilt[1] or not _lineage_is_valid(*rebuilt[1:6]):
        return _Status.INVALID_LINEAGE, None
    status, fingerprint = _canonical(rebuilt)
    if status is not None:
        return status, None
    try:
        completed = _frozen_construct(rebuilt, fingerprint)
    except Exception:  # noqa: BLE001 - frozen construction boundary only
        return _Status.FROZEN_CONSTRUCTION_FAILED, None
    try:
        reconstructed = copy.copy(completed)
    except Exception:  # noqa: BLE001 - frozen reconstruction boundary only
        return _Status.FROZEN_RECONSTRUCTION_FAILED, None
    if object.__getattribute__(reconstructed, "request_fingerprint") != fingerprint:
        return _Status.FINGERPRINT_MISMATCH, None
    if not _semantic_match(reconstructed, rebuilt, fingerprint):
        return _Status.SEMANTIC_PARITY_FAILED, None
    return None, reconstructed


def _extract(request):
    try:
        values = tuple(object.__getattribute__(request, name) for name in _FIELD_NAMES)
        fingerprint = object.__getattribute__(request, "request_fingerprint")
        return None, values, fingerprint
    except Exception:  # noqa: BLE001 - public field extraction boundary only
        return _Status.INVALID_REQUEST_STATE, None, None


def _reconstruct(request):
    status, values, stored = _extract(request)
    if status is not None:
        return status, None
    status, rebuilt = _reconstruct_values(values)
    if status is not None:
        return status, None
    if not _configuration_is_valid(rebuilt[6], rebuilt[7], rebuilt[8]):
        return _Status.INVALID_CONFIGURATION_PARITY, None
    if rebuilt[0].plan != rebuilt[1] or not _lineage_is_valid(*rebuilt[1:6]):
        return _Status.INVALID_LINEAGE, None
    status, fingerprint = _canonical(rebuilt)
    if status is not None:
        return status, None
    if type(stored) is not str or not hmac.compare_digest(stored, fingerprint):
        return _Status.FINGERPRINT_MISMATCH, None
    try:
        reconstructed = copy.copy(request)
    except Exception:  # noqa: BLE001 - frozen reconstruction boundary only
        return _Status.FROZEN_RECONSTRUCTION_FAILED, None
    if not _semantic_match(reconstructed, rebuilt, fingerprint):
        return _Status.SEMANTIC_PARITY_FAILED, None
    return None, reconstructed


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorGenerationExecutionRequestAuthorityV1:
    """Own aggregate fingerprint creation without retaining caller state."""

    def __init__(self) -> None:
        if type(self) is not EditorGenerationExecutionRequestAuthorityV1:
            del self
            _raise_public()

    def construct(
        self,
        *,
        preparation: EditorOperationalPreparationResultV1,
        plan: EditorGenerationPlanV1,
        flow_result: FlowOptimizationResult,
        editorial_blueprint: EditorialBlueprint,
        commentary_blueprint: EpisodeCommentaryBlueprint,
        voice_plan: EpisodeVoicePlan,
        generation_configuration: LanguageGenerationConfig,
        runtime_options: EditorGenerationRuntimeOptionsV1,
        provider: ProviderChoiceV1,
        requested_at: datetime,
        request_reference: str,
        cancellation: CancellationTokenV2,
    ) -> EditorGenerationExecutionRequestV1:
        if type(self) is not EditorGenerationExecutionRequestAuthorityV1:
            del self, preparation, plan, flow_result, editorial_blueprint
            del commentary_blueprint, voice_plan, generation_configuration
            del runtime_options, provider, requested_at, request_reference
            del cancellation
            _raise_public()
        values = (
            preparation,
            plan,
            flow_result,
            editorial_blueprint,
            commentary_blueprint,
            voice_plan,
            generation_configuration,
            runtime_options,
            provider,
            requested_at,
            request_reference,
            cancellation,
        )
        del self, preparation, plan, flow_result, editorial_blueprint
        del commentary_blueprint, voice_plan, generation_configuration
        del runtime_options, provider, requested_at, request_reference, cancellation
        status, result = _construct(values)
        del values
        if status is None and type(result) is not EditorGenerationExecutionRequestV1:
            status = _Status.INTERNAL_AUTHORITY_FAILURE
        if status is not None:
            del status, result
            _raise_public()
        del status
        return result

    def reconstruct(
        self,
        *,
        request: EditorGenerationExecutionRequestV1,
    ) -> EditorGenerationExecutionRequestV1:
        if (
            type(self) is not EditorGenerationExecutionRequestAuthorityV1
            or type(request) is not EditorGenerationExecutionRequestV1
        ):
            del self, request
            _raise_public()
        del self
        status, result = _reconstruct(request)
        del request
        if status is None and type(result) is not EditorGenerationExecutionRequestV1:
            status = _Status.INTERNAL_AUTHORITY_FAILURE
        if status is not None:
            del status, result
            _raise_public()
        del status
        return result

    def __repr__(self) -> str:
        if type(self) is not EditorGenerationExecutionRequestAuthorityV1:
            del self
            _raise_public()
        return "EditorGenerationExecutionRequestAuthorityV1()"

    def __eq__(self, other: object) -> bool:
        return (
            type(self) is EditorGenerationExecutionRequestAuthorityV1
            and type(other) is EditorGenerationExecutionRequestAuthorityV1
        )

    def __copy__(self) -> Self:
        if type(self) is not EditorGenerationExecutionRequestAuthorityV1:
            del self
            _raise_public()
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        if type(self) is not EditorGenerationExecutionRequestAuthorityV1:
            del self, memo
            _raise_public()
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError(
            "EditorGenerationExecutionRequestAuthorityV1 does not support pickle"
        )


__all__ = ("EditorGenerationExecutionRequestAuthorityV1",)

"""Immutable aggregate carrying deterministic Editor generation authority."""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from datetime import datetime
from typing import NoReturn

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
from pastila_scout.editor_generation_authority_v1.canonical import (
    canonical_value,
    semantic_fingerprint,
    tagged_number,
)
from pastila_scout.editor_generation_authority_v1.models import (
    reconstruct_runtime_options,
)
from pastila_scout.editor_operational_v1 import (
    EditorGenerationPlanV1,
    EditorOperationalPreparationResultV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .errors import EditorGenerationExecutionRequestError


def _raise_invalid() -> NoReturn:
    error = EditorGenerationExecutionRequestError(
        "Editor generation execution request is invalid."
    )
    error.__suppress_context__ = True
    raise error from None


def _pydantic(value: object, expected: type[BaseModel]):
    if type(value) is not expected:
        _raise_invalid()
    try:
        return expected.model_validate(
            value.model_dump(mode="python", warnings=False), strict=True
        )
    except Exception:  # noqa: BLE001 - nested validation details remain private
        _raise_invalid()


def _reconstruct_flow(value: object) -> FlowOptimizationResult:
    if type(value) is not FlowOptimizationResult:
        _raise_invalid()
    try:
        if type(value.output) is not EditorAgentOutputV1:
            _raise_invalid()
        output = EditorAgentOutputV1.model_validate(
            value.output.model_dump(mode="python", warnings=False), strict=True
        )
        trace = _pydantic(value.trace, FlowDecisionTrace)
        return FlowOptimizationResult(output, trace)
    except EditorGenerationExecutionRequestError:
        raise
    except Exception:  # noqa: BLE001 - nested validation details remain private
        _raise_invalid()


def _copy_exact(value: object, expected: type):
    if type(value) is not expected:
        _raise_invalid()
    try:
        rebuilt = copy(value)
    except Exception:  # noqa: BLE001 - copied-invalid state remains private
        _raise_invalid()
    if type(rebuilt) is not expected:
        _raise_invalid()
    return rebuilt


def _configuration(value: object) -> LanguageGenerationConfig:
    return _pydantic(value, LanguageGenerationConfig)


def _cancellation(value: object) -> CancellationTokenV2:
    return _pydantic(value, CancellationTokenV2)


_FIELDS = (
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
    "request_fingerprint",
)


@dataclass(frozen=True, slots=True, init=False, repr=False)
class EditorGenerationExecutionRequestV1:
    preparation: EditorOperationalPreparationResultV1
    plan: EditorGenerationPlanV1
    flow_result: FlowOptimizationResult
    editorial_blueprint: EditorialBlueprint
    commentary_blueprint: EpisodeCommentaryBlueprint
    voice_plan: EpisodeVoicePlan
    generation_configuration: LanguageGenerationConfig
    runtime_options: EditorGenerationRuntimeOptionsV1
    provider: ProviderChoiceV1
    requested_at: datetime
    request_reference: str
    cancellation: CancellationTokenV2
    request_fingerprint: str
    _seal: str

    def __init__(
        self,
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
        request_fingerprint,
    ) -> None:
        valid = True
        try:
            self._initialize(
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
                request_fingerprint,
            )
        except Exception:  # noqa: BLE001 - aggregate validation is discarded
            valid = False
        if not valid:
            del self, preparation, plan, flow_result, editorial_blueprint
            del commentary_blueprint, voice_plan, generation_configuration
            del runtime_options, provider, requested_at, request_reference
            del cancellation, request_fingerprint
            _raise_invalid()

    def _initialize(
        self,
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
        request_fingerprint,
    ) -> None:
        try:
            valid_preparation = _copy_exact(
                preparation, EditorOperationalPreparationResultV1
            )
            valid_plan = _copy_exact(plan, EditorGenerationPlanV1)
            valid_flow = _reconstruct_flow(flow_result)
            valid_editorial = _pydantic(editorial_blueprint, EditorialBlueprint)
            valid_commentary = _pydantic(
                commentary_blueprint, EpisodeCommentaryBlueprint
            )
            valid_voice = _pydantic(voice_plan, EpisodeVoicePlan)
            valid_config = _configuration(generation_configuration)
            valid_options = reconstruct_runtime_options(runtime_options)
            valid_cancellation = _cancellation(cancellation)
            if valid_preparation.plan != valid_plan:
                _raise_invalid()
            if (
                type(provider) is not ProviderChoiceV1
                or provider is not valid_options.provider
            ):
                _raise_invalid()
            if (
                type(requested_at) is not datetime
                or requested_at.tzinfo is None
                or requested_at.utcoffset() is None
            ):
                _raise_invalid()
            if (
                type(request_reference) is not str
                or not request_reference
                or request_reference != request_reference.strip()
                or len(request_reference) > 120
            ):
                _raise_invalid()
            _validate_configuration(valid_config, valid_options, provider)
            _validate_lineage(
                valid_plan, valid_flow, valid_editorial, valid_commentary, valid_voice
            )
            values = (
                valid_preparation,
                valid_plan,
                valid_flow,
                valid_editorial,
                valid_commentary,
                valid_voice,
                valid_config,
                valid_options,
                provider,
                requested_at,
                request_reference,
                valid_cancellation,
            )
            expected = semantic_fingerprint(_semantics(values))
            if request_fingerprint != expected:
                _raise_invalid()
        except EditorGenerationExecutionRequestError:
            raise
        except Exception:  # noqa: BLE001 - aggregate details remain private
            _raise_invalid()
        for name, value in zip(_FIELDS[:-1], values, strict=True):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "request_fingerprint", expected)
        object.__setattr__(self, "_seal", expected)

    def __repr__(self) -> str:
        valid = reconstruct_execution_request(self)
        return (
            "EditorGenerationExecutionRequestV1("
            f"provider={valid.provider.value!r}, source_report_id=<redacted>)"
        )

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _values(
            reconstruct_execution_request(self)
        ) == _values(reconstruct_execution_request(other))

    def __copy__(self):
        return reconstruct_execution_request(self)

    def __deepcopy__(self, memo):
        del memo
        return reconstruct_execution_request(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorGenerationExecutionRequestV1 does not support pickle")


def _validate_configuration(config, options, provider) -> None:
    if (
        config.provider != provider.value
        or config.model_identifier != options.model_identifier
        or config.model_revision != options.model_revision
        or type(config.temperature) is not type(options.temperature)
        or config.temperature != options.temperature
        or type(config.top_p) is not type(options.top_p)
        or config.top_p != options.top_p
        or config.max_output_tokens != options.max_output_tokens
        or config.seed is not options.seed
        or config.structured_output_mode is not options.structured_output_mode
        or type(config.timeout_seconds)
        is not type(options.timeout_policy.timeout_seconds)
        or config.timeout_seconds != options.timeout_policy.timeout_seconds
        or options.stop_sequences != ()
    ):
        _raise_invalid()


def _validate_lineage(plan, flow, editorial, commentary, voice) -> None:
    try:
        validate_editor_output_against_input(
            flow.output,
            plan.source_input,
            selection_profile=plan.selection_profile,
            episode_context=plan.episode_context,
        )
    except Exception:  # noqa: BLE001 - cross-validation details remain private
        _raise_invalid()
    if flow.output.episode_proposal is None:
        _raise_invalid()
    order = tuple(item.event_id for item in flow.output.episode_proposal.episode_flow)
    source_ids = {item.event_id for item in plan.source_input.ranked_events}
    if (
        editorial.source_report_id != plan.source_report_id
        or commentary.source_report_id != plan.source_report_id
        or voice.source_report_id != plan.source_report_id
        or editorial.flow_order != order
        or commentary.flow_order != order
        or voice.flow_order != order
        or not set(order).issubset(source_ids)
    ):
        _raise_invalid()


def _semantics(values):
    (
        preparation,
        plan,
        flow,
        editorial,
        commentary,
        voice,
        config,
        options,
        provider,
        requested_at,
        reference,
        cancellation,
    ) = values
    return {
        "preparation": canonical_value(preparation),
        "plan": canonical_value(plan),
        "flow_result": canonical_value(flow),
        "editorial_blueprint": canonical_value(editorial),
        "commentary_blueprint": canonical_value(commentary),
        "voice_plan": canonical_value(voice),
        "generation_configuration": canonical_value(config),
        "runtime_options": {
            "provider": options.provider.value,
            "model_identifier": options.model_identifier,
            "model_revision": options.model_revision,
            "temperature": tagged_number(options.temperature),
            "top_p": tagged_number(options.top_p),
            "max_output_tokens": options.max_output_tokens,
            "seed": options.seed,
            "stop_sequences": options.stop_sequences,
            "structured_output_mode": options.structured_output_mode,
            "timeout_seconds": tagged_number(options.timeout_policy.timeout_seconds),
        },
        "provider": provider.value,
        "requested_at": requested_at,
        "request_reference": reference,
        "cancellation_requested": cancellation.cancellation_requested,
    }


def _values(value):
    return tuple(object.__getattribute__(value, name) for name in _FIELDS)


def reconstruct_execution_request(value: object) -> EditorGenerationExecutionRequestV1:
    if type(value) is not EditorGenerationExecutionRequestV1:
        _raise_invalid()
    try:
        fields = _values(value)
        retained = object.__getattribute__(value, "_seal")
        rebuilt = EditorGenerationExecutionRequestV1(*fields)
        if retained != object.__getattribute__(rebuilt, "_seal"):
            _raise_invalid()
        return rebuilt
    except EditorGenerationExecutionRequestError:
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state remains private
        _raise_invalid()


__all__ = ("EditorGenerationExecutionRequestV1",)

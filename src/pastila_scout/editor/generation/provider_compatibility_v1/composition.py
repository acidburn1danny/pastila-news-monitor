"""Inert application-owned composition seam for future Producer migration."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from functools import cached_property, partial

from pastila_scout.provider_execution_v2 import (
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
    ProviderExecutorV2,
)

from .errors import ProducerCompatibilityConfigurationError
from .models import (
    AIRetryPolicy,
    ProducerCompatibilityEventV1,
    ProducerExecutionFailureV1,
    ProducerExecutionRequestV1,
)
from .projection import ProducerResultProjectorV1
from .protocols import (
    ProducerCompatibilityClockV1,
    ProducerCompatibilityObserverV1,
    ProducerDiagnosticsAuthorityV1,
)


@dataclass(frozen=True, slots=True)
class ProducerCompatibilityCompositionV1:
    """Immutable bindings only; deliberately exposes no execution method."""

    request: ProducerExecutionRequestV1
    executor: ProviderExecutorV2
    diagnostics_authority: ProducerDiagnosticsAuthorityV1 | None
    clock: ProducerCompatibilityClockV1 | None
    observer: ProducerCompatibilityObserverV1 | None
    cancellation_token: object
    retry_decider: object
    sleeper: object
    projector: ProducerResultProjectorV1


def compose_producer_compatibility_v1(
    *,
    request: ProducerExecutionRequestV1,
    executor: ProviderExecutorV2,
    diagnostics_authority: ProducerDiagnosticsAuthorityV1 | None = None,
    clock: ProducerCompatibilityClockV1 | None = None,
    observer: ProducerCompatibilityObserverV1 | None = None,
    cancellation_token: object,
    retry_decider: object,
    sleeper: object,
    projector: ProducerResultProjectorV1,
) -> ProducerCompatibilityCompositionV1:
    """Validate and retain Phase A authorities without calling any of them."""
    composition = _validated_composition(
        request=request,
        executor=executor,
        diagnostics_authority=diagnostics_authority,
        clock=clock,
        observer=observer,
        cancellation_token=cancellation_token,
        retry_decider=retry_decider,
        sleeper=sleeper,
        projector=projector,
    )
    if composition is not None:
        return composition
    del (
        request,
        executor,
        diagnostics_authority,
        clock,
        observer,
        cancellation_token,
        retry_decider,
        sleeper,
        projector,
    )
    _raise_configuration_error()


def _validated_composition(**bindings) -> ProducerCompatibilityCompositionV1 | None:
    try:
        request = ProducerExecutionRequestV1.reconstruct(bindings["request"])
        if not _method_matches(
            bindings["executor"],
            "execute",
            (
                ("self", inspect.Parameter.POSITIONAL_OR_KEYWORD, None),
                (
                    "request",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    ProviderExecutionRequestV2,
                ),
            ),
            ProviderExecutionResultV2,
        ):
            return None
        diagnostics = bindings["diagnostics_authority"]
        if diagnostics is not None and not _method_matches(
            diagnostics,
            "observe",
            (
                ("self", inspect.Parameter.POSITIONAL_OR_KEYWORD, None),
                ("correlation_id", inspect.Parameter.KEYWORD_ONLY, str),
                ("attempt_number", inspect.Parameter.KEYWORD_ONLY, int),
                ("execution_request_id", inspect.Parameter.KEYWORD_ONLY, str),
                ("request_envelope_identity", inspect.Parameter.KEYWORD_ONLY, str),
                ("result", inspect.Parameter.KEYWORD_ONLY, ProviderExecutionResultV2),
            ),
            "ProducerDiagnosticsObservationV1 | None",
        ):
            return None
        clock = bindings["clock"]
        if clock is not None and not _method_matches(
            clock,
            "read_monotonic_ns",
            (("self", inspect.Parameter.POSITIONAL_OR_KEYWORD, None),),
            int,
        ):
            return None
        observer = bindings["observer"]
        if observer is not None and not _method_matches(
            observer,
            "emit",
            (
                ("self", inspect.Parameter.POSITIONAL_OR_KEYWORD, None),
                (
                    "event",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    ProducerCompatibilityEventV1,
                ),
            ),
            None,
        ):
            return None
        if not _method_matches(
            bindings["cancellation_token"],
            "is_cancelled",
            (("self", inspect.Parameter.POSITIONAL_OR_KEYWORD, None),),
            bool,
        ):
            return None
        if not _method_matches(
            bindings["retry_decider"],
            "should_retry",
            (
                ("self", inspect.Parameter.POSITIONAL_OR_KEYWORD, None),
                ("failure", inspect.Parameter.KEYWORD_ONLY, ProducerExecutionFailureV1),
                ("attempt_number", inspect.Parameter.KEYWORD_ONLY, int),
                ("policy", inspect.Parameter.KEYWORD_ONLY, AIRetryPolicy),
            ),
            bool,
        ):
            return None
        if not _method_matches(
            bindings["sleeper"],
            "sleep",
            (
                ("self", inspect.Parameter.POSITIONAL_OR_KEYWORD, None),
                ("delay_seconds", inspect.Parameter.POSITIONAL_OR_KEYWORD, float),
            ),
            None,
        ):
            return None
        projector = bindings["projector"]
        if type(projector) is not ProducerResultProjectorV1:
            return None
        return ProducerCompatibilityCompositionV1(
            request=request,
            executor=bindings["executor"],
            diagnostics_authority=diagnostics,
            clock=clock,
            observer=observer,
            cancellation_token=bindings["cancellation_token"],
            retry_decider=bindings["retry_decider"],
            sleeper=bindings["sleeper"],
            projector=projector,
        )
    except (AttributeError, TypeError, ValueError):
        return None
    finally:
        bindings.clear()


def _method_matches(value, name: str, expected_parameters, expected_return) -> bool:
    if isinstance(value, partial):
        return False
    descriptor = _static_descriptor(type(value), name)
    if (
        descriptor is None
        or isinstance(
            descriptor, (staticmethod, classmethod, property, cached_property)
        )
        or not inspect.isfunction(descriptor)
    ):
        return False
    if "__wrapped__" in descriptor.__dict__ or "__signature__" in descriptor.__dict__:
        return False
    try:
        signature = inspect.signature(descriptor, follow_wrapped=False)
    except (TypeError, ValueError):
        return False
    parameters = tuple(signature.parameters.values())
    if len(parameters) != len(expected_parameters):
        return False
    for parameter, (expected_name, expected_kind, annotation) in zip(
        parameters, expected_parameters, strict=True
    ):
        if (
            parameter.name != expected_name
            or parameter.kind is not expected_kind
            or parameter.default is not inspect.Parameter.empty
        ):
            return False
        if annotation is not None and not _annotation_matches(
            parameter.annotation, annotation
        ):
            return False
    return _annotation_matches(signature.return_annotation, expected_return)


def _static_descriptor(owner: type, name: str):
    for candidate in owner.__mro__:
        if name in vars(candidate):
            return vars(candidate)[name]
    return None


def _annotation_matches(actual, expected) -> bool:
    if actual is expected:
        return True
    if expected is None:
        return actual in {None, "None"}
    expected_name = expected if type(expected) is str else expected.__name__
    return actual in {expected_name, getattr(expected, "__qualname__", expected_name)}


def _raise_configuration_error() -> None:
    raise ProducerCompatibilityConfigurationError from None


__all__ = ()

"""Minimal deterministic mappings for Scout provider-neutral execution."""

from pastila_scout.provider_execution_v2 import (
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)

from .errors import ScoutRuntimeExecutionError
from .models import ScoutRuntimeRequestV1, ScoutRuntimeResultV1


def map_scout_runtime_request(
    request: ScoutRuntimeRequestV1,
) -> ProviderExecutionRequestV2:
    """Revalidate and expose one explicitly opted-in neutral request."""
    if type(request) is not ScoutRuntimeRequestV1:
        raise _error("invalid Scout runtime request")
    return ScoutRuntimeRequestV1(
        provider_execution_opt_in=object.__getattribute__(
            request, "provider_execution_opt_in"
        ),
        provider_request=object.__getattribute__(request, "provider_request"),
    ).provider_request


def map_provider_execution_result(
    result: ProviderExecutionResultV2,
    request: ProviderExecutionRequestV2,
) -> ScoutRuntimeResultV1:
    """Project one neutral result after exact request-lineage validation."""
    projection = ScoutRuntimeResultV1(result)
    output = projection.provider_result
    if (
        output.request_id != request.context.request_id
        or output.provider_id != request.provider.provider_id
        or output.request_envelope_identity != request.request_envelope.identity
    ):
        raise _error("Scout provider execution result lineage mismatch")
    provider_result = output.provider_result
    if provider_result is not None:
        request_units = request.request_envelope.request_units
        outputs = provider_result.outputs
        if len(outputs) > len(request_units) or (
            provider_result.status.value == "success"
            and len(outputs) != len(request_units)
        ):
            raise _error("Scout provider execution output lineage mismatch")
        if any(
            item.ordinal >= len(request_units)
            or item.source_request_reference
            != request_units[item.ordinal].source_request_reference
            for item in outputs
        ):
            raise _error("Scout provider execution output lineage mismatch")
    return projection


def _error(message: str) -> ScoutRuntimeExecutionError:
    error = ScoutRuntimeExecutionError(message)
    error.__suppress_context__ = True
    return error


__all__ = ("map_provider_execution_result", "map_scout_runtime_request")

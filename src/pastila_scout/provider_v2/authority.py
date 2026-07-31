"""Authoritative V2 builders, reconstruction, and exact validation."""

from pydantic import ValidationError

from .canonical import semantic_sha256
from .errors import ProviderV2ValidationError
from .identity import (
    descriptor_fingerprint,
    descriptor_identity,
    request_envelope_fingerprint,
    request_envelope_identity,
    request_message_fingerprint,
    request_message_identity,
    request_unit_fingerprint,
    request_unit_identity,
    result_envelope_fingerprint,
    result_envelope_identity,
    result_unit_fingerprint,
    result_unit_identity,
)
from .models import (
    ProviderCapabilityV2,
    ProviderDescriptorV2,
    ProviderRequestEnvelopeV2,
    ProviderRequestIntentV2,
    ProviderRequestMessageV2,
    ProviderRequestUnitV2,
    ProviderResultEnvelopeV2,
    ProviderResultProjectionV2,
    ProviderResultStatusV2,
    ProviderResultUnitV2,
    ProviderV2ValidationIssue,
)

_ZERO = "0" * 64
_FALLBACK = "provider-v2-artifact"


def build_provider_descriptor(
    *,
    provider_id: str,
    display_name: str,
    capabilities: tuple[ProviderCapabilityV2, ...],
    descriptor_version: str,
    adapter_identity: str,
) -> ProviderDescriptorV2:
    """Construct one canonical, sealed provider descriptor."""

    try:
        value = ProviderDescriptorV2(
            identity=f"scout:provider-descriptor-v2:{_ZERO}",
            fingerprint=_ZERO,
            provider_id=provider_id,
            display_name=display_name,
            capabilities=tuple(sorted(capabilities, key=str)),
            descriptor_version=descriptor_version,
            adapter_identity=adapter_identity,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise ProviderV2ValidationError("invalid provider descriptor input") from error
    value = value.model_copy(update={"identity": descriptor_identity(value)})
    return value.model_copy(update={"fingerprint": descriptor_fingerprint(value)})


def validate_provider_descriptor(
    descriptor: ProviderDescriptorV2,
) -> tuple[ProviderV2ValidationIssue, ...]:
    """Reconstruct and validate descriptor seals exactly."""

    rebuilt = _reconstruct(ProviderDescriptorV2, descriptor)
    if rebuilt is None:
        return (_issue("provider-v2-invalid-descriptor", _FALLBACK),)
    issues = []
    if rebuilt.identity != descriptor_identity(rebuilt):
        issues.append(
            _issue("provider-v2-invalid-descriptor-identity", rebuilt.provider_id)
        )
    if rebuilt.fingerprint != descriptor_fingerprint(rebuilt):
        issues.append(
            _issue("provider-v2-invalid-descriptor-fingerprint", rebuilt.provider_id)
        )
    return _ordered(issues)


def build_provider_request_envelope(
    intent: ProviderRequestIntentV2,
    descriptor: ProviderDescriptorV2,
) -> ProviderRequestEnvelopeV2:
    """Build an exact neutral request projection from authoritative intent."""

    source = _required_reconstruction(ProviderRequestIntentV2, intent, "request intent")
    owner = _required_descriptor(descriptor)
    units = tuple(_build_request_unit(source, item) for item in source.request_units)
    value = ProviderRequestEnvelopeV2(
        identity=f"scout:provider-request-envelope-v2:{_ZERO}",
        fingerprint=_ZERO,
        request_envelope_reference=(
            "provider-request-envelope-v2:"
            f"{semantic_sha256((owner.identity, source.execution_plan_identity))}"
        ),
        descriptor_identity=owner.identity,
        descriptor_fingerprint=owner.fingerprint,
        adapter_identity=owner.adapter_identity,
        execution_plan_reference=source.execution_plan_reference,
        execution_plan_identity=source.execution_plan_identity,
        execution_plan_fingerprint=source.execution_plan_fingerprint,
        draft_reference=source.draft_reference,
        draft_fingerprint=source.draft_fingerprint,
        request_units=units,
    )
    value = value.model_copy(update={"identity": request_envelope_identity(value)})
    return value.model_copy(update={"fingerprint": request_envelope_fingerprint(value)})


def validate_provider_request_envelope(
    envelope: ProviderRequestEnvelopeV2,
    intent: ProviderRequestIntentV2,
    descriptor: ProviderDescriptorV2,
) -> tuple[ProviderV2ValidationIssue, ...]:
    """Reconstruct expected request authority and compare every field."""

    actual = _reconstruct(ProviderRequestEnvelopeV2, envelope)
    if actual is None:
        return (_issue("provider-v2-invalid-request-envelope", _FALLBACK),)
    try:
        expected = build_provider_request_envelope(intent, descriptor)
    except ProviderV2ValidationError:
        return (_issue("provider-v2-invalid-request-authority", _FALLBACK),)
    return _exact_issues("request", actual, expected)


def build_provider_result_envelope(
    request: ProviderRequestEnvelopeV2,
    intent: ProviderRequestIntentV2,
    descriptor: ProviderDescriptorV2,
    projection: ProviderResultProjectionV2,
) -> ProviderResultEnvelopeV2:
    """Build provider-neutral output sufficient for a future Composer."""

    if request_issues := validate_provider_request_envelope(
        request, intent, descriptor
    ):
        raise ProviderV2ValidationError(request_issues[0].code)
    authority = _required_reconstruction(
        ProviderRequestEnvelopeV2, request, "request envelope"
    )
    output = _required_reconstruction(
        ProviderResultProjectionV2, projection, "result projection"
    )
    if output.status is ProviderResultStatusV2.SUCCESS and len(output.outputs) != len(
        authority.request_units
    ):
        raise ProviderV2ValidationError(
            "successful result must cover every request unit"
        )
    if len(output.outputs) > len(authority.request_units):
        raise ProviderV2ValidationError("result contains extra output units")
    units = tuple(_build_result_unit(authority, item) for item in output.outputs)
    value = ProviderResultEnvelopeV2(
        identity=f"scout:provider-result-envelope-v2:{_ZERO}",
        fingerprint=_ZERO,
        result_envelope_reference=f"provider-result-envelope-v2:{authority.identity}",
        descriptor_identity=authority.descriptor_identity,
        descriptor_fingerprint=authority.descriptor_fingerprint,
        adapter_identity=authority.adapter_identity,
        request_envelope_reference=authority.request_envelope_reference,
        request_envelope_identity=authority.identity,
        request_envelope_fingerprint=authority.fingerprint,
        execution_plan_reference=authority.execution_plan_reference,
        execution_plan_identity=authority.execution_plan_identity,
        execution_plan_fingerprint=authority.execution_plan_fingerprint,
        draft_reference=authority.draft_reference,
        draft_fingerprint=authority.draft_fingerprint,
        status=output.status,
        outputs=units,
        failure_code=output.failure_code,
    )
    value = value.model_copy(update={"identity": result_envelope_identity(value)})
    return value.model_copy(update={"fingerprint": result_envelope_fingerprint(value)})


def validate_provider_result_envelope(
    envelope: ProviderResultEnvelopeV2,
    request: ProviderRequestEnvelopeV2,
    intent: ProviderRequestIntentV2,
    descriptor: ProviderDescriptorV2,
    projection: ProviderResultProjectionV2,
) -> tuple[ProviderV2ValidationIssue, ...]:
    """Reconstruct expected result authority and compare every field."""

    actual = _reconstruct(ProviderResultEnvelopeV2, envelope)
    if actual is None:
        return (_issue("provider-v2-invalid-result-envelope", _FALLBACK),)
    try:
        expected = build_provider_result_envelope(
            request, intent, descriptor, projection
        )
    except ProviderV2ValidationError:
        return (_issue("provider-v2-invalid-result-authority", _FALLBACK),)
    return _exact_issues("result", actual, expected)


def _build_request_unit(intent, item) -> ProviderRequestUnitV2:
    messages = []
    for message in item.messages:
        value = ProviderRequestMessageV2(
            identity=f"scout:provider-request-message-v2:{_ZERO}",
            fingerprint=_ZERO,
            message_reference=(
                f"provider-request-message-v2:{intent.execution_plan_identity}:"
                f"{item.ordinal}:{message.ordinal}"
            ),
            role=message.role,
            content=message.content,
            ordinal=message.ordinal,
        )
        value = value.model_copy(update={"identity": request_message_identity(value)})
        messages.append(
            value.model_copy(update={"fingerprint": request_message_fingerprint(value)})
        )
    value = ProviderRequestUnitV2(
        identity=f"scout:provider-request-unit-v2:{_ZERO}",
        fingerprint=_ZERO,
        request_unit_reference=(
            f"provider-request-unit-v2:{intent.execution_plan_identity}:{item.ordinal}"
        ),
        source_request_reference=item.source_request_reference,
        ordinal=item.ordinal,
        messages=tuple(messages),
    )
    value = value.model_copy(update={"identity": request_unit_identity(value)})
    return value.model_copy(update={"fingerprint": request_unit_fingerprint(value)})


def _build_result_unit(request, item) -> ProviderResultUnitV2:
    source = request.request_units[item.ordinal]
    if source.source_request_reference != item.source_request_reference:
        raise ProviderV2ValidationError(
            "output source request does not match authority"
        )
    value = ProviderResultUnitV2(
        identity=f"scout:provider-result-unit-v2:{_ZERO}",
        fingerprint=_ZERO,
        result_unit_reference=f"provider-result-unit-v2:{request.identity}:{item.ordinal}",
        source_request_reference=item.source_request_reference,
        request_unit_reference=source.request_unit_reference,
        request_unit_identity=source.identity,
        request_unit_fingerprint=source.fingerprint,
        ordinal=item.ordinal,
        generated_text=item.generated_text,
        finish_reason=item.finish_reason,
    )
    value = value.model_copy(update={"identity": result_unit_identity(value)})
    return value.model_copy(update={"fingerprint": result_unit_fingerprint(value)})


def _required_descriptor(value) -> ProviderDescriptorV2:
    rebuilt = _required_reconstruction(ProviderDescriptorV2, value, "descriptor")
    if validate_provider_descriptor(rebuilt):
        raise ProviderV2ValidationError("invalid provider descriptor authority")
    return rebuilt


def _required_reconstruction(model, value, label):
    rebuilt = _reconstruct(model, value)
    if rebuilt is None:
        raise ProviderV2ValidationError(f"invalid {label}")
    return rebuilt


def _reconstruct(model, value):
    try:
        return model.model_validate(value.model_dump(mode="python", warnings=False))
    except (
        AttributeError,
        KeyError,
        LookupError,
        RuntimeError,
        TypeError,
        ValueError,
        ValidationError,
    ):
        return None


def _exact_issues(kind, actual, expected):
    issues = []
    for field in type(actual).model_fields:
        if getattr(actual, field) != getattr(expected, field):
            issues.append(
                _issue(
                    f"provider-v2-{kind}-{field.replace('_', '-')}-mismatch",
                    getattr(actual, f"{kind}_envelope_reference"),
                    field,
                )
            )
    return _ordered(issues)


def _issue(code, reference, field=None):
    safe = (
        reference
        if isinstance(reference, str) and 0 < len(reference) <= 200
        else _FALLBACK
    )
    return ProviderV2ValidationIssue(code=code, artifact_reference=safe, field=field)


def _ordered(issues):
    return tuple(
        sorted(
            issues,
            key=lambda item: (item.code, item.artifact_reference, item.field or ""),
        )
    )


__all__ = (
    "build_provider_descriptor",
    "build_provider_request_envelope",
    "build_provider_result_envelope",
    "validate_provider_descriptor",
    "validate_provider_request_envelope",
    "validate_provider_result_envelope",
)

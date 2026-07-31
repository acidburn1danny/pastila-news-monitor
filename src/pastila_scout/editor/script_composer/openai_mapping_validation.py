"""OpenAI request projection and validation for Phase 6.2."""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from pydantic import ValidationError

from .errors import DomainValidationError, DomainValidationIssue
from .llm_execution_models import DraftLLMExecutionPlan
from .llm_execution_validation import validate_draft_llm_execution_plan
from .openai_mapping_identity import (
    derive_openai_provider_message_fingerprint,
    derive_openai_provider_message_identity,
    derive_openai_provider_request_fingerprint,
    derive_openai_provider_request_identity,
    derive_openai_provider_request_plan_fingerprint,
    derive_openai_provider_request_plan_identity,
)
from .openai_mapping_models import (
    OpenAIProviderMessage,
    OpenAIProviderRequest,
    OpenAIProviderRequestPlan,
)
from .provider_mapping_models import (
    ProviderMappingValidationContext,
    ProviderRequestPlanDescriptor,
)

_ZERO = "0" * 64
_FALLBACK = "provider-mapping-artifact"
_RELATED_FALLBACK = "unsafe-related-reference"
_MAX_REFERENCE_LENGTH = 200


@dataclass(frozen=True, slots=True)
class _Reconstruction:
    plan: OpenAIProviderRequestPlan | None
    context: ProviderMappingValidationContext | None
    issues: tuple[DomainValidationIssue, ...]


def _descriptor_reference(provider: str, version: str) -> str:
    return f"provider-mapping-descriptor:{provider}:{version}"


def _plan_reference(execution_plan) -> str:
    return f"openai-request-plan:{execution_plan.identity}"


def _request_reference(execution_request) -> str:
    return f"openai-request:{execution_request.identity}"


def _message_reference(execution_message) -> str:
    return f"openai-message:{execution_message.identity}"


def _openai_role(execution_role: str) -> str:
    return "developer" if execution_role == "instruction" else "user"


def build_openai_provider_request_plan(
    execution_plan: DraftLLMExecutionPlan,
    provider_descriptor: ProviderRequestPlanDescriptor,
    validation_context: ProviderMappingValidationContext,
) -> OpenAIProviderRequestPlan:
    """Build one exact OpenAI mapping from authoritative Phase 6.1 state."""

    source, descriptor, context, issues = _reconstruct_builder_inputs(
        execution_plan, provider_descriptor, validation_context
    )
    if issues:
        raise DomainValidationError(issues)
    assert source is not None and descriptor is not None and context is not None
    issues = list(_descriptor_issues(descriptor))
    sources = tuple(
        item
        for item in context.execution_plans
        if item.identity == source.identity
        and item.execution_plan_reference == source.execution_plan_reference
    )
    descriptors = tuple(
        item
        for item in context.provider_descriptors
        if item.identity == descriptor.identity
        and item.provider_descriptor_reference
        == descriptor.provider_descriptor_reference
    )
    if len(sources) != 1:
        issues.append(_issue("provider-mapping-unresolved-execution-plan", _FALLBACK))
    if len(descriptors) != 1:
        issues.append(
            _issue("provider-mapping-unresolved-provider-descriptor", _FALLBACK)
        )
    if issues:
        raise DomainValidationError(tuple(_ordered(issues)))
    authoritative_source = sources[0]
    authoritative_descriptor = descriptors[0]
    upstream = validate_draft_llm_execution_plan(
        authoritative_source, context.execution_validation_context
    )
    if upstream:
        raise DomainValidationError(upstream)
    return _project(authoritative_source, authoritative_descriptor)


def _project(source, descriptor):
    requests = tuple(
        _project_request(source, request) for request in source.execution_requests
    )
    value = OpenAIProviderRequestPlan(
        identity=f"scout:openai-provider-request-plan:{_ZERO}",
        fingerprint=_ZERO,
        openai_request_plan_reference=_plan_reference(source),
        provider_descriptor_reference=descriptor.provider_descriptor_reference,
        provider_descriptor_identity=descriptor.identity,
        provider_descriptor_fingerprint=descriptor.fingerprint,
        execution_plan_reference=source.execution_plan_reference,
        execution_plan_identity=source.identity,
        execution_plan_fingerprint=source.fingerprint,
        draft_reference=source.draft_reference,
        draft_fingerprint=source.draft_fingerprint,
        requests=requests,
    )
    return _seal(
        value,
        derive_openai_provider_request_plan_identity,
        derive_openai_provider_request_plan_fingerprint,
    )


def _project_request(source, request):
    messages = tuple(
        _project_message(source, request, message)
        for message in request.execution_messages
    )
    value = OpenAIProviderRequest(
        identity=f"scout:openai-provider-request:{_ZERO}",
        fingerprint=_ZERO,
        openai_request_reference=_request_reference(request),
        execution_request_reference=request.execution_request_reference,
        execution_request_identity=request.identity,
        execution_request_fingerprint=request.fingerprint,
        execution_plan_reference=source.execution_plan_reference,
        execution_plan_identity=source.identity,
        execution_plan_fingerprint=source.fingerprint,
        draft_reference=request.draft_reference,
        draft_fingerprint=request.draft_fingerprint,
        request_ordinal=request.request_ordinal,
        messages=messages,
    )
    return _seal(
        value,
        derive_openai_provider_request_identity,
        derive_openai_provider_request_fingerprint,
    )


def _project_message(source, request, message):
    value = OpenAIProviderMessage(
        identity=f"scout:openai-provider-message:{_ZERO}",
        fingerprint=_ZERO,
        openai_message_reference=_message_reference(message),
        execution_message_reference=message.execution_message_reference,
        execution_message_identity=message.identity,
        execution_message_fingerprint=message.fingerprint,
        execution_request_reference=request.execution_request_reference,
        execution_request_identity=request.identity,
        execution_request_fingerprint=request.fingerprint,
        execution_plan_reference=source.execution_plan_reference,
        execution_plan_identity=source.identity,
        execution_plan_fingerprint=source.fingerprint,
        role=_openai_role(message.execution_role),
        content=message.execution_text,
        ordinal=message.ordinal,
    )
    return _seal(
        value,
        derive_openai_provider_message_identity,
        derive_openai_provider_message_fingerprint,
    )


def _seal(value, identity_function, fingerprint_function):
    value = value.model_copy(update={"identity": identity_function(value)})
    return value.model_copy(update={"fingerprint": fingerprint_function(value)})


def validate_openai_provider_request_plan(
    provider_plan: OpenAIProviderRequestPlan,
    validation_context: ProviderMappingValidationContext,
) -> tuple[DomainValidationIssue, ...]:
    """Validate one submitted OpenAI plan against reconstructed authority."""

    reconstructed = _reconstruct(provider_plan, validation_context)
    if reconstructed.issues:
        return reconstructed.issues
    assert reconstructed.plan is not None and reconstructed.context is not None
    plan, context = reconstructed.plan, reconstructed.context
    issues = list(_seal_issues(plan))
    issues.extend(_duplicate_issues(plan))
    sources = tuple(
        item
        for item in context.execution_plans
        if item.identity == plan.execution_plan_identity
        and item.execution_plan_reference == plan.execution_plan_reference
    )
    descriptors = tuple(
        item
        for item in context.provider_descriptors
        if item.identity == plan.provider_descriptor_identity
        and item.provider_descriptor_reference == plan.provider_descriptor_reference
    )
    if len(sources) != 1:
        issues.append(
            _issue(
                "provider-mapping-unknown-execution-plan",
                plan.openai_request_plan_reference,
            )
        )
    if len(descriptors) != 1:
        issues.append(
            _issue(
                "provider-mapping-unknown-provider-descriptor",
                plan.openai_request_plan_reference,
            )
        )
    if len(sources) != 1 or len(descriptors) != 1:
        return tuple(_ordered(issues))
    if upstream := validate_draft_llm_execution_plan(
        sources[0], context.execution_validation_context
    ):
        return tuple(upstream)
    issues.extend(_compare_plan(plan, _project(sources[0], descriptors[0])))
    return tuple(_ordered(issues))


def _compare_plan(actual, expected):
    issues = _field_issues(
        actual,
        expected,
        (
            "openai_request_plan_reference",
            "provider_descriptor_reference",
            "provider_descriptor_identity",
            "provider_descriptor_fingerprint",
            "execution_plan_reference",
            "execution_plan_identity",
            "execution_plan_fingerprint",
            "draft_reference",
            "draft_fingerprint",
        ),
        "provider-mapping-openai-plan",
        actual.openai_request_plan_reference,
    )
    actual_keys = tuple(item.execution_request_identity for item in actual.requests)
    expected_keys = tuple(item.execution_request_identity for item in expected.requests)
    issues.extend(
        _completeness(
            actual_keys, expected_keys, actual.openai_request_plan_reference, "request"
        )
    )
    if actual_keys != expected_keys and Counter(actual_keys) == Counter(expected_keys):
        issues.append(
            _issue(
                "provider-mapping-invalid-request-order",
                actual.openai_request_plan_reference,
                field="requests",
            )
        )
    expected_by_key = {
        item.execution_request_identity: item for item in expected.requests
    }
    for request in actual.requests:
        if authoritative := expected_by_key.get(request.execution_request_identity):
            issues.extend(_compare_request(request, authoritative))
    return issues


def _compare_request(actual, expected):
    issues = _field_issues(
        actual,
        expected,
        (
            "openai_request_reference",
            "execution_request_reference",
            "execution_request_identity",
            "execution_request_fingerprint",
            "execution_plan_reference",
            "execution_plan_identity",
            "execution_plan_fingerprint",
            "draft_reference",
            "draft_fingerprint",
            "request_ordinal",
        ),
        "provider-mapping-openai-request",
        actual.openai_request_reference,
    )
    actual_keys = tuple(item.execution_message_identity for item in actual.messages)
    expected_keys = tuple(item.execution_message_identity for item in expected.messages)
    issues.extend(
        _completeness(
            actual_keys, expected_keys, actual.openai_request_reference, "message"
        )
    )
    if actual_keys != expected_keys and Counter(actual_keys) == Counter(expected_keys):
        issues.append(
            _issue(
                "provider-mapping-invalid-message-order",
                actual.openai_request_reference,
                field="messages",
            )
        )
    expected_by_key = {
        item.execution_message_identity: item for item in expected.messages
    }
    for message in actual.messages:
        if authoritative := expected_by_key.get(message.execution_message_identity):
            issues.extend(_compare_message(message, authoritative))
    return issues


def _compare_message(actual, expected):
    return _field_issues(
        actual,
        expected,
        (
            "openai_message_reference",
            "execution_message_reference",
            "execution_message_identity",
            "execution_message_fingerprint",
            "execution_request_reference",
            "execution_request_identity",
            "execution_request_fingerprint",
            "execution_plan_reference",
            "execution_plan_identity",
            "execution_plan_fingerprint",
            "role",
            "content",
            "ordinal",
        ),
        "provider-mapping-openai-message",
        actual.openai_message_reference,
    )


def _field_issues(actual, expected, fields, prefix, reference):
    return [
        _issue(f"{prefix}-{field.replace('_', '-')}-mismatch", reference, field=field)
        for field in fields
        if getattr(actual, field) != getattr(expected, field)
    ]


def _completeness(actual, expected, reference, kind):
    issues = []
    for value in sorted((Counter(expected) - Counter(actual)).elements()):
        issues.append(
            _issue(f"provider-mapping-missing-{kind}", reference, related=(value,))
        )
    for value in sorted((Counter(actual) - Counter(expected)).elements()):
        issues.append(
            _issue(f"provider-mapping-extra-{kind}", reference, related=(value,))
        )
    return issues


def _seal_issues(plan):
    artifacts = (
        (
            plan,
            derive_openai_provider_request_plan_identity,
            derive_openai_provider_request_plan_fingerprint,
            "plan",
            plan.openai_request_plan_reference,
        ),
        *(
            (
                request,
                derive_openai_provider_request_identity,
                derive_openai_provider_request_fingerprint,
                "request",
                request.openai_request_reference,
            )
            for request in plan.requests
        ),
        *(
            (
                message,
                derive_openai_provider_message_identity,
                derive_openai_provider_message_fingerprint,
                "message",
                message.openai_message_reference,
            )
            for request in plan.requests
            for message in request.messages
        ),
    )
    issues = []
    for artifact, identity_function, fingerprint_function, kind, reference in artifacts:
        if artifact.identity != identity_function(artifact):
            issues.append(
                _issue(f"provider-mapping-invalid-openai-{kind}-identity", reference)
            )
        if artifact.fingerprint != fingerprint_function(artifact):
            issues.append(
                _issue(f"provider-mapping-invalid-openai-{kind}-fingerprint", reference)
            )
    return issues


def _duplicate_issues(plan):
    issues = []
    for field, label in (
        ("openai_request_reference", "openai-request-reference"),
        ("identity", "openai-request-identity"),
        ("execution_request_reference", "execution-request-reference"),
        ("execution_request_identity", "execution-request-identity"),
        ("request_ordinal", "request-ordinal"),
    ):
        issues.extend(
            _duplicates(
                plan.requests,
                field,
                f"provider-mapping-duplicate-{label}",
                plan.openai_request_plan_reference,
            )
        )
    for request in plan.requests:
        for field, label in (
            ("openai_message_reference", "openai-message-reference"),
            ("identity", "openai-message-identity"),
            ("execution_message_reference", "execution-message-reference"),
            ("execution_message_identity", "execution-message-identity"),
            ("ordinal", "message-ordinal"),
        ):
            issues.extend(
                _duplicates(
                    request.messages,
                    field,
                    f"provider-mapping-duplicate-{label}",
                    request.openai_request_reference,
                )
            )
    return issues


def _duplicates(items, field, code, reference):
    values = [getattr(item, field) for item in items]
    return [
        _issue(code, reference, field=field, related=(str(value),))
        for value, count in sorted(
            Counter(values).items(), key=lambda item: str(item[0])
        )
        if count > 1
    ]


def _descriptor_issues(descriptor):
    from .provider_mapping_identity import (
        derive_provider_request_plan_descriptor_fingerprint,
        derive_provider_request_plan_descriptor_identity,
    )

    issues = []
    expected_reference = _descriptor_reference(
        descriptor.provider, descriptor.mapping_contract_version
    )
    if descriptor.provider_descriptor_reference != expected_reference:
        issues.append(
            _issue(
                "provider-mapping-noncanonical-descriptor-reference",
                descriptor.provider_descriptor_reference,
            )
        )
    if descriptor.identity != derive_provider_request_plan_descriptor_identity(
        descriptor
    ):
        issues.append(
            _issue(
                "provider-mapping-invalid-descriptor-identity",
                descriptor.provider_descriptor_reference,
            )
        )
    if descriptor.fingerprint != derive_provider_request_plan_descriptor_fingerprint(
        descriptor
    ):
        issues.append(
            _issue(
                "provider-mapping-invalid-descriptor-fingerprint",
                descriptor.provider_descriptor_reference,
            )
        )
    return issues


def _reconstruct_builder_inputs(execution_plan, descriptor, context):
    try:
        return (
            DraftLLMExecutionPlan.model_validate(
                execution_plan.model_dump(mode="python", warnings=False)
            ),
            ProviderRequestPlanDescriptor.model_validate(
                descriptor.model_dump(mode="python", warnings=False)
            ),
            ProviderMappingValidationContext.model_validate(
                context.model_dump(mode="python", warnings=False)
            ),
            (),
        )
    except (
        KeyError,
        LookupError,
        RuntimeError,
        ValueError,
        TypeError,
        ValidationError,
    ):
        return (
            None,
            None,
            None,
            (_issue("provider-mapping-invalid-builder-input", _FALLBACK),),
        )


def _reconstruct(provider_plan, context):
    try:
        plan = OpenAIProviderRequestPlan.model_validate(
            provider_plan.model_dump(mode="python", warnings=False)
        )
    except (
        KeyError,
        LookupError,
        RuntimeError,
        ValueError,
        TypeError,
        ValidationError,
    ):
        return _Reconstruction(
            None, None, (_issue("provider-mapping-invalid-openai-plan", _FALLBACK),)
        )
    try:
        rebuilt_context = ProviderMappingValidationContext.model_validate(
            context.model_dump(mode="python", warnings=False)
        )
    except (
        KeyError,
        LookupError,
        RuntimeError,
        ValueError,
        TypeError,
        ValidationError,
    ):
        return _Reconstruction(
            None, None, (_issue("provider-mapping-invalid-context", _FALLBACK),)
        )
    return _Reconstruction(plan, rebuilt_context, ())


def _safe_reference(value, fallback):
    if not isinstance(value, str):
        return fallback
    value = unicodedata.normalize("NFC", value)
    lowered = value.casefold()
    if (
        not value
        or len(value) > _MAX_REFERENCE_LENGTH
        or any(
            word in lowered
            for word in (
                "traceback",
                "exception",
                "error",
                "password",
                "secret",
                "token",
            )
        )
        or re.search(r"0x[0-9a-fA-F]+", value)
        or re.search(r"[\\/?&#=\s\x00-\x1f\x7f]", value)
        or not value.isascii()
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", value) is None
    ):
        return fallback
    return value


def _issue(code, reference, *, field=None, related=()):
    return DomainValidationIssue(
        code=code,
        artifact_reference=_safe_reference(reference, _FALLBACK),
        field_reference=field,
        field_path=(field,) if field else (),
        related_references=tuple(
            _safe_reference(value, _RELATED_FALLBACK) for value in related
        ),
        message_key=code,
    )


def _ordered(issues):
    return sorted(
        issues,
        key=lambda item: (
            item.code,
            item.artifact_reference,
            item.field_path,
            item.related_references,
        ),
    )


__all__ = (
    "build_openai_provider_request_plan",
    "validate_openai_provider_request_plan",
)

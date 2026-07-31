"""Deterministic OpenAI execution-result construction and validation."""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from pydantic import ValidationError

from .errors import DomainValidationError, DomainValidationIssue
from .extracted_result_models import OpenAIExtractedExecutionResult
from .extracted_result_validation import validate_openai_extracted_execution_result
from .openai_result_identity import (
    derive_openai_provider_execution_result_fingerprint,
    derive_openai_provider_execution_result_identity,
    derive_openai_provider_response_fingerprint,
    derive_openai_provider_response_identity,
    derive_openai_provider_response_message_fingerprint,
    derive_openai_provider_response_message_identity,
)
from .openai_result_models import (
    OpenAIProviderExecutionResult,
    OpenAIProviderResponse,
    OpenAIProviderResponseMessage,
)
from .provider_mapping_models import DraftProviderRequestPlan
from .provider_mapping_validation import validate_draft_provider_request_plan
from .provider_result_models import ProviderExecutionResultValidationContext

_ZERO = "0" * 64
_FALLBACK = "provider-result-artifact"
_RELATED_FALLBACK = "unsafe-related-reference"
_MAX_REFERENCE_LENGTH = 200
_MISSING = object()


@dataclass(frozen=True, slots=True)
class _Reconstruction:
    result: OpenAIProviderExecutionResult | None
    context: ProviderExecutionResultValidationContext | None
    issues: tuple[DomainValidationIssue, ...]


def _result_reference(plan) -> str:
    return f"openai-provider-execution-result:{plan.openai_request_plan.identity}"


def _response_reference(request) -> str:
    return f"openai-provider-response:{request.identity}"


def _message_reference(request, ordinal: int) -> str:
    return f"openai-provider-response-message:{request.identity}:{ordinal}"


def build_openai_provider_execution_result(
    provider_request_plan: DraftProviderRequestPlan | object = _MISSING,
    extracted_execution_result: (
        OpenAIExtractedExecutionResult | tuple[str, ...] | object
    ) = _MISSING,
    validation_context: (
        ProviderExecutionResultValidationContext | tuple[str, ...] | object
    ) = _MISSING,
    legacy_validation_context: ProviderExecutionResultValidationContext | None = None,
    *extra_arguments: object,
) -> OpenAIProviderExecutionResult:
    """Build an immutable result from already extracted provider output."""

    if (
        provider_request_plan is _MISSING
        or extracted_execution_result is _MISSING
        or validation_context is _MISSING
        or extra_arguments
    ):
        raise DomainValidationError(
            (_issue("provider-result-unsupported-builder-signature", _FALLBACK),)
        )

    if legacy_validation_context is not None:
        try:
            outputs = tuple(extracted_execution_result)
            reasons = tuple(validation_context)
            plan_input = DraftProviderRequestPlan.model_validate(
                provider_request_plan.model_dump(mode="python", warnings=False)
            )
            context_input = ProviderExecutionResultValidationContext.model_validate(
                legacy_validation_context.model_dump(mode="python", warnings=False)
            )
            request_count = len(plan_input.openai_request_plan.requests)
        except (
            KeyError,
            AttributeError,
            LookupError,
            RuntimeError,
            ValueError,
            TypeError,
            ValidationError,
        ):
            raise DomainValidationError(
                (_issue("provider-result-invalid-openai-builder-input", _FALLBACK),)
            ) from None
        if len(outputs) != request_count or len(reasons) != request_count:
            raise DomainValidationError(
                (_issue("provider-result-output-count-mismatch", _FALLBACK),)
            )
        if any(not isinstance(value, str) or not value for value in outputs):
            raise DomainValidationError(
                (_issue("provider-result-invalid-generated-output", _FALLBACK),)
            )
        if any(value not in {"stop", "length", "content_filter"} for value in reasons):
            raise DomainValidationError(
                (_issue("provider-result-invalid-finish-reason", _FALLBACK),)
            )
        matching = tuple(
            item
            for item in context_input.extracted_execution_results
            if item.provider_request_plan_identity == plan_input.identity
        )
        if len(matching) != 1:
            raise DomainValidationError(
                (_issue("provider-result-unresolved-extracted-authority", _FALLBACK),)
            )
        extracted_execution_result = matching[0]
        authoritative_output = tuple(
            response.messages[0].generated_text
            for response in extracted_execution_result.responses
        )
        authoritative_reasons = tuple(
            response.messages[0].finish_reason
            for response in extracted_execution_result.responses
        )
        if outputs != authoritative_output or reasons != authoritative_reasons:
            raise DomainValidationError(
                (_issue("provider-result-extracted-output-mismatch", _FALLBACK),)
            )
        provider_request_plan = plan_input
        validation_context = context_input
    plan, extracted, context, issues = _reconstruct_builder_inputs(
        provider_request_plan, extracted_execution_result, validation_context
    )
    if issues:
        raise DomainValidationError(issues)
    assert plan is not None and extracted is not None
    assert context is not None
    authorities = tuple(
        item
        for item in context.provider_request_plans
        if item.identity == plan.identity
        and item.provider_request_plan_reference == plan.provider_request_plan_reference
    )
    if len(authorities) != 1:
        raise DomainValidationError(
            (_issue("provider-result-unresolved-provider-request-plan", _FALLBACK),)
        )
    authority = authorities[0]
    if upstream := validate_draft_provider_request_plan(
        authority, context.provider_mapping_validation_context
    ):
        raise DomainValidationError(upstream)
    extracted_authorities = tuple(
        item
        for item in context.extracted_execution_results
        if item.identity == extracted.identity
        and item.extracted_execution_result_reference
        == extracted.extracted_execution_result_reference
    )
    if len(extracted_authorities) != 1:
        raise DomainValidationError(
            (_issue("provider-result-unresolved-extracted-authority", _FALLBACK),)
        )
    extracted_authority = extracted_authorities[0]
    if extracted_issues := validate_openai_extracted_execution_result(
        extracted_authority, authority, context.provider_mapping_validation_context
    ):
        raise DomainValidationError(extracted_issues)
    requests = authority.openai_request_plan.requests
    if len(extracted_authority.responses) != len(requests):
        raise DomainValidationError(
            (_issue("provider-result-output-count-mismatch", _FALLBACK),)
        )
    responses = tuple(
        _project_response(authority, request, extracted_response, ordinal)
        for ordinal, (request, extracted_response) in enumerate(
            zip(requests, extracted_authority.responses, strict=True)
        )
    )
    value = OpenAIProviderExecutionResult(
        identity=f"scout:openai-provider-execution-result:{_ZERO}",
        fingerprint=_ZERO,
        openai_provider_execution_result_reference=_result_reference(authority),
        provider="openai",
        provider_request_plan_reference=authority.provider_request_plan_reference,
        provider_request_plan_identity=authority.identity,
        provider_request_plan_fingerprint=authority.fingerprint,
        openai_request_plan_reference=authority.openai_request_plan.openai_request_plan_reference,
        openai_request_plan_identity=authority.openai_request_plan.identity,
        openai_request_plan_fingerprint=authority.openai_request_plan.fingerprint,
        execution_plan_reference=authority.execution_plan_reference,
        execution_plan_identity=authority.execution_plan_identity,
        execution_plan_fingerprint=authority.execution_plan_fingerprint,
        draft_reference=authority.draft_reference,
        draft_fingerprint=authority.draft_fingerprint,
        responses=responses,
    )
    return _seal(
        value,
        derive_openai_provider_execution_result_identity,
        derive_openai_provider_execution_result_fingerprint,
    )


def _project_response(plan, request, extracted_response, ordinal):
    extracted_message = extracted_response.messages[0]
    response_reference = _response_reference(request)
    message = OpenAIProviderResponseMessage(
        identity=f"scout:openai-provider-response-message:{_ZERO}",
        fingerprint=_ZERO,
        provider_response_message_reference=_message_reference(request, 0),
        provider_response_reference=response_reference,
        provider_request_plan_reference=plan.provider_request_plan_reference,
        provider_request_plan_identity=plan.identity,
        provider_request_plan_fingerprint=plan.fingerprint,
        openai_request_plan_reference=plan.openai_request_plan.openai_request_plan_reference,
        openai_request_plan_identity=plan.openai_request_plan.identity,
        openai_request_plan_fingerprint=plan.openai_request_plan.fingerprint,
        openai_request_reference=request.openai_request_reference,
        openai_request_identity=request.identity,
        openai_request_fingerprint=request.fingerprint,
        execution_request_reference=request.execution_request_reference,
        execution_request_identity=request.execution_request_identity,
        execution_request_fingerprint=request.execution_request_fingerprint,
        execution_plan_reference=plan.execution_plan_reference,
        execution_plan_identity=plan.execution_plan_identity,
        execution_plan_fingerprint=plan.execution_plan_fingerprint,
        draft_reference=plan.draft_reference,
        draft_fingerprint=plan.draft_fingerprint,
        ordinal=0,
        generated_text=extracted_message.generated_text,
        finish_reason=extracted_message.finish_reason,
    )
    message = _seal(
        message,
        derive_openai_provider_response_message_identity,
        derive_openai_provider_response_message_fingerprint,
    )
    response = OpenAIProviderResponse(
        identity=f"scout:openai-provider-response:{_ZERO}",
        fingerprint=_ZERO,
        provider_response_reference=response_reference,
        provider_request_plan_reference=plan.provider_request_plan_reference,
        provider_request_plan_identity=plan.identity,
        provider_request_plan_fingerprint=plan.fingerprint,
        openai_request_plan_reference=plan.openai_request_plan.openai_request_plan_reference,
        openai_request_plan_identity=plan.openai_request_plan.identity,
        openai_request_plan_fingerprint=plan.openai_request_plan.fingerprint,
        openai_request_reference=request.openai_request_reference,
        openai_request_identity=request.identity,
        openai_request_fingerprint=request.fingerprint,
        execution_request_reference=request.execution_request_reference,
        execution_request_identity=request.execution_request_identity,
        execution_request_fingerprint=request.execution_request_fingerprint,
        execution_plan_reference=plan.execution_plan_reference,
        execution_plan_identity=plan.execution_plan_identity,
        execution_plan_fingerprint=plan.execution_plan_fingerprint,
        draft_reference=plan.draft_reference,
        draft_fingerprint=plan.draft_fingerprint,
        response_ordinal=ordinal,
        messages=(message,),
    )
    return _seal(
        response,
        derive_openai_provider_response_identity,
        derive_openai_provider_response_fingerprint,
    )


def validate_openai_provider_execution_result(
    execution_result: OpenAIProviderExecutionResult,
    validation_context: ProviderExecutionResultValidationContext,
) -> tuple[DomainValidationIssue, ...]:
    """Validate one submitted OpenAI result against Phase 6.2 authority."""

    reconstructed = _reconstruct(execution_result, validation_context)
    if reconstructed.issues:
        return reconstructed.issues
    assert reconstructed.result is not None and reconstructed.context is not None
    result, context = reconstructed.result, reconstructed.context
    issues = list(_seal_issues(result))
    issues.extend(_duplicate_issues(result))
    authorities = tuple(
        item
        for item in context.provider_request_plans
        if item.identity == result.provider_request_plan_identity
        and item.provider_request_plan_reference
        == result.provider_request_plan_reference
    )
    if len(authorities) != 1:
        issues.append(
            _issue(
                "provider-result-unknown-provider-request-plan",
                result.openai_provider_execution_result_reference,
            )
        )
        return tuple(_ordered(issues))
    authority = authorities[0]
    if upstream := validate_draft_provider_request_plan(
        authority, context.provider_mapping_validation_context
    ):
        return tuple(upstream)
    extracted_authorities = tuple(
        item
        for item in context.extracted_execution_results
        if item.provider_request_plan_identity == authority.identity
        and item.provider_request_plan_reference
        == authority.provider_request_plan_reference
    )
    if len(extracted_authorities) != 1:
        issues.append(
            _issue(
                "provider-result-unresolved-extracted-authority",
                result.openai_provider_execution_result_reference,
            )
        )
        return tuple(_ordered(issues))
    extracted = extracted_authorities[0]
    if extracted_issues := validate_openai_extracted_execution_result(
        extracted, authority, context.provider_mapping_validation_context
    ):
        return tuple(extracted_issues)
    try:
        expected = build_openai_provider_execution_result(authority, extracted, context)
    except DomainValidationError as error:
        issues.extend(error.issues)
        return tuple(_ordered(issues))
    issues.extend(_compare(result, expected))
    return tuple(_ordered(issues))


def _compare(actual, expected):
    issues = []
    for field in (
        "openai_provider_execution_result_reference",
        "provider",
        "provider_request_plan_reference",
        "provider_request_plan_identity",
        "provider_request_plan_fingerprint",
        "openai_request_plan_reference",
        "openai_request_plan_identity",
        "openai_request_plan_fingerprint",
        "execution_plan_reference",
        "execution_plan_identity",
        "execution_plan_fingerprint",
        "draft_reference",
        "draft_fingerprint",
    ):
        if getattr(actual, field) != getattr(expected, field):
            issues.append(
                _issue(
                    f"provider-result-openai-{field.replace('_', '-')}-mismatch",
                    actual.openai_provider_execution_result_reference,
                    field=field,
                )
            )
    actual_keys = tuple(item.openai_request_identity for item in actual.responses)
    expected_keys = tuple(item.openai_request_identity for item in expected.responses)
    issues.extend(
        _completeness(
            actual_keys,
            expected_keys,
            actual.openai_provider_execution_result_reference,
            "response",
        )
    )
    if actual_keys != expected_keys and Counter(actual_keys) == Counter(expected_keys):
        issues.append(
            _issue(
                "provider-result-invalid-response-order",
                actual.openai_provider_execution_result_reference,
                field="responses",
            )
        )
    expected_by_key = {
        item.openai_request_identity: item for item in expected.responses
    }
    for response in actual.responses:
        authoritative = expected_by_key.get(response.openai_request_identity)
        if authoritative is not None:
            issues.extend(_field_issues(response, authoritative, "response"))
            expected_message = authoritative.messages[0]
            for message in response.messages:
                issues.extend(_field_issues(message, expected_message, "message"))
    return issues


def _field_issues(actual, expected, kind):
    issues = []
    excluded = {
        "identity",
        "fingerprint",
        "messages",
    }
    reference = getattr(
        actual,
        (
            "provider_response_reference"
            if kind == "response"
            else "provider_response_message_reference"
        ),
    )
    for field in actual.__class__.model_fields:
        if field not in excluded and getattr(actual, field) != getattr(expected, field):
            issues.append(
                _issue(
                    f"provider-result-{kind}-{field.replace('_', '-')}-mismatch",
                    reference,
                    field=field,
                )
            )
    return issues


def _seal_issues(result):
    artifacts = (
        (
            result,
            derive_openai_provider_execution_result_identity,
            derive_openai_provider_execution_result_fingerprint,
            "openai-result",
            result.openai_provider_execution_result_reference,
        ),
        *(
            (
                response,
                derive_openai_provider_response_identity,
                derive_openai_provider_response_fingerprint,
                "response",
                response.provider_response_reference,
            )
            for response in result.responses
        ),
        *(
            (
                message,
                derive_openai_provider_response_message_identity,
                derive_openai_provider_response_message_fingerprint,
                "message",
                message.provider_response_message_reference,
            )
            for response in result.responses
            for message in response.messages
        ),
    )
    issues = []
    for artifact, identity_fn, fingerprint_fn, kind, reference in artifacts:
        if artifact.identity != identity_fn(artifact):
            issues.append(_issue(f"provider-result-invalid-{kind}-identity", reference))
        if artifact.fingerprint != fingerprint_fn(artifact):
            issues.append(
                _issue(f"provider-result-invalid-{kind}-fingerprint", reference)
            )
    return issues


def _duplicate_issues(result):
    issues = []
    for field, label in (
        ("provider_response_reference", "response-reference"),
        ("identity", "response-identity"),
        ("openai_request_reference", "openai-request-reference"),
        ("openai_request_identity", "openai-request-identity"),
        ("response_ordinal", "response-ordinal"),
    ):
        issues.extend(
            _duplicates(
                result.responses,
                field,
                f"provider-result-duplicate-{label}",
                result.openai_provider_execution_result_reference,
            )
        )
    for response in result.responses:
        for field, label in (
            ("provider_response_message_reference", "message-reference"),
            ("identity", "message-identity"),
            ("ordinal", "message-ordinal"),
        ):
            issues.extend(
                _duplicates(
                    response.messages,
                    field,
                    f"provider-result-duplicate-{label}",
                    response.provider_response_reference,
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


def _completeness(actual, expected, reference, kind):
    actual_counter, expected_counter = Counter(actual), Counter(expected)
    issues = []
    for value in sorted((expected_counter - actual_counter).elements()):
        issues.append(
            _issue(f"provider-result-missing-{kind}", reference, related=(value,))
        )
    for value in sorted((actual_counter - expected_counter).elements()):
        issues.append(
            _issue(f"provider-result-extra-{kind}", reference, related=(value,))
        )
    return issues


def _reconstruct_builder_inputs(plan, extracted, context):
    try:
        rebuilt_plan = DraftProviderRequestPlan.model_validate(
            plan.model_dump(mode="python", warnings=False)
        )
    except (
        AttributeError,
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
            (_issue("provider-result-invalid-provider-request-plan-input", _FALLBACK),),
        )
    try:
        rebuilt_extracted = OpenAIExtractedExecutionResult.model_validate(
            extracted.model_dump(mode="python", warnings=False)
        )
    except (
        AttributeError,
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
            (_issue("provider-result-invalid-extracted-authority-input", _FALLBACK),),
        )
    try:
        rebuilt_context = ProviderExecutionResultValidationContext.model_validate(
            context.model_dump(mode="python", warnings=False)
        )
    except (
        AttributeError,
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
            (_issue("provider-result-invalid-validation-context-input", _FALLBACK),),
        )
    return rebuilt_plan, rebuilt_extracted, rebuilt_context, ()


def _reconstruct(result, context):
    try:
        rebuilt_result = OpenAIProviderExecutionResult.model_validate(
            result.model_dump(mode="python", warnings=False)
        )
    except (
        AttributeError,
        KeyError,
        LookupError,
        RuntimeError,
        ValueError,
        TypeError,
        ValidationError,
    ):
        return _Reconstruction(
            None,
            None,
            (_issue("provider-result-invalid-openai-result", _FALLBACK),),
        )
    try:
        rebuilt_context = ProviderExecutionResultValidationContext.model_validate(
            context.model_dump(mode="python", warnings=False)
        )
    except (
        AttributeError,
        KeyError,
        LookupError,
        RuntimeError,
        ValueError,
        TypeError,
        ValidationError,
    ):
        return _Reconstruction(
            None,
            None,
            (_issue("provider-result-invalid-context", _FALLBACK),),
        )
    return _Reconstruction(rebuilt_result, rebuilt_context, ())


def _seal(value, identity_fn, fingerprint_fn):
    value = value.model_copy(update={"identity": identity_fn(value)})
    return value.model_copy(update={"fingerprint": fingerprint_fn(value)})


def _safe_reference(value, fallback):
    if not isinstance(value, str):
        return fallback
    normalized = unicodedata.normalize("NFC", value)
    lowered = normalized.casefold()
    if (
        not normalized
        or len(normalized) > _MAX_REFERENCE_LENGTH
        or any(
            word in lowered for word in ("traceback", "exception", "secret", "token")
        )
        or re.search(r"0x[0-9a-fA-F]+", normalized)
        or re.search(r"[\\/?&#=\s\x00-\x1f\x7f]", normalized)
        or not normalized.isascii()
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", normalized) is None
    ):
        return fallback
    return normalized


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
    "build_openai_provider_execution_result",
    "validate_openai_provider_execution_result",
)

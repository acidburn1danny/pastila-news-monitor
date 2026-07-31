"""Construction and validation of independent extracted-result authority."""

import re
import unicodedata
from collections import Counter

from pydantic import ValidationError

from .errors import DomainValidationError, DomainValidationIssue
from .extracted_result_identity import (
    derive_openai_extracted_execution_result_fingerprint,
    derive_openai_extracted_execution_result_identity,
    derive_openai_extracted_response_fingerprint,
    derive_openai_extracted_response_identity,
    derive_openai_extracted_response_message_fingerprint,
    derive_openai_extracted_response_message_identity,
)
from .extracted_result_models import (
    OpenAIExtractedExecutionResult,
    OpenAIExtractedResponse,
    OpenAIExtractedResponseMessage,
)
from .provider_mapping_models import (
    DraftProviderRequestPlan,
    ProviderMappingValidationContext,
)
from .provider_mapping_validation import validate_draft_provider_request_plan

_ZERO = "0" * 64
_FALLBACK = "extracted-result-authority"
_RELATED_FALLBACK = "unsafe-related-reference"


def _execution_reference(plan) -> str:
    return f"openai-extracted-execution-result:{plan.openai_request_plan.identity}"


def _response_reference(request) -> str:
    return f"openai-extracted-response:{request.identity}"


def _message_reference(request, ordinal: int) -> str:
    return f"openai-extracted-response-message:{request.identity}:{ordinal}"


def build_openai_extracted_execution_result(
    provider_request_plan: DraftProviderRequestPlan,
    generated_outputs: tuple[str, ...],
    finish_reasons: tuple[str, ...],
    mapping_validation_context: ProviderMappingValidationContext,
) -> OpenAIExtractedExecutionResult:
    """Create sealed independent authority from already extracted output."""

    try:
        if isinstance(generated_outputs, (str, bytes, dict)) or isinstance(
            finish_reasons, (str, bytes, dict)
        ):
            raise TypeError
        plan = DraftProviderRequestPlan.model_validate(
            provider_request_plan.model_dump(mode="python", warnings=False)
        )
        context = ProviderMappingValidationContext.model_validate(
            mapping_validation_context.model_dump(mode="python", warnings=False)
        )
        outputs, reasons = tuple(generated_outputs), tuple(finish_reasons)
    except (
        AttributeError,
        KeyError,
        LookupError,
        RuntimeError,
        ValueError,
        TypeError,
        ValidationError,
    ):
        raise DomainValidationError(
            (_issue("extracted-result-invalid-builder-input", _FALLBACK),)
        ) from None
    if upstream := validate_draft_provider_request_plan(plan, context):
        raise DomainValidationError(upstream)
    requests = plan.openai_request_plan.requests
    if len(outputs) != len(requests) or len(reasons) != len(requests):
        raise DomainValidationError(
            (_issue("extracted-result-output-count-mismatch", _FALLBACK),)
        )
    if any(not isinstance(value, str) or not value for value in outputs):
        raise DomainValidationError(
            (_issue("extracted-result-invalid-generated-output", _FALLBACK),)
        )
    if any(value not in {"stop", "length", "content_filter"} for value in reasons):
        raise DomainValidationError(
            (_issue("extracted-result-invalid-finish-reason", _FALLBACK),)
        )
    responses = tuple(
        _response(plan, request, ordinal, text, reason)
        for ordinal, (request, text, reason) in enumerate(
            zip(requests, outputs, reasons, strict=True)
        )
    )
    value = OpenAIExtractedExecutionResult(
        identity=f"scout:openai-extracted-execution-result:{_ZERO}",
        fingerprint=_ZERO,
        extracted_execution_result_reference=_execution_reference(plan),
        provider="openai",
        provider_request_plan_reference=plan.provider_request_plan_reference,
        provider_request_plan_identity=plan.identity,
        provider_request_plan_fingerprint=plan.fingerprint,
        openai_request_plan_reference=plan.openai_request_plan.openai_request_plan_reference,
        openai_request_plan_identity=plan.openai_request_plan.identity,
        openai_request_plan_fingerprint=plan.openai_request_plan.fingerprint,
        execution_plan_reference=plan.execution_plan_reference,
        execution_plan_identity=plan.execution_plan_identity,
        execution_plan_fingerprint=plan.execution_plan_fingerprint,
        draft_reference=plan.draft_reference,
        draft_fingerprint=plan.draft_fingerprint,
        responses=responses,
    )
    return _seal(
        value,
        derive_openai_extracted_execution_result_identity,
        derive_openai_extracted_execution_result_fingerprint,
    )


def _response(plan, request, ordinal, text, reason):
    response_reference = _response_reference(request)
    message = OpenAIExtractedResponseMessage(
        identity=f"scout:openai-extracted-response-message:{_ZERO}",
        fingerprint=_ZERO,
        extracted_response_message_reference=_message_reference(request, 0),
        extracted_response_reference=response_reference,
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
        generated_text=text,
        finish_reason=reason,
    )
    message = _seal(
        message,
        derive_openai_extracted_response_message_identity,
        derive_openai_extracted_response_message_fingerprint,
    )
    response = OpenAIExtractedResponse(
        identity=f"scout:openai-extracted-response:{_ZERO}",
        fingerprint=_ZERO,
        extracted_response_reference=response_reference,
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
        derive_openai_extracted_response_identity,
        derive_openai_extracted_response_fingerprint,
    )


def validate_openai_extracted_execution_result(
    authority: OpenAIExtractedExecutionResult,
    provider_request_plan: DraftProviderRequestPlan,
    mapping_validation_context: ProviderMappingValidationContext,
) -> tuple[DomainValidationIssue, ...]:
    """Validate extracted authority against frozen Phase 6.2 ownership."""

    try:
        value = OpenAIExtractedExecutionResult.model_validate(
            authority.model_dump(mode="python", warnings=False)
        )
        plan = DraftProviderRequestPlan.model_validate(
            provider_request_plan.model_dump(mode="python", warnings=False)
        )
        context = ProviderMappingValidationContext.model_validate(
            mapping_validation_context.model_dump(mode="python", warnings=False)
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
        return (_issue("extracted-result-invalid-reconstruction", _FALLBACK),)
    if upstream := validate_draft_provider_request_plan(plan, context):
        return tuple(upstream)
    issues = list(_seal_issues(value))
    issues.extend(_duplicate_issues(value))
    if any(len(response.messages) != 1 for response in value.responses):
        issues.append(
            _issue(
                "extracted-result-invalid-message-cardinality",
                value.extracted_execution_result_reference,
            )
        )
        return tuple(_ordered(issues))
    outputs = tuple(response.messages[0].generated_text for response in value.responses)
    reasons = tuple(response.messages[0].finish_reason for response in value.responses)
    if len(outputs) != len(plan.openai_request_plan.requests):
        issues.append(
            _issue(
                "extracted-result-output-count-mismatch",
                value.extracted_execution_result_reference,
            )
        )
        return tuple(_ordered(issues))
    try:
        expected = build_openai_extracted_execution_result(
            plan, outputs, reasons, context
        )
    except DomainValidationError as error:
        return tuple(error.issues)
    issues.extend(_compare(value, expected))
    return tuple(_ordered(issues))


def _compare(actual, expected):
    issues = []
    for field in actual.__class__.model_fields:
        if field not in {"identity", "fingerprint", "responses"} and getattr(
            actual, field
        ) != getattr(expected, field):
            issues.append(_mismatch("execution", actual, field))
    actual_keys = tuple(item.openai_request_identity for item in actual.responses)
    expected_keys = tuple(item.openai_request_identity for item in expected.responses)
    issues.extend(
        _completeness(
            actual_keys,
            expected_keys,
            actual.extracted_execution_result_reference,
            "response",
        )
    )
    if actual_keys != expected_keys and Counter(actual_keys) == Counter(expected_keys):
        issues.append(
            _issue(
                "extracted-result-invalid-response-order",
                actual.extracted_execution_result_reference,
                field="responses",
            )
        )
    expected_by_key = {
        item.openai_request_identity: item for item in expected.responses
    }
    for response in actual.responses:
        expected_response = expected_by_key.get(response.openai_request_identity)
        if expected_response is None:
            continue
        for field in response.__class__.model_fields:
            if field not in {"identity", "fingerprint", "messages"} and getattr(
                response, field
            ) != getattr(expected_response, field):
                issues.append(_mismatch("response", response, field))
        expected_message = expected_response.messages[0]
        for message in response.messages:
            for field in message.__class__.model_fields:
                if field not in {
                    "identity",
                    "fingerprint",
                    "generated_text",
                    "finish_reason",
                } and getattr(message, field) != getattr(expected_message, field):
                    issues.append(_mismatch("message", message, field))
    return issues


def _mismatch(kind, value, field):
    reference = getattr(
        value,
        {
            "execution": "extracted_execution_result_reference",
            "response": "extracted_response_reference",
            "message": "extracted_response_message_reference",
        }[kind],
    )
    return _issue(
        f"extracted-result-{kind}-{field.replace('_', '-')}-mismatch",
        reference,
        field=field,
    )


def _seal_issues(value):
    artifacts = [
        (
            value,
            derive_openai_extracted_execution_result_identity,
            derive_openai_extracted_execution_result_fingerprint,
            "execution",
            value.extracted_execution_result_reference,
        )
    ]
    artifacts.extend(
        (
            response,
            derive_openai_extracted_response_identity,
            derive_openai_extracted_response_fingerprint,
            "response",
            response.extracted_response_reference,
        )
        for response in value.responses
    )
    artifacts.extend(
        (
            message,
            derive_openai_extracted_response_message_identity,
            derive_openai_extracted_response_message_fingerprint,
            "message",
            message.extracted_response_message_reference,
        )
        for response in value.responses
        for message in response.messages
    )
    issues = []
    for artifact, identity_fn, fingerprint_fn, kind, reference in artifacts:
        if artifact.identity != identity_fn(artifact):
            issues.append(
                _issue(f"extracted-result-invalid-{kind}-identity", reference)
            )
        if artifact.fingerprint != fingerprint_fn(artifact):
            issues.append(
                _issue(f"extracted-result-invalid-{kind}-fingerprint", reference)
            )
    return issues


def _duplicate_issues(value):
    issues = []
    for field in (
        "extracted_response_reference",
        "identity",
        "openai_request_reference",
        "openai_request_identity",
        "response_ordinal",
    ):
        issues.extend(
            _duplicates(
                value.responses, field, value.extracted_execution_result_reference
            )
        )
    for response in value.responses:
        for field in (
            "extracted_response_message_reference",
            "identity",
            "extracted_response_reference",
            "openai_request_reference",
            "openai_request_identity",
            "ordinal",
        ):
            issues.extend(
                _duplicates(
                    response.messages, field, response.extracted_response_reference
                )
            )
    return issues


def _duplicates(items, field, reference):
    values = [getattr(item, field) for item in items]
    return [
        _issue(
            f"extracted-result-duplicate-{field.replace('_', '-')}",
            reference,
            field=field,
            related=(str(value),),
        )
        for value, count in sorted(
            Counter(values).items(), key=lambda item: str(item[0])
        )
        if count > 1
    ]


def _completeness(actual, expected, reference, kind):
    actual_counter, expected_counter = Counter(actual), Counter(expected)
    return tuple(
        _issue(f"extracted-result-missing-{kind}", reference, related=(value,))
        for value in sorted((expected_counter - actual_counter).elements())
    ) + tuple(
        _issue(f"extracted-result-extra-{kind}", reference, related=(value,))
        for value in sorted((actual_counter - expected_counter).elements())
    )


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
        or len(normalized) > 200
        or any(
            word in lowered
            for word in ("traceback", "exception", "secret", "token", "key")
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
    "build_openai_extracted_execution_result",
    "validate_openai_extracted_execution_result",
)

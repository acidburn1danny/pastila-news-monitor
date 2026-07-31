"""Generic deterministic execution-result dispatch and validation for Phase 6.3."""

from dataclasses import dataclass

from pydantic import ValidationError

from .errors import DomainValidationError, DomainValidationIssue
from .extracted_result_models import OpenAIExtractedExecutionResult
from .openai_result_validation import (
    _issue,
    _ordered,
    build_openai_provider_execution_result,
    validate_openai_provider_execution_result,
)
from .provider_mapping_models import DraftProviderRequestPlan
from .provider_result_identity import (
    derive_provider_execution_result_fingerprint,
    derive_provider_execution_result_identity,
)
from .provider_result_models import (
    ProviderExecutionResult,
    ProviderExecutionResultValidationContext,
)

_ZERO = "0" * 64
_FALLBACK = "provider-result-artifact"
_MISSING = object()


@dataclass(frozen=True, slots=True)
class _Reconstruction:
    result: ProviderExecutionResult | None
    context: ProviderExecutionResultValidationContext | None
    issues: tuple[DomainValidationIssue, ...]


def _result_reference(plan) -> str:
    return (
        "provider-execution-result:"
        f"{plan.provider_descriptor.provider}:{plan.identity}"
    )


def build_provider_execution_result(
    provider_request_plan: DraftProviderRequestPlan | object = _MISSING,
    extracted_execution_result: (
        OpenAIExtractedExecutionResult | tuple[str, ...] | object
    ) = _MISSING,
    validation_context: (
        ProviderExecutionResultValidationContext | tuple[str, ...] | object
    ) = _MISSING,
    legacy_validation_context: ProviderExecutionResultValidationContext | None = None,
    *extra_arguments: object,
) -> ProviderExecutionResult:
    """Dispatch and wrap one typed result without executing a provider."""

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
                (_issue("provider-result-invalid-generic-builder-input", _FALLBACK),)
            ) from None
        if len(outputs) != request_count or len(reasons) != request_count:
            raise DomainValidationError(
                (_issue("provider-result-output-count-mismatch", _FALLBACK),)
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
        authority_outputs = tuple(
            response.messages[0].generated_text
            for response in extracted_execution_result.responses
        )
        authority_reasons = tuple(
            response.messages[0].finish_reason
            for response in extracted_execution_result.responses
        )
        if outputs != authority_outputs or reasons != authority_reasons:
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
    assert plan is not None and extracted is not None and context is not None
    concrete = build_openai_provider_execution_result(plan, extracted, context)
    value = ProviderExecutionResult(
        identity=f"scout:provider-execution-result:{_ZERO}",
        fingerprint=_ZERO,
        provider_execution_result_reference=_result_reference(plan),
        provider=plan.provider_descriptor.provider,
        execution_plan_reference=plan.execution_plan_reference,
        execution_plan_identity=plan.execution_plan_identity,
        execution_plan_fingerprint=plan.execution_plan_fingerprint,
        provider_request_plan_reference=plan.provider_request_plan_reference,
        provider_request_plan_identity=plan.identity,
        provider_request_plan_fingerprint=plan.fingerprint,
        draft_reference=plan.draft_reference,
        draft_fingerprint=plan.draft_fingerprint,
        provider_result_reference=concrete.openai_provider_execution_result_reference,
        provider_result_identity=concrete.identity,
        provider_result_fingerprint=concrete.fingerprint,
        openai_execution_result=concrete,
    )
    value = value.model_copy(
        update={"identity": derive_provider_execution_result_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": derive_provider_execution_result_fingerprint(value)}
    )


def validate_provider_execution_result(
    execution_result: ProviderExecutionResult,
    validation_context: ProviderExecutionResultValidationContext,
) -> tuple[DomainValidationIssue, ...]:
    """Validate a generic execution-result wrapper and concrete result."""

    reconstructed = _reconstruct(execution_result, validation_context)
    if reconstructed.issues:
        return reconstructed.issues
    assert reconstructed.result is not None and reconstructed.context is not None
    result, context = reconstructed.result, reconstructed.context
    issues = []
    if result.identity != derive_provider_execution_result_identity(result):
        issues.append(
            _issue(
                "provider-result-invalid-generic-result-identity",
                result.provider_execution_result_reference,
            )
        )
    if result.fingerprint != derive_provider_execution_result_fingerprint(result):
        issues.append(
            _issue(
                "provider-result-invalid-generic-result-fingerprint",
                result.provider_execution_result_reference,
            )
        )
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
                result.provider_execution_result_reference,
            )
        )
        return tuple(_ordered(issues))
    extracted_authorities = tuple(
        item
        for item in context.extracted_execution_results
        if item.provider_request_plan_identity == authorities[0].identity
        and item.provider_request_plan_reference
        == authorities[0].provider_request_plan_reference
    )
    if len(extracted_authorities) != 1:
        issues.append(
            _issue(
                "provider-result-unresolved-extracted-authority",
                result.provider_execution_result_reference,
            )
        )
        return tuple(_ordered(issues))
    try:
        expected = build_provider_execution_result(
            authorities[0], extracted_authorities[0], context
        )
    except DomainValidationError as error:
        return tuple(error.issues)
    for field in (
        "provider_execution_result_reference",
        "provider",
        "execution_plan_reference",
        "execution_plan_identity",
        "execution_plan_fingerprint",
        "provider_request_plan_reference",
        "provider_request_plan_identity",
        "provider_request_plan_fingerprint",
        "draft_reference",
        "draft_fingerprint",
        "provider_result_reference",
        "provider_result_identity",
        "provider_result_fingerprint",
        "openai_execution_result",
    ):
        if getattr(result, field) != getattr(expected, field):
            issues.append(
                _issue(
                    f"provider-result-generic-{field.replace('_', '-')}-mismatch",
                    result.provider_execution_result_reference,
                    field=field,
                )
            )
    issues.extend(
        validate_openai_provider_execution_result(
            result.openai_execution_result, context
        )
    )
    return tuple(_ordered(issues))


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
        rebuilt_result = ProviderExecutionResult.model_validate(
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
            (_issue("provider-result-invalid-generic-result", _FALLBACK),),
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


__all__ = (
    "build_provider_execution_result",
    "validate_provider_execution_result",
)

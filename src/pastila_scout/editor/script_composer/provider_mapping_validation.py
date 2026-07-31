"""Common deterministic dispatch and validation for Phase 6.2."""

from dataclasses import dataclass

from pydantic import ValidationError

from .errors import DomainValidationError, DomainValidationIssue
from .llm_execution_models import DraftLLMExecutionPlan
from .openai_mapping_validation import (
    _descriptor_issues,
    _issue,
    _ordered,
    build_openai_provider_request_plan,
    validate_openai_provider_request_plan,
)
from .provider_mapping_identity import (
    derive_draft_provider_request_plan_fingerprint,
    derive_draft_provider_request_plan_identity,
)
from .provider_mapping_models import (
    DraftProviderRequestPlan,
    ProviderMappingValidationContext,
    ProviderRequestPlanDescriptor,
)

_ZERO = "0" * 64
_FALLBACK = "provider-mapping-artifact"


@dataclass(frozen=True, slots=True)
class _Reconstruction:
    plan: DraftProviderRequestPlan | None
    context: ProviderMappingValidationContext | None
    issues: tuple[DomainValidationIssue, ...]


def _provider_plan_reference(descriptor, execution_plan) -> str:
    return f"provider-request-plan:{descriptor.provider}:{execution_plan.identity}"


def build_draft_provider_request_plan(
    execution_plan: DraftLLMExecutionPlan,
    provider_descriptor: ProviderRequestPlanDescriptor,
    validation_context: ProviderMappingValidationContext,
) -> DraftProviderRequestPlan:
    """Dispatch deterministically and wrap one typed concrete provider plan."""

    source, descriptor, context, issues = _reconstruct_builder_inputs(
        execution_plan, provider_descriptor, validation_context
    )
    if issues:
        raise DomainValidationError(issues)
    assert source is not None and descriptor is not None and context is not None
    if descriptor_issues := _descriptor_issues(descriptor):
        raise DomainValidationError(tuple(_ordered(descriptor_issues)))
    concrete = build_openai_provider_request_plan(source, descriptor, context)
    value = DraftProviderRequestPlan(
        identity=f"scout:draft-provider-request-plan:{_ZERO}",
        fingerprint=_ZERO,
        provider_request_plan_reference=_provider_plan_reference(descriptor, source),
        provider_descriptor=descriptor,
        execution_plan_reference=source.execution_plan_reference,
        execution_plan_identity=source.identity,
        execution_plan_fingerprint=source.fingerprint,
        draft_reference=source.draft_reference,
        draft_fingerprint=source.draft_fingerprint,
        provider_plan_reference=concrete.openai_request_plan_reference,
        provider_plan_identity=concrete.identity,
        provider_plan_fingerprint=concrete.fingerprint,
        openai_request_plan=concrete,
    )
    value = value.model_copy(
        update={"identity": derive_draft_provider_request_plan_identity(value)}
    )
    return value.model_copy(
        update={"fingerprint": derive_draft_provider_request_plan_fingerprint(value)}
    )


def validate_draft_provider_request_plan(
    provider_plan: DraftProviderRequestPlan,
    validation_context: ProviderMappingValidationContext,
) -> tuple[DomainValidationIssue, ...]:
    """Validate a generic wrapper and its concrete provider plan."""

    reconstructed = _reconstruct(provider_plan, validation_context)
    if reconstructed.issues:
        return reconstructed.issues
    assert reconstructed.plan is not None and reconstructed.context is not None
    plan, context = reconstructed.plan, reconstructed.context
    issues = list(_descriptor_issues(plan.provider_descriptor))
    if plan.identity != derive_draft_provider_request_plan_identity(plan):
        issues.append(
            _issue(
                "provider-mapping-invalid-generic-plan-identity",
                plan.provider_request_plan_reference,
            )
        )
    if plan.fingerprint != derive_draft_provider_request_plan_fingerprint(plan):
        issues.append(
            _issue(
                "provider-mapping-invalid-generic-plan-fingerprint",
                plan.provider_request_plan_reference,
            )
        )
    sources = tuple(
        item
        for item in context.execution_plans
        if item.identity == plan.execution_plan_identity
        and item.execution_plan_reference == plan.execution_plan_reference
    )
    descriptors = tuple(
        item
        for item in context.provider_descriptors
        if item.identity == plan.provider_descriptor.identity
        and item.provider_descriptor_reference
        == plan.provider_descriptor.provider_descriptor_reference
    )
    if len(sources) != 1:
        issues.append(
            _issue(
                "provider-mapping-unknown-execution-plan",
                plan.provider_request_plan_reference,
            )
        )
    if len(descriptors) != 1:
        issues.append(
            _issue(
                "provider-mapping-unknown-provider-descriptor",
                plan.provider_request_plan_reference,
            )
        )
    if len(sources) != 1 or len(descriptors) != 1:
        return tuple(_ordered(issues))
    try:
        expected = build_draft_provider_request_plan(
            sources[0], descriptors[0], context
        )
    except DomainValidationError as error:
        return tuple(error.issues)
    for field in (
        "provider_request_plan_reference",
        "provider_descriptor",
        "execution_plan_reference",
        "execution_plan_identity",
        "execution_plan_fingerprint",
        "draft_reference",
        "draft_fingerprint",
        "provider_plan_reference",
        "provider_plan_identity",
        "provider_plan_fingerprint",
        "openai_request_plan",
    ):
        if getattr(plan, field) != getattr(expected, field):
            issues.append(
                _issue(
                    f"provider-mapping-generic-{field.replace('_', '-')}-mismatch",
                    plan.provider_request_plan_reference,
                    field=field,
                )
            )
    issues.extend(
        validate_openai_provider_request_plan(plan.openai_request_plan, context)
    )
    return tuple(_ordered(issues))


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
            (_issue("provider-mapping-invalid-generic-builder-input", _FALLBACK),),
        )


def _reconstruct(provider_plan, context):
    try:
        plan = DraftProviderRequestPlan.model_validate(
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
            None,
            None,
            (_issue("provider-mapping-invalid-generic-plan", _FALLBACK),),
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
            None,
            None,
            (_issue("provider-mapping-invalid-context", _FALLBACK),),
        )
    return _Reconstruction(plan, rebuilt_context, ())


__all__ = (
    "build_draft_provider_request_plan",
    "validate_draft_provider_request_plan",
)

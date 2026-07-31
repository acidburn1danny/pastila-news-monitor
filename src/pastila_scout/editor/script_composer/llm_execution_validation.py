"""Construction and validation for provider-neutral Phase 6.1 execution plans."""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from pydantic import ValidationError

from .canonical import semantic_fingerprint
from .errors import DomainValidationError, DomainValidationIssue
from .identity import derive_identity
from .llm_execution_identity import (
    derive_draft_llm_execution_plan_fingerprint,
    derive_draft_llm_execution_plan_identity,
    derive_llm_execution_message_fingerprint,
    derive_llm_execution_message_identity,
    derive_llm_execution_request_fingerprint,
    derive_llm_execution_request_identity,
)
from .llm_execution_models import (
    DraftLLMExecutionPlan,
    LLMExecutionMessage,
    LLMExecutionRequest,
    LLMExecutionValidationContext,
)
from .prompt_rendering_models import DraftRenderedPromptPlan
from .prompt_rendering_validation import validate_draft_rendered_prompt_plan

_ZERO = "0" * 64
_ARTIFACT_FALLBACK = "llm-execution-artifact"
_PLAN_FALLBACK = "draft-llm-execution-plan"
_RELATED_FALLBACK = "unsafe-related-reference"
_MAX_REFERENCE_LENGTH = 200


@dataclass(frozen=True, slots=True)
class _Reconstruction:
    plan: DraftLLMExecutionPlan | None
    context: LLMExecutionValidationContext | None
    issues: tuple[DomainValidationIssue, ...]


def _canonical_execution_plan_reference(rendered_plan) -> str:
    return f"llm-execution-plan:{rendered_plan.identity}"


def _canonical_execution_request_reference(rendered_section) -> str:
    return f"llm-execution-request:{rendered_section.identity}"


def _canonical_execution_message_reference(rendered_message) -> str:
    return f"llm-execution-message:{rendered_message.identity}"


def _local_normalized_input_lineage_identity(reference: str) -> str:
    return derive_identity(
        "llm-execution-normalized-input-lineage",
        {
            "lineage_owner": "phase-6.1",
            "normalized_input_reference": reference,
        },
    )


def _local_normalized_input_lineage_fingerprint(reference: str) -> str:
    return semantic_fingerprint(
        {
            "lineage_owner": "phase-6.1",
            "normalized_input_reference": reference,
        }
    )


def build_draft_llm_execution_plan(
    rendered_plan: DraftRenderedPromptPlan,
    validation_context: LLMExecutionValidationContext,
) -> DraftLLMExecutionPlan:
    """Build one deterministic plan from valid authoritative Phase 5.2 state."""

    source, context, issues = _reconstruct_builder_inputs(
        rendered_plan, validation_context
    )
    if issues:
        raise DomainValidationError(issues)
    assert source is not None and context is not None
    matches = tuple(
        item
        for item in context.rendered_prompt_plans
        if item.identity == source.identity
        and item.rendered_plan_reference == source.rendered_plan_reference
    )
    if len(matches) != 1:
        raise DomainValidationError(
            (
                _issue(
                    "llm-execution-unresolved-rendered-plan",
                    source.rendered_plan_reference,
                ),
            )
        )
    if upstream := validate_draft_rendered_prompt_plan(
        source, context.rendered_prompt_validation_context
    ):
        raise DomainValidationError(upstream)
    return _project(source)


def _project(source: DraftRenderedPromptPlan) -> DraftLLMExecutionPlan:
    requests = tuple(
        _project_request(source, section, request_ordinal)
        for request_ordinal, section in enumerate(source.rendered_sections)
    )
    value = DraftLLMExecutionPlan(
        identity=f"scout:draft-llm-execution-plan:{_ZERO}",
        fingerprint=_ZERO,
        execution_plan_reference=_canonical_execution_plan_reference(source),
        rendered_plan_reference=source.rendered_plan_reference,
        rendered_plan_identity=source.identity,
        rendered_plan_fingerprint=source.fingerprint,
        request_plan_reference=source.source_request_plan_reference,
        request_plan_identity=source.source_request_plan_identity,
        request_plan_fingerprint=source.source_request_plan_fingerprint,
        draft_reference=source.draft_reference,
        draft_fingerprint=source.draft_fingerprint,
        normalized_input_reference=source.normalized_input_reference,
        normalized_input_identity=_local_normalized_input_lineage_identity(
            source.normalized_input_reference
        ),
        normalized_input_fingerprint=_local_normalized_input_lineage_fingerprint(
            source.normalized_input_reference
        ),
        execution_requests=requests,
    )
    return _seal(
        value,
        derive_draft_llm_execution_plan_identity,
        derive_draft_llm_execution_plan_fingerprint,
    )


def _project_request(source, section, request_ordinal):
    messages = tuple(
        _project_message(source, section, message)
        for message in section.rendered_messages
    )
    value = LLMExecutionRequest(
        identity=f"scout:llm-execution-request:{_ZERO}",
        fingerprint=_ZERO,
        execution_request_reference=_canonical_execution_request_reference(section),
        rendered_section_reference=section.rendered_section_reference,
        rendered_section_identity=section.identity,
        rendered_section_fingerprint=section.fingerprint,
        rendered_plan_reference=source.rendered_plan_reference,
        rendered_plan_identity=source.identity,
        rendered_plan_fingerprint=source.fingerprint,
        draft_reference=source.draft_reference,
        draft_fingerprint=source.draft_fingerprint,
        request_ordinal=request_ordinal,
        execution_messages=messages,
    )
    return _seal(
        value,
        derive_llm_execution_request_identity,
        derive_llm_execution_request_fingerprint,
    )


def _project_message(source, section, message):
    value = LLMExecutionMessage(
        identity=f"scout:llm-execution-message:{_ZERO}",
        fingerprint=_ZERO,
        execution_message_reference=_canonical_execution_message_reference(message),
        rendered_message_reference=message.rendered_message_reference,
        rendered_message_identity=message.identity,
        rendered_message_fingerprint=message.fingerprint,
        rendered_section_reference=section.rendered_section_reference,
        rendered_section_identity=section.identity,
        rendered_section_fingerprint=section.fingerprint,
        rendered_plan_reference=source.rendered_plan_reference,
        rendered_plan_identity=source.identity,
        rendered_plan_fingerprint=source.fingerprint,
        execution_role=message.rendering_role,
        execution_text=message.rendered_text,
        ordinal=message.ordinal,
    )
    return _seal(
        value,
        derive_llm_execution_message_identity,
        derive_llm_execution_message_fingerprint,
    )


def _seal(value, identity_function, fingerprint_function):
    value = value.model_copy(update={"identity": identity_function(value)})
    return value.model_copy(update={"fingerprint": fingerprint_function(value)})


def validate_draft_llm_execution_plan(
    execution_plan: DraftLLMExecutionPlan,
    validation_context: LLMExecutionValidationContext,
) -> tuple[DomainValidationIssue, ...]:
    """Return deterministic findings for one submitted execution plan."""

    reconstructed = _reconstruct(execution_plan, validation_context)
    if reconstructed.issues:
        return reconstructed.issues
    assert reconstructed.plan is not None and reconstructed.context is not None
    plan = reconstructed.plan
    context = reconstructed.context
    issues = list(_seal_issues(plan))
    issues.extend(_duplicate_issues(plan))
    sources = tuple(
        item
        for item in context.rendered_prompt_plans
        if item.identity == plan.rendered_plan_identity
        and item.rendered_plan_reference == plan.rendered_plan_reference
    )
    if len(sources) != 1:
        issues.append(
            _issue(
                "llm-execution-unknown-rendered-plan",
                plan.execution_plan_reference,
                field="rendered_plan_reference",
            )
        )
        return tuple(_ordered(issues))
    source = sources[0]
    if upstream := validate_draft_rendered_prompt_plan(
        source, context.rendered_prompt_validation_context
    ):
        return tuple(upstream)
    expected = _project(source)
    issues.extend(_compare_plan(plan, expected))
    return tuple(_ordered(issues))


def _compare_plan(actual, expected):
    issues = []
    fields = (
        "execution_plan_reference",
        "rendered_plan_reference",
        "rendered_plan_identity",
        "rendered_plan_fingerprint",
        "request_plan_reference",
        "request_plan_identity",
        "request_plan_fingerprint",
        "draft_reference",
        "draft_fingerprint",
        "normalized_input_reference",
        "normalized_input_identity",
        "normalized_input_fingerprint",
    )
    for field in fields:
        if getattr(actual, field) != getattr(expected, field):
            issues.append(
                _issue(
                    f"llm-execution-{field.replace('_', '-')}-mismatch",
                    actual.execution_plan_reference,
                    field=field,
                )
            )
    actual_refs = tuple(
        item.rendered_section_identity for item in actual.execution_requests
    )
    expected_refs = tuple(
        item.rendered_section_identity for item in expected.execution_requests
    )
    issues.extend(
        _completeness(
            actual_refs,
            expected_refs,
            actual.execution_plan_reference,
            "request",
        )
    )
    if actual_refs != expected_refs and Counter(actual_refs) == Counter(expected_refs):
        issues.append(
            _issue(
                "llm-execution-invalid-request-order",
                actual.execution_plan_reference,
                field="execution_requests",
            )
        )
    expected_by_source = {
        item.rendered_section_identity: item for item in expected.execution_requests
    }
    for request in actual.execution_requests:
        authoritative = expected_by_source.get(request.rendered_section_identity)
        if authoritative is not None:
            issues.extend(_compare_request(request, authoritative))
    return issues


def _compare_request(actual, expected):
    issues = []
    for field in (
        "execution_request_reference",
        "rendered_section_reference",
        "rendered_section_identity",
        "rendered_section_fingerprint",
        "rendered_plan_reference",
        "rendered_plan_identity",
        "rendered_plan_fingerprint",
        "draft_reference",
        "draft_fingerprint",
        "request_ordinal",
    ):
        if getattr(actual, field) != getattr(expected, field):
            issues.append(
                _issue(
                    f"llm-execution-request-{field.replace('_', '-')}-mismatch",
                    actual.execution_request_reference,
                    field=field,
                )
            )
    actual_refs = tuple(
        item.rendered_message_identity for item in actual.execution_messages
    )
    expected_refs = tuple(
        item.rendered_message_identity for item in expected.execution_messages
    )
    issues.extend(
        _completeness(
            actual_refs,
            expected_refs,
            actual.execution_request_reference,
            "message",
        )
    )
    if actual_refs != expected_refs and Counter(actual_refs) == Counter(expected_refs):
        issues.append(
            _issue(
                "llm-execution-invalid-message-order",
                actual.execution_request_reference,
                field="execution_messages",
            )
        )
    expected_by_source = {
        item.rendered_message_identity: item for item in expected.execution_messages
    }
    for message in actual.execution_messages:
        authoritative = expected_by_source.get(message.rendered_message_identity)
        if authoritative is not None:
            issues.extend(_compare_message(message, authoritative))
    return issues


def _compare_message(actual, expected):
    issues = []
    for field in (
        "execution_message_reference",
        "rendered_message_reference",
        "rendered_message_identity",
        "rendered_message_fingerprint",
        "rendered_section_reference",
        "rendered_section_identity",
        "rendered_section_fingerprint",
        "rendered_plan_reference",
        "rendered_plan_identity",
        "rendered_plan_fingerprint",
        "execution_role",
        "execution_text",
        "ordinal",
    ):
        if getattr(actual, field) != getattr(expected, field):
            issues.append(
                _issue(
                    f"llm-execution-message-{field.replace('_', '-')}-mismatch",
                    actual.execution_message_reference,
                    field=field,
                )
            )
    return issues


def _completeness(actual, expected, reference, kind):
    issues = []
    actual_counter = Counter(actual)
    expected_counter = Counter(expected)
    for value in sorted((expected_counter - actual_counter).elements()):
        issues.append(
            _issue(
                f"llm-execution-missing-{kind}",
                reference,
                related=(value,),
            )
        )
    for value in sorted((actual_counter - expected_counter).elements()):
        issues.append(
            _issue(
                f"llm-execution-extra-{kind}",
                reference,
                related=(value,),
            )
        )
    return issues


def _seal_issues(plan):
    issues = []
    if plan.identity != derive_draft_llm_execution_plan_identity(plan):
        issues.append(
            _issue("llm-execution-invalid-plan-identity", plan.execution_plan_reference)
        )
    if plan.fingerprint != derive_draft_llm_execution_plan_fingerprint(plan):
        issues.append(
            _issue(
                "llm-execution-invalid-plan-fingerprint", plan.execution_plan_reference
            )
        )
    for request in plan.execution_requests:
        if request.identity != derive_llm_execution_request_identity(request):
            issues.append(
                _issue(
                    "llm-execution-invalid-request-identity",
                    request.execution_request_reference,
                )
            )
        if request.fingerprint != derive_llm_execution_request_fingerprint(request):
            issues.append(
                _issue(
                    "llm-execution-invalid-request-fingerprint",
                    request.execution_request_reference,
                )
            )
        for message in request.execution_messages:
            if message.identity != derive_llm_execution_message_identity(message):
                issues.append(
                    _issue(
                        "llm-execution-invalid-message-identity",
                        message.execution_message_reference,
                    )
                )
            if message.fingerprint != derive_llm_execution_message_fingerprint(message):
                issues.append(
                    _issue(
                        "llm-execution-invalid-message-fingerprint",
                        message.execution_message_reference,
                    )
                )
    return issues


def _duplicate_issues(plan):
    issues = []
    request_dimensions = (
        ("execution_request_reference", "execution-request-reference"),
        ("identity", "execution-request-identity"),
        ("rendered_section_reference", "rendered-section-reference"),
        ("rendered_section_identity", "rendered-section-identity"),
        ("request_ordinal", "request-ordinal"),
    )
    for field, code in request_dimensions:
        issues.extend(
            _duplicates(
                plan.execution_requests,
                field,
                f"llm-execution-duplicate-{code}",
                plan.execution_plan_reference,
            )
        )
    for request in plan.execution_requests:
        message_dimensions = (
            ("execution_message_reference", "execution-message-reference"),
            ("identity", "execution-message-identity"),
            ("rendered_message_reference", "rendered-message-reference"),
            ("rendered_message_identity", "rendered-message-identity"),
            ("ordinal", "message-ordinal"),
        )
        for field, code in message_dimensions:
            issues.extend(
                _duplicates(
                    request.execution_messages,
                    field,
                    f"llm-execution-duplicate-{code}",
                    request.execution_request_reference,
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


def _reconstruct_builder_inputs(rendered_plan, validation_context):
    try:
        source = DraftRenderedPromptPlan.model_validate(
            rendered_plan.model_dump(mode="python", warnings=False)
        )
        context = LLMExecutionValidationContext.model_validate(
            validation_context.model_dump(mode="python", warnings=False)
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
            (_issue("llm-execution-invalid-builder-input", _ARTIFACT_FALLBACK),),
        )
    return source, context, ()


def _reconstruct(execution_plan, validation_context):
    try:
        plan = DraftLLMExecutionPlan.model_validate(
            execution_plan.model_dump(mode="python", warnings=False)
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
            (_issue("llm-execution-invalid-reconstructed-plan", _PLAN_FALLBACK),),
        )
    try:
        context = LLMExecutionValidationContext.model_validate(
            validation_context.model_dump(mode="python", warnings=False)
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
            (_issue("llm-execution-invalid-reconstructed-context", _PLAN_FALLBACK),),
        )
    return _Reconstruction(plan, context, ())


def _safe_reference(value, fallback):
    if not isinstance(value, str):
        return fallback
    normalized = unicodedata.normalize("NFC", value)
    lowered = normalized.casefold()
    unsafe_words = ("traceback", "exception", "error", "password", "secret", "token")
    if (
        not normalized
        or len(normalized) > _MAX_REFERENCE_LENGTH
        or any(word in lowered for word in unsafe_words)
        or re.search(r"0x[0-9a-fA-F]+", normalized)
        or re.search(r"[\\/]", normalized)
        or re.search(r"[?&#=\s\x00-\x1f\x7f]", normalized)
        or not normalized.isascii()
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", normalized) is None
    ):
        return fallback
    return normalized


def _issue(code, reference, *, field=None, related=()):
    return DomainValidationIssue(
        code=code,
        artifact_reference=_safe_reference(reference, _ARTIFACT_FALLBACK),
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


__all__ = ("build_draft_llm_execution_plan", "validate_draft_llm_execution_plan")

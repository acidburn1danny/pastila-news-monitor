"""Construction and authoritative validation for Phase 5.2 prompt renderings."""

import re
import unicodedata
from dataclasses import dataclass

from pydantic import ValidationError

from .errors import DomainValidationError, DomainValidationIssue
from .llm_request_models import DraftLLMRequestPlan, LLMRequestValidationContext
from .llm_request_validation import validate_draft_llm_request_plan
from .prompt_rendering_identity import (
    derive_draft_rendered_prompt_plan_fingerprint,
    derive_draft_rendered_prompt_plan_identity,
    derive_rendered_prompt_message_fingerprint,
    derive_rendered_prompt_message_identity,
    derive_rendered_prompt_section_fingerprint,
    derive_rendered_prompt_section_identity,
)
from .prompt_rendering_models import (
    DraftRenderedPromptPlan,
    RenderedPromptMessage,
    RenderedPromptSection,
    RenderedPromptValidationContext,
)

_ZERO = "0" * 64
_ARTIFACT_FALLBACK = "rendered-prompt-artifact"
_PLAN_FALLBACK = "draft-rendered-prompt-plan"
_RELATED_FALLBACK = "unsafe-related-reference"
_MAX_REFERENCE_LENGTH = 200
_MESSAGE_OPEN = "<request-claim>"
_MESSAGE_CLOSE = "</request-claim>"
_RENDERING_ROLE = "generation"


@dataclass(frozen=True, slots=True)
class _AuthoritativeRenderedPromptInputs:
    plan: DraftRenderedPromptPlan | None
    context: RenderedPromptValidationContext | None
    issues: tuple[DomainValidationIssue, ...]


def _canonical_rendered_plan_reference(source_plan) -> str:
    return f"rendered-prompt-plan:{source_plan.identity}"


def _canonical_rendered_section_reference(source_section) -> str:
    return f"rendered-prompt-section:{source_section.identity}"


def _canonical_rendered_message_reference(source_claim) -> str:
    return f"rendered-prompt-message:{source_claim.identity}"


def _render_request_claim(source_claim) -> str:
    """Render one request claim using the sole canonical Phase 5.2 format."""

    return "\n".join(
        (
            _MESSAGE_OPEN,
            f"claim-reference: {source_claim.claim_reference}",
            f"requirement: {source_claim.requirement}",
            f"role: {source_claim.role}",
            f"ordinal: {source_claim.ordinal}",
            _MESSAGE_CLOSE,
        )
    )


def build_draft_rendered_prompt_plan(
    request_plan: DraftLLMRequestPlan,
    request_context: LLMRequestValidationContext,
) -> DraftRenderedPromptPlan:
    """Build one deterministic prompt rendering from valid Phase 5.1 state."""

    source_plan, source_context, issues = _reconstruct_upstream(
        request_plan, request_context
    )
    if issues:
        raise DomainValidationError(issues)
    assert source_plan is not None and source_context is not None
    if upstream_issues := validate_draft_llm_request_plan(source_plan, source_context):
        raise DomainValidationError(upstream_issues)
    sections = tuple(
        _build_rendered_section(source_plan, section)
        for section in source_plan.request_sections
    )
    value = DraftRenderedPromptPlan(
        identity=f"scout:draft-rendered-prompt-plan:{_ZERO}",
        fingerprint=_ZERO,
        rendered_plan_reference=_canonical_rendered_plan_reference(source_plan),
        source_request_plan_reference=source_plan.request_plan_reference,
        source_request_plan_identity=source_plan.identity,
        source_request_plan_fingerprint=source_plan.fingerprint,
        draft_reference=source_plan.draft_reference,
        draft_fingerprint=source_plan.draft_fingerprint,
        normalized_input_reference=source_plan.normalized_input_reference,
        rendered_sections=sections,
    )
    return _seal(
        value,
        derive_draft_rendered_prompt_plan_identity,
        derive_draft_rendered_prompt_plan_fingerprint,
    )


def _build_rendered_section(source_plan, source_section):
    messages = tuple(
        _build_rendered_message(source_plan, source_section, claim)
        for claim in source_section.request_claims
    )
    value = RenderedPromptSection(
        identity=f"scout:rendered-prompt-section:{_ZERO}",
        fingerprint=_ZERO,
        rendered_section_reference=_canonical_rendered_section_reference(
            source_section
        ),
        source_request_section_reference=source_section.request_section_reference,
        source_request_section_identity=source_section.identity,
        source_request_section_fingerprint=source_section.fingerprint,
        source_request_plan_reference=source_plan.request_plan_reference,
        source_request_plan_identity=source_plan.identity,
        source_request_plan_fingerprint=source_plan.fingerprint,
        draft_reference=source_plan.draft_reference,
        rendered_messages=messages,
    )
    return _seal(
        value,
        derive_rendered_prompt_section_identity,
        derive_rendered_prompt_section_fingerprint,
    )


def _build_rendered_message(source_plan, source_section, source_claim):
    value = RenderedPromptMessage(
        identity=f"scout:rendered-prompt-message:{_ZERO}",
        fingerprint=_ZERO,
        rendered_message_reference=_canonical_rendered_message_reference(source_claim),
        source_request_claim_reference=source_claim.request_claim_reference,
        source_request_claim_identity=source_claim.identity,
        source_request_claim_fingerprint=source_claim.fingerprint,
        source_request_section_reference=source_section.request_section_reference,
        source_request_section_identity=source_section.identity,
        source_request_section_fingerprint=source_section.fingerprint,
        source_request_plan_reference=source_plan.request_plan_reference,
        source_request_plan_identity=source_plan.identity,
        source_request_plan_fingerprint=source_plan.fingerprint,
        rendering_role=_RENDERING_ROLE,
        rendered_text=_render_request_claim(source_claim),
        ordinal=source_claim.ordinal,
    )
    return _seal(
        value,
        derive_rendered_prompt_message_identity,
        derive_rendered_prompt_message_fingerprint,
    )


def _seal(value, identity_function, fingerprint_function):
    value = value.model_copy(update={"identity": identity_function(value)})
    return value.model_copy(update={"fingerprint": fingerprint_function(value)})


def validate_draft_rendered_prompt_plan(
    plan: DraftRenderedPromptPlan,
    context: RenderedPromptValidationContext,
) -> tuple[DomainValidationIssue, ...]:
    """Validate one rendering against fresh authoritative Phase 5.1 state."""

    reconstructed = _reconstruct_for_validation(plan, context)
    if reconstructed.issues:
        return reconstructed.issues
    validated_plan = reconstructed.plan
    validated_context = reconstructed.context
    assert validated_plan is not None and validated_context is not None
    issues: list[DomainValidationIssue] = []
    _validate_seals(validated_plan, issues)
    _validate_plan_duplicates(validated_plan, issues)
    source = next(
        (
            item
            for item in validated_context.request_plans
            if item.request_plan_reference
            == validated_plan.source_request_plan_reference
        ),
        None,
    )
    if source is None:
        issues.append(_issue("prompt-rendering-unknown-source-plan", validated_plan))
        return _ordered(issues)
    if upstream := validate_draft_llm_request_plan(
        source, validated_context.llm_request_validation_context
    ):
        issues.append(
            _issue(
                "prompt-rendering-invalid-source-plan",
                validated_plan,
                related=tuple(item.code for item in upstream),
            )
        )
        return _ordered(issues)
    _compare(
        validated_plan,
        (
            (
                "rendered_plan_reference",
                _canonical_rendered_plan_reference(source),
                "prompt-rendering-invalid-plan-reference",
            ),
            (
                "source_request_plan_identity",
                source.identity,
                "prompt-rendering-source-plan-identity-mismatch",
            ),
            (
                "source_request_plan_fingerprint",
                source.fingerprint,
                "prompt-rendering-source-plan-fingerprint-mismatch",
            ),
            (
                "draft_reference",
                source.draft_reference,
                "prompt-rendering-draft-reference-mismatch",
            ),
            (
                "draft_fingerprint",
                source.draft_fingerprint,
                "prompt-rendering-draft-fingerprint-mismatch",
            ),
            (
                "normalized_input_reference",
                source.normalized_input_reference,
                "prompt-rendering-input-reference-mismatch",
            ),
        ),
        issues,
    )
    _validate_sections(validated_plan, source, issues)
    return _ordered(issues)


def _validate_sections(plan, source_plan, issues):
    actual, expected = plan.rendered_sections, source_plan.request_sections
    _validate_count(plan, "section", actual, expected, issues)
    if len(actual) == len(expected) and tuple(
        item.source_request_section_identity for item in actual
    ) != tuple(item.identity for item in expected):
        issues.append(_issue("prompt-rendering-invalid-section-order", plan))
    expected_by_identity = {item.identity: item for item in expected}
    for index, section in enumerate(actual):
        source = expected_by_identity.get(section.source_request_section_identity)
        if source is None:
            issues.append(_issue("prompt-rendering-source-section-mismatch", section))
            continue
        _validate_section(section, source, source_plan, index, issues)


def _validate_section(section, source, source_plan, section_index, issues):
    _compare(
        section,
        (
            (
                "rendered_section_reference",
                _canonical_rendered_section_reference(source),
                "prompt-rendering-invalid-section-reference",
            ),
            (
                "source_request_section_reference",
                source.request_section_reference,
                "prompt-rendering-source-section-reference-mismatch",
            ),
            (
                "source_request_section_fingerprint",
                source.fingerprint,
                "prompt-rendering-source-section-fingerprint-mismatch",
            ),
            (
                "source_request_plan_reference",
                source_plan.request_plan_reference,
                "prompt-rendering-section-source-plan-reference-mismatch",
            ),
            (
                "source_request_plan_identity",
                source_plan.identity,
                "prompt-rendering-section-source-plan-identity-mismatch",
            ),
            (
                "source_request_plan_fingerprint",
                source_plan.fingerprint,
                "prompt-rendering-section-source-plan-fingerprint-mismatch",
            ),
            (
                "draft_reference",
                source_plan.draft_reference,
                "prompt-rendering-section-draft-reference-mismatch",
            ),
        ),
        issues,
    )
    _validate_message_duplicates(section, issues)
    actual, expected = section.rendered_messages, source.request_claims
    _validate_count(section, "message", actual, expected, issues)
    if len(actual) == len(expected) and tuple(
        item.source_request_claim_identity for item in actual
    ) != tuple(item.identity for item in expected):
        issues.append(_issue("prompt-rendering-invalid-message-order", section))
    expected_by_identity = {item.identity: item for item in expected}
    for message in actual:
        source_claim = expected_by_identity.get(message.source_request_claim_identity)
        if source_claim is None:
            issues.append(_issue("prompt-rendering-source-claim-mismatch", message))
            continue
        _validate_message(message, source_claim, source, source_plan, issues)


def _validate_message(message, source, source_section, source_plan, issues):
    _compare(
        message,
        (
            (
                "rendered_message_reference",
                _canonical_rendered_message_reference(source),
                "prompt-rendering-invalid-message-reference",
            ),
            (
                "source_request_claim_reference",
                source.request_claim_reference,
                "prompt-rendering-source-claim-reference-mismatch",
            ),
            (
                "source_request_claim_fingerprint",
                source.fingerprint,
                "prompt-rendering-source-claim-fingerprint-mismatch",
            ),
            (
                "source_request_section_reference",
                source_section.request_section_reference,
                "prompt-rendering-message-source-section-reference-mismatch",
            ),
            (
                "source_request_section_identity",
                source_section.identity,
                "prompt-rendering-message-source-section-identity-mismatch",
            ),
            (
                "source_request_section_fingerprint",
                source_section.fingerprint,
                "prompt-rendering-message-source-section-fingerprint-mismatch",
            ),
            (
                "source_request_plan_reference",
                source_plan.request_plan_reference,
                "prompt-rendering-message-source-plan-reference-mismatch",
            ),
            (
                "source_request_plan_identity",
                source_plan.identity,
                "prompt-rendering-message-source-plan-identity-mismatch",
            ),
            (
                "source_request_plan_fingerprint",
                source_plan.fingerprint,
                "prompt-rendering-message-source-plan-fingerprint-mismatch",
            ),
            ("rendering_role", _RENDERING_ROLE, "prompt-rendering-role-mismatch"),
            (
                "rendered_text",
                _render_request_claim(source),
                "prompt-rendering-text-mismatch",
            ),
            ("ordinal", source.ordinal, "prompt-rendering-ordinal-mismatch"),
        ),
        issues,
    )


def _validate_count(artifact, kind, actual, expected, issues):
    if len(actual) < len(expected):
        issues.append(_issue(f"prompt-rendering-missing-{kind}", artifact))
    elif len(actual) > len(expected):
        issues.append(_issue(f"prompt-rendering-extra-{kind}", artifact))


def _validate_seals(plan, issues):
    artifacts = (
        (
            plan,
            derive_draft_rendered_prompt_plan_identity,
            derive_draft_rendered_prompt_plan_fingerprint,
            "plan",
        ),
        *(
            (
                section,
                derive_rendered_prompt_section_identity,
                derive_rendered_prompt_section_fingerprint,
                "section",
            )
            for section in plan.rendered_sections
        ),
        *(
            (
                message,
                derive_rendered_prompt_message_identity,
                derive_rendered_prompt_message_fingerprint,
                "message",
            )
            for section in plan.rendered_sections
            for message in section.rendered_messages
        ),
    )
    for artifact, identity_function, fingerprint_function, kind in artifacts:
        if artifact.identity != identity_function(artifact):
            issues.append(_issue(f"prompt-rendering-invalid-{kind}-identity", artifact))
        if artifact.fingerprint != fingerprint_function(artifact):
            issues.append(
                _issue(f"prompt-rendering-invalid-{kind}-fingerprint", artifact)
            )


def _validate_plan_duplicates(plan, issues):
    for field, code in (
        ("rendered_section_reference", "duplicate-rendered-section-reference"),
        ("identity", "duplicate-rendered-section-identity"),
        ("source_request_section_reference", "duplicate-source-section-reference"),
        ("source_request_section_identity", "duplicate-source-section-identity"),
    ):
        if duplicates := _duplicates(
            getattr(item, field) for item in plan.rendered_sections
        ):
            issues.append(_issue(f"prompt-rendering-{code}", plan, related=duplicates))


def _validate_message_duplicates(section, issues):
    for field, code in (
        ("rendered_message_reference", "duplicate-rendered-message-reference"),
        ("identity", "duplicate-rendered-message-identity"),
        ("source_request_claim_reference", "duplicate-source-claim-reference"),
        ("source_request_claim_identity", "duplicate-source-claim-identity"),
        ("ordinal", "duplicate-ordinal"),
    ):
        if duplicates := _duplicates(
            getattr(item, field) for item in section.rendered_messages
        ):
            issues.append(
                _issue(f"prompt-rendering-{code}", section, related=duplicates)
            )
    if tuple(item.ordinal for item in section.rendered_messages) != tuple(
        range(len(section.rendered_messages))
    ):
        issues.append(_issue("prompt-rendering-invalid-ordinal-sequence", section))


def _compare(artifact, comparisons, issues):
    for field, expected, code in comparisons:
        if getattr(artifact, field) != expected:
            issues.append(_issue(code, artifact, (field,)))


def _reconstruct_upstream(raw_plan, raw_context):
    issues: list[DomainValidationIssue] = []
    plan = context = None
    try:
        plan = DraftLLMRequestPlan.model_validate(
            raw_plan.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(
                error, raw_plan, "prompt-rendering-invalid-source-plan"
            )
        )
    try:
        context = LLMRequestValidationContext.model_validate(
            raw_context.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(
                error, raw_context, "prompt-rendering-invalid-source-context"
            )
        )
    return plan, context, _ordered(issues)


def _reconstruct_for_validation(raw_plan, raw_context):
    issues: list[DomainValidationIssue] = []
    plan = context = None
    try:
        plan = DraftRenderedPromptPlan.model_validate(
            raw_plan.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(
                error, raw_plan, "prompt-rendering-invalid-reconstructed-plan"
            )
        )
    try:
        context = RenderedPromptValidationContext.model_validate(
            raw_context.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(
                error, raw_context, "prompt-rendering-invalid-reconstructed-context"
            )
        )
    return _AuthoritativeRenderedPromptInputs(plan, context, _ordered(issues))


def _validation_error_issues(error, artifact, fallback):
    details = error.errors() if isinstance(error, ValidationError) else ({"loc": ()},)
    return tuple(
        _issue(
            (
                str(item.get("type"))
                if str(item.get("type", "")).startswith("prompt-rendering-")
                else fallback
            ),
            _safe_artifact_reference(artifact, fallback),
            _safe_error_location(item.get("loc", ())),
        )
        for item in details
    )


def _issue(code, artifact, path=(), related=()):
    reference = (
        _safe_reference(artifact, _ARTIFACT_FALLBACK)
        if isinstance(artifact, str)
        else _safe_artifact_reference(artifact, _ARTIFACT_FALLBACK)
    )
    return DomainValidationIssue(
        code=code,
        artifact_reference=reference,
        artifact_type=type(artifact).__name__,
        field_reference=".".join(map(str, path)) or None,
        field_path=path,
        related_references=tuple(
            sorted(_safe_reference(item, _RELATED_FALLBACK) for item in related)
        ),
        message_key=code,
    )


def _safe_artifact_reference(artifact, fallback):
    for name in (
        "rendered_plan_reference",
        "rendered_section_reference",
        "rendered_message_reference",
    ):
        try:
            value = getattr(artifact, name, None)
        except Exception:  # noqa: BLE001
            return fallback
        if value is not None:
            return _safe_reference(value, fallback)
    return fallback


def _safe_reference(value, fallback):
    if not isinstance(value, str):
        return fallback
    normalized = unicodedata.normalize("NFC", value)
    lowered = normalized.casefold()
    if (
        not normalized
        or len(normalized) > _MAX_REFERENCE_LENGTH
        or not normalized.isascii()
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", normalized)
        or re.search(r"(?:^|[^A-Za-z0-9])0x[0-9a-f]+", lowered)
        or any(token in lowered for token in ("traceback", "exception", "error"))
    ):
        return fallback
    return normalized


def _safe_error_location(value):
    try:
        items = tuple(value)
    except TypeError:
        return ()
    result: list[str | int] = []
    for item in items:
        if isinstance(item, int) and not isinstance(item, bool):
            result.append(item)
        elif isinstance(item, str):
            token = unicodedata.normalize("NFC", item)
            result.append(
                token
                if token
                and len(token) <= _MAX_REFERENCE_LENGTH
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", token)
                else "invalid-field"
            )
        else:
            result.append("invalid-field")
    return tuple(result)


def _duplicates(values):
    seen, duplicates = set(), set()
    for value in values:
        normalized = str(value)
        if normalized in seen:
            duplicates.add(normalized)
        seen.add(normalized)
    return tuple(sorted(duplicates))


def _ordered(issues):
    return tuple(
        sorted(
            issues,
            key=lambda item: (
                item.code,
                item.artifact_reference,
                tuple(map(str, item.field_path)),
                item.related_references,
            ),
        )
    )


__all__ = ("build_draft_rendered_prompt_plan", "validate_draft_rendered_prompt_plan")

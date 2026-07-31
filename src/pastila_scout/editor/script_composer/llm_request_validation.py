"""Construction and authoritative validation for Phase 5.1 semantic requests."""

import re
import unicodedata
from dataclasses import dataclass

from pydantic import ValidationError

from .errors import DomainValidationError, DomainValidationIssue
from .llm_request_identity import (
    derive_draft_llm_request_plan_fingerprint,
    derive_draft_llm_request_plan_identity,
    derive_llm_request_claim_fingerprint,
    derive_llm_request_claim_identity,
    derive_llm_request_section_fingerprint,
    derive_llm_request_section_identity,
)
from .llm_request_models import (
    DraftLLMRequestPlan,
    LLMRequestClaim,
    LLMRequestSection,
    LLMRequestValidationContext,
)
from .section_composition_models import (
    DraftSectionCompositionPlan,
    SectionCompositionValidationContext,
)
from .section_composition_validation import (
    validate_draft_section_composition_plan,
)

_ZERO = "0" * 64
_PLAN_FALLBACK = "draft-llm-request-plan"
_ARTIFACT_FALLBACK = "llm-request-artifact"
_MAX_REFERENCE_LENGTH = 200


@dataclass(frozen=True, slots=True)
class _AuthoritativeLLMRequestInputs:
    plan: DraftLLMRequestPlan | None
    context: LLMRequestValidationContext | None
    issues: tuple[DomainValidationIssue, ...]


def _canonical_llm_request_plan_reference(source_plan) -> str:
    return f"llm-request-plan:{source_plan.identity}"


def _canonical_llm_request_section_reference(source_section) -> str:
    return f"llm-request-section:{source_section.identity}"


def _canonical_llm_request_claim_reference(source_claim) -> str:
    return f"llm-request-claim:{source_claim.identity}"


def build_draft_llm_request_plan(
    composition_plan: DraftSectionCompositionPlan,
    composition_context: SectionCompositionValidationContext,
) -> DraftLLMRequestPlan:
    """Build a self-contained semantic request from valid Phase 4.3 state."""

    source_plan, source_context, issues = _reconstruct_upstream(
        composition_plan, composition_context
    )
    if issues:
        raise DomainValidationError(issues)
    assert source_plan is not None and source_context is not None
    if upstream_issues := validate_draft_section_composition_plan(
        source_plan, source_context
    ):
        raise DomainValidationError(upstream_issues)
    sections = tuple(
        _build_request_section(source_plan, section)
        for section in source_plan.composed_sections
    )
    value = DraftLLMRequestPlan(
        identity=f"scout:draft-llm-request-plan:{_ZERO}",
        fingerprint=_ZERO,
        request_plan_reference=_canonical_llm_request_plan_reference(source_plan),
        source_composition_plan_reference=source_plan.composition_plan_reference,
        source_composition_plan_identity=source_plan.identity,
        source_composition_plan_fingerprint=source_plan.fingerprint,
        draft_reference=source_plan.draft_reference,
        draft_fingerprint=source_plan.draft_fingerprint,
        normalized_input_reference=source_plan.normalized_input_reference,
        request_sections=sections,
    )
    return _seal(
        value,
        derive_draft_llm_request_plan_identity,
        derive_draft_llm_request_plan_fingerprint,
    )


def _build_request_section(source_plan, source_section):
    claims = tuple(
        _build_request_claim(source_plan, source_section, source_claim)
        for source_claim in source_section.composed_claims
    )
    value = LLMRequestSection(
        identity=f"scout:llm-request-section:{_ZERO}",
        fingerprint=_ZERO,
        request_section_reference=_canonical_llm_request_section_reference(
            source_section
        ),
        source_composed_section_reference=source_section.composed_section_reference,
        source_composed_section_identity=source_section.identity,
        source_composed_section_fingerprint=source_section.fingerprint,
        source_composition_plan_reference=source_plan.composition_plan_reference,
        source_composition_plan_identity=source_plan.identity,
        source_composition_plan_fingerprint=source_plan.fingerprint,
        draft_reference=source_plan.draft_reference,
        normalized_input_reference=source_plan.normalized_input_reference,
        section_reference=source_section.section_reference,
        request_claims=claims,
    )
    return _seal(
        value,
        derive_llm_request_section_identity,
        derive_llm_request_section_fingerprint,
    )


def _build_request_claim(source_plan, source_section, source_claim):
    value = LLMRequestClaim(
        identity=f"scout:llm-request-claim:{_ZERO}",
        fingerprint=_ZERO,
        request_claim_reference=_canonical_llm_request_claim_reference(source_claim),
        source_composed_claim_reference=source_claim.composed_claim_reference,
        source_composed_claim_identity=source_claim.identity,
        source_composed_claim_fingerprint=source_claim.fingerprint,
        source_composed_section_reference=source_section.composed_section_reference,
        source_composed_section_identity=source_section.identity,
        source_composed_section_fingerprint=source_section.fingerprint,
        source_composition_plan_reference=source_plan.composition_plan_reference,
        source_composition_plan_identity=source_plan.identity,
        source_composition_plan_fingerprint=source_plan.fingerprint,
        draft_reference=source_plan.draft_reference,
        normalized_input_reference=source_plan.normalized_input_reference,
        section_reference=source_claim.section_reference,
        claim_reference=source_claim.claim_reference,
        requirement=str(source_claim.requirement),
        role=str(source_claim.role),
        ordinal=source_claim.ordinal,
    )
    return _seal(
        value,
        derive_llm_request_claim_identity,
        derive_llm_request_claim_fingerprint,
    )


def _seal(value, identity_function, fingerprint_function):
    value = value.model_copy(update={"identity": identity_function(value)})
    return value.model_copy(update={"fingerprint": fingerprint_function(value)})


def validate_draft_llm_request_plan(
    plan: DraftLLMRequestPlan,
    context: LLMRequestValidationContext,
) -> tuple[DomainValidationIssue, ...]:
    """Validate one request plan against fresh authoritative Phase 4.3 state."""

    reconstructed = _reconstruct_for_validation(plan, context)
    if reconstructed.issues:
        return reconstructed.issues
    validated_plan = reconstructed.plan
    validated_context = reconstructed.context
    assert validated_plan is not None and validated_context is not None
    issues: list[DomainValidationIssue] = []
    _validate_seals(validated_plan, issues)
    _validate_plan_duplicates(validated_plan, issues)
    source_plan = next(
        (
            candidate
            for candidate in validated_context.composition_plans
            if candidate.composition_plan_reference
            == validated_plan.source_composition_plan_reference
        ),
        None,
    )
    if source_plan is None:
        issues.append(
            _issue(
                "llm-request-unknown-source-composition-plan",
                validated_plan,
                ("source_composition_plan_reference",),
            )
        )
        return _ordered(issues)
    if upstream_issues := validate_draft_section_composition_plan(
        source_plan,
        validated_context.section_composition_validation_context,
    ):
        issues.append(
            _issue(
                "llm-request-invalid-source-composition-plan",
                validated_plan,
                related=tuple(item.code for item in upstream_issues),
            )
        )
        return _ordered(issues)
    _validate_plan_lineage(validated_plan, source_plan, issues)
    _validate_sections(validated_plan, source_plan, issues)
    return _ordered(issues)


def _validate_plan_lineage(plan, source, issues):
    comparisons = (
        (
            "request_plan_reference",
            _canonical_llm_request_plan_reference(source),
            "llm-request-invalid-request-plan-reference",
        ),
        (
            "source_composition_plan_identity",
            source.identity,
            "llm-request-source-plan-identity-mismatch",
        ),
        (
            "source_composition_plan_fingerprint",
            source.fingerprint,
            "llm-request-source-plan-fingerprint-mismatch",
        ),
        (
            "draft_reference",
            source.draft_reference,
            "llm-request-draft-reference-mismatch",
        ),
        (
            "draft_fingerprint",
            source.draft_fingerprint,
            "llm-request-draft-fingerprint-mismatch",
        ),
        (
            "normalized_input_reference",
            source.normalized_input_reference,
            "llm-request-normalized-input-mismatch",
        ),
    )
    _compare(plan, comparisons, issues)


def _validate_sections(plan, source_plan, issues):
    actual, expected = plan.request_sections, source_plan.composed_sections
    _validate_count(plan, "section", actual, expected, issues)
    actual_order = tuple(item.source_composed_section_identity for item in actual)
    expected_order = tuple(item.identity for item in expected)
    if len(actual) == len(expected) and actual_order != expected_order:
        issues.append(
            _issue("llm-request-invalid-section-order", plan, ("request_sections",))
        )
    expected_by_identity = {item.identity: item for item in expected}
    for index, section in enumerate(actual):
        source = expected_by_identity.get(section.source_composed_section_identity)
        if source is None:
            issues.append(
                _issue(
                    "llm-request-source-section-mismatch",
                    section,
                    ("request_sections", index),
                )
            )
            continue
        _validate_section(section, source, source_plan, index, issues)


def _validate_section(section, source, source_plan, section_index, issues):
    comparisons = (
        (
            "request_section_reference",
            _canonical_llm_request_section_reference(source),
            "llm-request-invalid-request-section-reference",
        ),
        (
            "source_composed_section_reference",
            source.composed_section_reference,
            "llm-request-source-section-reference-mismatch",
        ),
        (
            "source_composed_section_fingerprint",
            source.fingerprint,
            "llm-request-source-section-fingerprint-mismatch",
        ),
        (
            "source_composition_plan_reference",
            source_plan.composition_plan_reference,
            "llm-request-section-source-plan-reference-mismatch",
        ),
        (
            "source_composition_plan_identity",
            source_plan.identity,
            "llm-request-section-source-plan-identity-mismatch",
        ),
        (
            "source_composition_plan_fingerprint",
            source_plan.fingerprint,
            "llm-request-section-source-plan-fingerprint-mismatch",
        ),
        (
            "draft_reference",
            source_plan.draft_reference,
            "llm-request-section-draft-mismatch",
        ),
        (
            "normalized_input_reference",
            source_plan.normalized_input_reference,
            "llm-request-section-input-mismatch",
        ),
        (
            "section_reference",
            source.section_reference,
            "llm-request-section-reference-mismatch",
        ),
    )
    _compare(section, comparisons, issues)
    _validate_claim_duplicates(section, issues)
    _validate_claims(section, source, source_plan, section_index, issues)


def _validate_claims(section, source_section, source_plan, section_index, issues):
    actual, expected = section.request_claims, source_section.composed_claims
    _validate_count(section, "claim", actual, expected, issues)
    actual_order = tuple(item.source_composed_claim_identity for item in actual)
    expected_order = tuple(item.identity for item in expected)
    if len(actual) == len(expected) and actual_order != expected_order:
        issues.append(
            _issue("llm-request-invalid-claim-order", section, ("request_claims",))
        )
    expected_by_identity = {item.identity: item for item in expected}
    for index, claim in enumerate(actual):
        source = expected_by_identity.get(claim.source_composed_claim_identity)
        path = ("request_sections", section_index, "request_claims", index)
        if source is None:
            issues.append(_issue("llm-request-source-claim-mismatch", claim, path))
            continue
        _validate_claim(claim, source, source_section, source_plan, path, issues)


def _validate_claim(claim, source, source_section, source_plan, path, issues):
    comparisons = (
        (
            "request_claim_reference",
            _canonical_llm_request_claim_reference(source),
            "llm-request-invalid-request-claim-reference",
        ),
        (
            "source_composed_claim_reference",
            source.composed_claim_reference,
            "llm-request-source-claim-reference-mismatch",
        ),
        (
            "source_composed_claim_fingerprint",
            source.fingerprint,
            "llm-request-source-claim-fingerprint-mismatch",
        ),
        (
            "source_composed_section_reference",
            source_section.composed_section_reference,
            "llm-request-claim-source-section-reference-mismatch",
        ),
        (
            "source_composed_section_identity",
            source_section.identity,
            "llm-request-claim-source-section-identity-mismatch",
        ),
        (
            "source_composed_section_fingerprint",
            source_section.fingerprint,
            "llm-request-claim-source-section-fingerprint-mismatch",
        ),
        (
            "source_composition_plan_reference",
            source_plan.composition_plan_reference,
            "llm-request-claim-source-plan-reference-mismatch",
        ),
        (
            "source_composition_plan_identity",
            source_plan.identity,
            "llm-request-claim-source-plan-identity-mismatch",
        ),
        (
            "source_composition_plan_fingerprint",
            source_plan.fingerprint,
            "llm-request-claim-source-plan-fingerprint-mismatch",
        ),
        (
            "draft_reference",
            source_plan.draft_reference,
            "llm-request-claim-draft-mismatch",
        ),
        (
            "normalized_input_reference",
            source_plan.normalized_input_reference,
            "llm-request-claim-input-mismatch",
        ),
        (
            "section_reference",
            source.section_reference,
            "llm-request-claim-section-mismatch",
        ),
        (
            "claim_reference",
            source.claim_reference,
            "llm-request-semantic-claim-reference-mismatch",
        ),
        ("requirement", str(source.requirement), "llm-request-requirement-mismatch"),
        ("role", str(source.role), "llm-request-role-mismatch"),
        ("ordinal", source.ordinal, "llm-request-ordinal-mismatch"),
    )
    _compare(claim, comparisons, issues, path)


def _compare(artifact, comparisons, issues, path=()):
    for field, expected, code in comparisons:
        if getattr(artifact, field) != expected:
            issues.append(_issue(code, artifact, (*path, field)))


def _validate_count(artifact, kind, actual, expected, issues):
    if len(actual) < len(expected):
        issues.append(_issue(f"llm-request-missing-{kind}", artifact))
    elif len(actual) > len(expected):
        issues.append(_issue(f"llm-request-extra-{kind}", artifact))


def _validate_seals(plan, issues):
    artifacts = (
        (
            plan,
            derive_draft_llm_request_plan_identity,
            derive_draft_llm_request_plan_fingerprint,
            "plan",
        ),
        *(
            (
                section,
                derive_llm_request_section_identity,
                derive_llm_request_section_fingerprint,
                "section",
            )
            for section in plan.request_sections
        ),
        *(
            (
                claim,
                derive_llm_request_claim_identity,
                derive_llm_request_claim_fingerprint,
                "claim",
            )
            for section in plan.request_sections
            for claim in section.request_claims
        ),
    )
    for artifact, identity_function, fingerprint_function, kind in artifacts:
        if artifact.identity != identity_function(artifact):
            issues.append(_issue(f"llm-request-invalid-{kind}-identity", artifact))
        if artifact.fingerprint != fingerprint_function(artifact):
            issues.append(_issue(f"llm-request-invalid-{kind}-fingerprint", artifact))


def _validate_plan_duplicates(plan, issues):
    for field, code in (
        ("request_section_reference", "duplicate-request-section-reference"),
        ("identity", "duplicate-request-section-identity"),
        ("source_composed_section_reference", "duplicate-source-section-reference"),
        ("source_composed_section_identity", "duplicate-source-section-identity"),
        ("section_reference", "duplicate-section-reference"),
    ):
        if duplicates := _duplicates(
            getattr(item, field) for item in plan.request_sections
        ):
            issues.append(_issue(f"llm-request-{code}", plan, related=duplicates))


def _validate_claim_duplicates(section, issues):
    for field, code in (
        ("request_claim_reference", "duplicate-request-claim-reference"),
        ("identity", "duplicate-request-claim-identity"),
        ("source_composed_claim_reference", "duplicate-source-claim-reference"),
        ("source_composed_claim_identity", "duplicate-source-claim-identity"),
        ("claim_reference", "duplicate-claim-reference"),
        ("ordinal", "duplicate-ordinal"),
    ):
        if duplicates := _duplicates(
            getattr(item, field) for item in section.request_claims
        ):
            issues.append(_issue(f"llm-request-{code}", section, related=duplicates))
    if tuple(item.ordinal for item in section.request_claims) != tuple(
        range(len(section.request_claims))
    ):
        issues.append(_issue("llm-request-invalid-ordinal-sequence", section))


def _reconstruct_upstream(raw_plan, raw_context):
    issues = []
    plan = context = None
    try:
        plan = DraftSectionCompositionPlan.model_validate(
            raw_plan.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(error, raw_plan, "llm-request-invalid-source-plan")
        )
    try:
        context = SectionCompositionValidationContext.model_validate(
            raw_context.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(
                error, raw_context, "llm-request-invalid-source-context"
            )
        )
    return plan, context, _ordered(issues)


def _reconstruct_for_validation(raw_plan, raw_context):
    issues = []
    plan = context = None
    try:
        plan = DraftLLMRequestPlan.model_validate(
            raw_plan.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(
                error, raw_plan, "llm-request-invalid-reconstructed-plan"
            )
        )
    try:
        context = LLMRequestValidationContext.model_validate(
            raw_context.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(
                error, raw_context, "llm-request-invalid-reconstructed-context"
            )
        )
    return _AuthoritativeLLMRequestInputs(plan, context, _ordered(issues))


def _validation_error_issues(error, artifact, fallback):
    details = error.errors() if isinstance(error, ValidationError) else ({"loc": ()},)
    return tuple(
        _issue(
            (
                str(item.get("type"))
                if str(item.get("type", "")).startswith("llm-request-")
                else fallback
            ),
            _safe_artifact_reference(artifact, fallback),
            _safe_error_location(item.get("loc", ())),
        )
        for item in details
    )


def _issue(code, artifact, path=(), related=()):
    reference = (
        artifact
        if isinstance(artifact, str)
        else _safe_artifact_reference(artifact, _ARTIFACT_FALLBACK)
    )
    return DomainValidationIssue(
        code=code,
        artifact_reference=reference,
        artifact_type=type(artifact).__name__,
        field_reference=".".join(map(str, path)) or None,
        field_path=path,
        related_references=tuple(sorted(str(item) for item in related)),
        message_key=code,
    )


def _safe_artifact_reference(artifact, fallback):
    for name in (
        "request_plan_reference",
        "request_section_reference",
        "request_claim_reference",
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
    value = unicodedata.normalize("NFC", value)
    if (
        not value
        or len(value) > _MAX_REFERENCE_LENGTH
        or any(c.isspace() for c in value)
        or "\\" in value
        or "/" in value
        or "://" in value
        or re.match(r"^[A-Za-z]:", value)
    ):
        return fallback
    return value


def _safe_error_location(value):
    try:
        items = tuple(value)
    except TypeError:
        return ()
    result = []
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
        value = str(value)
        if value in seen:
            duplicates.add(value)
        seen.add(value)
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


__all__ = ("build_draft_llm_request_plan", "validate_draft_llm_request_plan")

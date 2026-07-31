"""Construction and authoritative validation for Phase 4.3 composition."""

import re
import unicodedata
from dataclasses import dataclass

from pydantic import ValidationError

from .claim_binding_models import ClaimBindingValidationContext, DraftClaimBindingPlan
from .claim_binding_validation import validate_draft_claim_binding_plan
from .errors import DomainValidationError, DomainValidationIssue
from .section_composition_identity import (
    compute_composed_claim_fingerprint,
    compute_composed_claim_identity,
    compute_composed_section_fingerprint,
    compute_composed_section_identity,
    compute_draft_section_composition_plan_fingerprint,
    compute_draft_section_composition_plan_identity,
)
from .section_composition_models import (
    ComposedClaim,
    ComposedSection,
    DraftSectionCompositionPlan,
    SectionCompositionValidationContext,
)

_ZERO_FINGERPRINT = "0" * 64
_PLAN_FALLBACK = "draft-section-composition-plan"
_CONTEXT_FALLBACK = "section-composition-validation-context"
_ARTIFACT_FALLBACK = "section-composition-artifact"
_MAX_REFERENCE_LENGTH = 200


@dataclass(frozen=True, slots=True)
class _AuthoritativeCompositionInputs:
    plan: DraftSectionCompositionPlan | None
    context: SectionCompositionValidationContext | None
    issues: tuple[DomainValidationIssue, ...]


def _canonical_composition_plan_reference(source_plan: DraftClaimBindingPlan) -> str:
    """Derive the sole caller-facing reference for one source binding plan."""

    return f"composition-plan:{source_plan.identity}"


def _canonical_composed_section_reference(source_binding_set) -> str:
    """Derive the sole caller-facing reference for one source binding set."""

    return f"composed-section:{source_binding_set.identity}"


def _canonical_composed_claim_reference(source_binding) -> str:
    """Derive the sole caller-facing reference for one source binding."""

    return f"composed-claim:{source_binding.identity}"


def build_draft_section_composition_plan(
    claim_binding_plan: DraftClaimBindingPlan,
    claim_binding_context: ClaimBindingValidationContext,
) -> DraftSectionCompositionPlan:
    """Materialize one valid Phase 4.2 plan without interpreting its semantics."""

    upstream_plan, upstream_context, issues = _reconstruct_upstream(
        claim_binding_plan, claim_binding_context
    )
    if issues:
        raise DomainValidationError(issues)
    assert upstream_plan is not None and upstream_context is not None
    if upstream_issues := validate_draft_claim_binding_plan(
        upstream_plan, upstream_context
    ):
        raise DomainValidationError(upstream_issues)

    sections = tuple(
        _build_composed_section(upstream_plan, binding_set)
        for binding_set in upstream_plan.section_binding_sets
    )
    value = DraftSectionCompositionPlan(
        identity=f"scout:draft-section-composition-plan:{_ZERO_FINGERPRINT}",
        fingerprint=_ZERO_FINGERPRINT,
        composition_plan_reference=_canonical_composition_plan_reference(upstream_plan),
        source_claim_binding_plan_reference=upstream_plan.plan_reference,
        source_claim_binding_plan_identity=upstream_plan.identity,
        source_claim_binding_plan_fingerprint=upstream_plan.fingerprint,
        draft_reference=upstream_plan.draft_reference,
        draft_fingerprint=upstream_plan.draft_fingerprint,
        normalized_input_reference=upstream_plan.normalized_input_reference,
        composed_sections=sections,
    )
    return _seal(
        value,
        compute_draft_section_composition_plan_identity,
        compute_draft_section_composition_plan_fingerprint,
    )


def _build_composed_section(plan, binding_set) -> ComposedSection:
    claims = tuple(_build_composed_claim(binding) for binding in binding_set.bindings)
    value = ComposedSection(
        identity=f"scout:composed-section:{_ZERO_FINGERPRINT}",
        fingerprint=_ZERO_FINGERPRINT,
        composed_section_reference=_canonical_composed_section_reference(binding_set),
        source_section_binding_set_reference=binding_set.binding_set_reference,
        source_section_binding_set_identity=binding_set.identity,
        source_section_binding_set_fingerprint=binding_set.fingerprint,
        draft_reference=plan.draft_reference,
        section_reference=binding_set.section_reference,
        composed_claims=claims,
    )
    return _seal(
        value,
        compute_composed_section_identity,
        compute_composed_section_fingerprint,
    )


def _build_composed_claim(binding) -> ComposedClaim:
    value = ComposedClaim(
        identity=f"scout:composed-claim:{_ZERO_FINGERPRINT}",
        fingerprint=_ZERO_FINGERPRINT,
        composed_claim_reference=_canonical_composed_claim_reference(binding),
        source_claim_binding_reference=binding.binding_reference,
        source_claim_binding_identity=binding.identity,
        source_claim_binding_fingerprint=binding.fingerprint,
        draft_reference=binding.draft_reference,
        section_reference=binding.section_reference,
        claim_reference=binding.claim_reference,
        requirement=binding.requirement,
        role=binding.role,
        ordinal=binding.ordinal,
    )
    return _seal(
        value,
        compute_composed_claim_identity,
        compute_composed_claim_fingerprint,
    )


def _seal(value, identity_function, fingerprint_function):
    value = value.model_copy(update={"identity": identity_function(value)})
    return value.model_copy(update={"fingerprint": fingerprint_function(value)})


def validate_draft_section_composition_plan(
    plan: DraftSectionCompositionPlan,
    context: SectionCompositionValidationContext,
) -> tuple[DomainValidationIssue, ...]:
    """Validate one composition plan against fresh authoritative Phase 4.2 state."""

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
            for candidate in validated_context.claim_binding_plans
            if candidate.plan_reference
            == validated_plan.source_claim_binding_plan_reference
        ),
        None,
    )
    if source_plan is None:
        issues.append(
            _issue(
                "section-composition-unknown-source-binding-plan",
                validated_plan,
                ("source_claim_binding_plan_reference",),
            )
        )
        return _ordered(issues)
    if upstream_issues := validate_draft_claim_binding_plan(
        source_plan, validated_context.claim_binding_validation_context
    ):
        issues.append(
            _issue(
                "section-composition-invalid-source-binding-plan",
                validated_plan,
                related=tuple(item.code for item in upstream_issues),
            )
        )
        return _ordered(issues)

    _validate_plan_lineage(validated_plan, source_plan, issues)
    _validate_sections(validated_plan, source_plan, issues)
    return _ordered(issues)


def _validate_plan_lineage(plan, source_plan, issues) -> None:
    comparisons = (
        (
            "composition_plan_reference",
            _canonical_composition_plan_reference(source_plan),
            "section-composition-invalid-composition-plan-reference",
        ),
        (
            "source_claim_binding_plan_identity",
            source_plan.identity,
            "section-composition-source-plan-identity-mismatch",
        ),
        (
            "source_claim_binding_plan_fingerprint",
            source_plan.fingerprint,
            "section-composition-source-plan-fingerprint-mismatch",
        ),
        (
            "draft_reference",
            source_plan.draft_reference,
            "section-composition-draft-reference-mismatch",
        ),
        (
            "draft_fingerprint",
            source_plan.draft_fingerprint,
            "section-composition-draft-fingerprint-mismatch",
        ),
        (
            "normalized_input_reference",
            source_plan.normalized_input_reference,
            "section-composition-normalized-input-mismatch",
        ),
    )
    for field, expected, code in comparisons:
        if getattr(plan, field) != expected:
            issues.append(_issue(code, plan, (field,)))


def _validate_sections(plan, source_plan, issues) -> None:
    actual = plan.composed_sections
    expected = source_plan.section_binding_sets
    if len(actual) < len(expected):
        issues.append(
            _issue(
                "section-composition-missing-composed-section",
                plan,
                ("composed_sections",),
                tuple(item.section_reference for item in expected[len(actual) :]),
            )
        )
    elif len(actual) > len(expected):
        issues.append(
            _issue(
                "section-composition-extra-composed-section",
                plan,
                ("composed_sections",),
                tuple(item.section_reference for item in actual[len(expected) :]),
            )
        )
    actual_order = tuple(item.source_section_binding_set_identity for item in actual)
    expected_order = tuple(item.identity for item in expected)
    if actual_order != expected_order and len(actual) == len(expected):
        issues.append(
            _issue(
                "section-composition-invalid-section-order",
                plan,
                ("composed_sections",),
            )
        )
    expected_by_identity = {item.identity: item for item in expected}
    for section_index, section in enumerate(actual):
        source_set = expected_by_identity.get(
            section.source_section_binding_set_identity
        )
        if source_set is None:
            issues.append(
                _issue(
                    "section-composition-source-binding-set-mismatch",
                    section,
                    ("composed_sections", section_index),
                )
            )
            continue
        _validate_section(section, source_set, source_plan, section_index, issues)


def _validate_section(section, source_set, source_plan, section_index, issues) -> None:
    comparisons = (
        (
            "composed_section_reference",
            _canonical_composed_section_reference(source_set),
            "section-composition-invalid-composed-section-reference",
        ),
        (
            "source_section_binding_set_reference",
            source_set.binding_set_reference,
            "section-composition-source-binding-set-reference-mismatch",
        ),
        (
            "source_section_binding_set_fingerprint",
            source_set.fingerprint,
            "section-composition-source-binding-set-fingerprint-mismatch",
        ),
        (
            "draft_reference",
            source_plan.draft_reference,
            "section-composition-section-draft-mismatch",
        ),
        (
            "section_reference",
            source_set.section_reference,
            "section-composition-section-reference-mismatch",
        ),
    )
    for field, expected, code in comparisons:
        if getattr(section, field) != expected:
            issues.append(_issue(code, section, (field,)))
    _validate_claim_duplicates(section, issues)
    _validate_claims(section, source_set, section_index, issues)


def _validate_claims(section, source_set, section_index, issues) -> None:
    actual = section.composed_claims
    expected = source_set.bindings
    if len(actual) < len(expected):
        issues.append(
            _issue(
                "section-composition-missing-composed-claim",
                section,
                ("composed_claims",),
                tuple(item.claim_reference for item in expected[len(actual) :]),
            )
        )
    elif len(actual) > len(expected):
        issues.append(
            _issue(
                "section-composition-extra-composed-claim",
                section,
                ("composed_claims",),
                tuple(item.claim_reference for item in actual[len(expected) :]),
            )
        )
    actual_order = tuple(item.source_claim_binding_identity for item in actual)
    expected_order = tuple(item.identity for item in expected)
    if actual_order != expected_order and len(actual) == len(expected):
        issues.append(
            _issue(
                "section-composition-invalid-claim-order",
                section,
                ("composed_claims",),
            )
        )
    expected_by_identity = {item.identity: item for item in expected}
    for claim_index, claim in enumerate(actual):
        source_binding = expected_by_identity.get(claim.source_claim_binding_identity)
        path = ("composed_sections", section_index, "composed_claims", claim_index)
        if source_binding is None:
            issues.append(
                _issue("section-composition-source-binding-mismatch", claim, path)
            )
            continue
        _validate_claim(claim, source_binding, source_set, path, issues)


def _validate_claim(claim, source, source_set, path, issues) -> None:
    comparisons = (
        (
            "composed_claim_reference",
            _canonical_composed_claim_reference(source),
            "section-composition-invalid-composed-claim-reference",
        ),
        (
            "source_claim_binding_reference",
            source.binding_reference,
            "section-composition-source-binding-reference-mismatch",
        ),
        (
            "source_claim_binding_fingerprint",
            source.fingerprint,
            "section-composition-source-binding-fingerprint-mismatch",
        ),
        (
            "draft_reference",
            source.draft_reference,
            "section-composition-claim-draft-mismatch",
        ),
        (
            "section_reference",
            source_set.section_reference,
            "section-composition-claim-section-mismatch",
        ),
        (
            "claim_reference",
            source.claim_reference,
            "section-composition-claim-reference-mismatch",
        ),
        (
            "requirement",
            source.requirement,
            "section-composition-requirement-mismatch",
        ),
        ("role", source.role, "section-composition-role-mismatch"),
        ("ordinal", source.ordinal, "section-composition-ordinal-mismatch"),
    )
    for field, expected, code in comparisons:
        if getattr(claim, field) != expected:
            issues.append(_issue(code, claim, (*path, field)))


def _validate_seals(plan, issues) -> None:
    artifacts = (
        (
            plan,
            compute_draft_section_composition_plan_identity,
            compute_draft_section_composition_plan_fingerprint,
            "plan",
        ),
        *(
            (
                section,
                compute_composed_section_identity,
                compute_composed_section_fingerprint,
                "section",
            )
            for section in plan.composed_sections
        ),
        *(
            (
                claim,
                compute_composed_claim_identity,
                compute_composed_claim_fingerprint,
                "claim",
            )
            for section in plan.composed_sections
            for claim in section.composed_claims
        ),
    )
    for artifact, identity_function, fingerprint_function, kind in artifacts:
        if artifact.identity != identity_function(artifact):
            issues.append(
                _issue(f"section-composition-invalid-{kind}-identity", artifact)
            )
        if artifact.fingerprint != fingerprint_function(artifact):
            issues.append(
                _issue(f"section-composition-invalid-{kind}-fingerprint", artifact)
            )


def _validate_plan_duplicates(plan, issues) -> None:
    sections = plan.composed_sections
    for field, code in (
        ("composed_section_reference", "duplicate-composed-section-reference"),
        ("identity", "duplicate-composed-section-identity"),
        ("section_reference", "duplicate-section-reference"),
        (
            "source_section_binding_set_reference",
            "duplicate-source-binding-set-reference",
        ),
        (
            "source_section_binding_set_identity",
            "duplicate-source-binding-set-identity",
        ),
    ):
        if duplicates := _duplicates(getattr(item, field) for item in sections):
            issues.append(
                _issue(
                    f"section-composition-{code}",
                    plan,
                    ("composed_sections",),
                    duplicates,
                )
            )


def _validate_claim_duplicates(section, issues) -> None:
    claims = section.composed_claims
    for field, code in (
        ("composed_claim_reference", "duplicate-composed-claim-reference"),
        ("identity", "duplicate-composed-claim-identity"),
        ("source_claim_binding_reference", "duplicate-source-binding-reference"),
        ("source_claim_binding_identity", "duplicate-source-binding-identity"),
        ("claim_reference", "duplicate-claim-reference"),
        ("ordinal", "duplicate-ordinal"),
    ):
        if duplicates := _duplicates(getattr(item, field) for item in claims):
            issues.append(
                _issue(
                    f"section-composition-{code}",
                    section,
                    ("composed_claims",),
                    duplicates,
                )
            )
    if tuple(item.ordinal for item in claims) != tuple(range(len(claims))):
        issues.append(
            _issue(
                "section-composition-invalid-ordinal-sequence",
                section,
                ("composed_claims",),
            )
        )


def _reconstruct_upstream(raw_plan, raw_context):
    issues: list[DomainValidationIssue] = []
    plan = None
    context = None
    try:
        plan = DraftClaimBindingPlan.model_validate(
            raw_plan.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(
                error, raw_plan, "section-composition-invalid-source-plan"
            )
        )
    try:
        context = ClaimBindingValidationContext.model_validate(
            raw_context.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(
                error, raw_context, "section-composition-invalid-source-context"
            )
        )
    return plan, context, _ordered(issues)


def _reconstruct_for_validation(raw_plan, raw_context):
    issues: list[DomainValidationIssue] = []
    plan = None
    context = None
    try:
        plan = DraftSectionCompositionPlan.model_validate(
            raw_plan.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(
                error,
                raw_plan,
                "section-composition-invalid-reconstructed-plan",
            )
        )
    try:
        context = SectionCompositionValidationContext.model_validate(
            raw_context.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001
        issues.extend(
            _validation_error_issues(
                error,
                raw_context,
                "section-composition-invalid-reconstructed-context",
            )
        )
    return _AuthoritativeCompositionInputs(plan, context, _ordered(issues))


def _validation_error_issues(error, artifact, fallback):
    details = error.errors() if isinstance(error, ValidationError) else ({"loc": ()},)
    return tuple(
        _issue(
            (
                str(item.get("type"))
                if str(item.get("type", "")).startswith("section-composition-")
                else fallback
            ),
            _safe_artifact_reference(artifact, fallback),
            _safe_error_location(item.get("loc", ())),
        )
        for item in details
    )


def _issue(code, artifact, path=(), related=()):
    if isinstance(artifact, str):
        reference = artifact
    else:
        reference = _safe_artifact_reference(artifact, _ARTIFACT_FALLBACK)
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
        "composition_plan_reference",
        "composed_section_reference",
        "composed_claim_reference",
        "plan_reference",
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
    if (
        not normalized
        or len(normalized) > _MAX_REFERENCE_LENGTH
        or any(character.isspace() for character in normalized)
        or "\\" in normalized
        or "/" in normalized
        or "://" in normalized
        or re.match(r"^[A-Za-z]:", normalized)
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
    seen: set[str] = set()
    duplicates: set[str] = set()
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


__all__ = (
    "build_draft_section_composition_plan",
    "validate_draft_section_composition_plan",
)

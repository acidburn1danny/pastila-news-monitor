"""Pure explicit validation for Module 2.9 Phase 4.2 claim bindings."""

import re
import unicodedata
from dataclasses import dataclass

from pydantic import ValidationError

from .claim_binding_identity import (
    claim_binding_identity,
    draft_claim_binding_plan_identity,
    section_claim_binding_set_identity,
)
from .claim_binding_models import (
    ClaimBindingRequirement,
    ClaimBindingValidationContext,
    DraftClaimBindingPlan,
    claim_binding_semantic_fingerprint,
)
from .draft_validation import validate_draft_structure
from .errors import DomainValidationIssue

_RECONSTRUCTION_ARTIFACT_FALLBACK = "draft-claim-binding-plan"
_VALIDATION_ARTIFACT_FALLBACK = "claim-binding-artifact"
_MAX_DIAGNOSTIC_REFERENCE_LENGTH = 200


@dataclass(frozen=True, slots=True)
class _AuthoritativeClaimBindingInputs:
    plan: DraftClaimBindingPlan | None
    context: ClaimBindingValidationContext | None
    issues: tuple[DomainValidationIssue, ...]


def _issue(
    code: str,
    artifact,
    path: tuple[str | int, ...] = (),
    related: tuple[str, ...] = (),
) -> DomainValidationIssue:
    reference = (
        artifact
        if isinstance(artifact, str)
        else next(
            (
                getattr(artifact, name)
                for name in (
                    "binding_reference",
                    "binding_set_reference",
                    "plan_reference",
                    "identity",
                )
                if hasattr(artifact, name)
            ),
            type(artifact).__name__,
        )
    )
    safe_reference = _safe_diagnostic_reference(
        reference, fallback=_VALIDATION_ARTIFACT_FALLBACK
    )
    return DomainValidationIssue(
        code=code,
        artifact_reference=safe_reference,
        artifact_type=type(artifact).__name__,
        field_reference=".".join(map(str, path)) or None,
        field_path=path,
        related_references=tuple(sorted(related)),
        message_key=code,
    )


def _duplicates(values) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        normalized = str(value)
        if normalized in seen:
            duplicates.add(normalized)
        seen.add(normalized)
    return tuple(sorted(duplicates))


def validate_draft_claim_binding_plan(
    plan: DraftClaimBindingPlan,
    context: ClaimBindingValidationContext,
) -> tuple[DomainValidationIssue, ...]:
    """Validate one plan against authoritative rebuilt draft ownership state."""

    reconstructed = _reconstruct_for_validation(plan, context)
    if reconstructed.issues:
        return reconstructed.issues
    validated_plan = reconstructed.plan
    validated_context = reconstructed.context
    assert validated_plan is not None and validated_context is not None

    issues: list[DomainValidationIssue] = []
    _validate_seals(validated_plan, issues)
    _validate_plan_duplicates(validated_plan, issues)

    drafts = {draft.identity: draft for draft in validated_context.drafts}
    draft = drafts.get(validated_plan.draft_reference)
    if draft is None:
        issues.append(
            _issue(
                "claim-binding-unknown-draft-reference",
                validated_plan,
                ("draft_reference",),
            )
        )
        return _ordered(issues)
    if validate_draft_structure(draft, validated_context.draft_validation_context):
        issues.append(_issue("claim-binding-invalid-referenced-draft", validated_plan))
        return _ordered(issues)
    if validated_plan.draft_fingerprint != draft.fingerprint:
        issues.append(
            _issue(
                "claim-binding-draft-fingerprint-mismatch",
                validated_plan,
                ("draft_fingerprint",),
            )
        )
    if validated_plan.normalized_input_reference != draft.normalized_input_reference:
        issues.append(
            _issue(
                "claim-binding-normalized-input-mismatch",
                validated_plan,
                ("normalized_input_reference",),
            )
        )

    scopes = {
        scope.normalized_input_reference: scope
        for scope in validated_context.draft_validation_context.normalized_input_scopes
    }
    scope = scopes.get(draft.normalized_input_reference)
    if scope is None:
        issues.append(
            _issue("claim-binding-missing-normalized-input-scope", validated_plan)
        )
        return _ordered(issues)
    owned_claims = frozenset(scope.claim_references)
    globally_owned_claims = {
        reference
        for candidate in validated_context.draft_validation_context.normalized_input_scopes
        for reference in candidate.claim_references
    }
    sections = {section.section_reference: section for section in draft.sections}
    expected_set_order = tuple(
        reference
        for reference in draft.section_references
        if reference
        in {item.section_reference for item in validated_plan.section_binding_sets}
    )
    actual_set_order = tuple(
        item.section_reference for item in validated_plan.section_binding_sets
    )
    if actual_set_order != expected_set_order:
        issues.append(
            _issue(
                "claim-binding-section-set-order-mismatch",
                validated_plan,
                ("section_binding_sets",),
            )
        )

    bound_sections: set[str] = set()
    for set_index, binding_set in enumerate(validated_plan.section_binding_sets):
        bound_sections.add(binding_set.section_reference)
        section = sections.get(binding_set.section_reference)
        if section is None:
            issues.append(
                _issue(
                    "claim-binding-unknown-section-reference",
                    binding_set,
                    ("section_reference",),
                )
            )
            continue
        if binding_set.draft_reference != draft.identity:
            issues.append(
                _issue(
                    "claim-binding-set-draft-mismatch",
                    binding_set,
                    ("draft_reference",),
                )
            )
        _validate_binding_set(
            binding_set,
            section,
            draft.identity,
            owned_claims,
            globally_owned_claims,
            set_index,
            issues,
        )

    for section in draft.sections:
        if (
            section.required_claim_references
            and section.section_reference not in bound_sections
        ):
            issues.append(
                _issue(
                    "claim-binding-missing-required-section-binding-set",
                    validated_plan,
                    ("section_binding_sets",),
                    (section.section_reference,),
                )
            )
    return _ordered(issues)


def _validate_seals(plan: DraftClaimBindingPlan, issues: list) -> None:
    artifacts = (
        (plan, draft_claim_binding_plan_identity),
        *(
            (binding_set, section_claim_binding_set_identity)
            for binding_set in plan.section_binding_sets
        ),
        *(
            (binding, claim_binding_identity)
            for binding_set in plan.section_binding_sets
            for binding in binding_set.bindings
        ),
    )
    for artifact, identity_function in artifacts:
        if artifact.identity != identity_function(artifact):
            issues.append(_issue("claim-binding-identity-mismatch", artifact))
        if artifact.fingerprint != claim_binding_semantic_fingerprint(artifact):
            issues.append(_issue("claim-binding-fingerprint-mismatch", artifact))


def _validate_plan_duplicates(plan: DraftClaimBindingPlan, issues: list) -> None:
    sets = plan.section_binding_sets
    for field, code in (
        ("binding_set_reference", "claim-binding-duplicate-binding-set-reference"),
        ("identity", "claim-binding-duplicate-binding-set-identity"),
        ("section_reference", "claim-binding-duplicate-section-reference"),
    ):
        if duplicates := _duplicates(getattr(item, field) for item in sets):
            issues.append(_issue(code, plan, ("section_binding_sets",), duplicates))


def _validate_binding_set(
    binding_set,
    section,
    draft_reference: str,
    owned_claims: frozenset[str],
    globally_owned_claims: set[str],
    set_index: int,
    issues: list,
) -> None:
    bindings = binding_set.bindings
    for field, code in (
        ("binding_reference", "claim-binding-duplicate-binding-reference"),
        ("identity", "claim-binding-duplicate-binding-identity"),
        ("claim_reference", "claim-binding-duplicate-claim-reference"),
        ("ordinal", "claim-binding-duplicate-ordinal"),
    ):
        if duplicates := _duplicates(getattr(item, field) for item in bindings):
            issues.append(_issue(code, binding_set, ("bindings",), duplicates))
    actual_ordinals = tuple(item.ordinal for item in bindings)
    if actual_ordinals != tuple(range(len(bindings))):
        issues.append(
            _issue("claim-binding-invalid-ordinal-sequence", binding_set, ("bindings",))
        )

    required = frozenset(section.required_claim_references)
    optional = frozenset(section.optional_claim_references)
    bound_required: list[str] = []
    for binding_index, binding in enumerate(bindings):
        path = ("section_binding_sets", set_index, "bindings", binding_index)
        if binding.draft_reference != draft_reference:
            issues.append(_issue("claim-binding-draft-mismatch", binding, path))
        if binding.section_reference != section.section_reference:
            issues.append(_issue("claim-binding-section-mismatch", binding, path))
        if binding.claim_reference not in owned_claims:
            code = (
                "claim-binding-cross-normalized-input-claim-ownership"
                if binding.claim_reference in globally_owned_claims
                else "claim-binding-unknown-claim-reference"
            )
            issues.append(_issue(code, binding, path, (binding.claim_reference,)))
        if binding.claim_reference in required:
            if binding.requirement != ClaimBindingRequirement.REQUIRED:
                issues.append(
                    _issue("claim-binding-required-marked-optional", binding, path)
                )
            bound_required.append(binding.claim_reference)
        elif binding.claim_reference in optional:
            if binding.requirement != ClaimBindingRequirement.OPTIONAL:
                issues.append(
                    _issue("claim-binding-optional-marked-required", binding, path)
                )
        else:
            issues.append(
                _issue("claim-binding-claim-not-declared-by-section", binding, path)
            )
    if missing := tuple(sorted(required - set(bound_required))):
        issues.append(
            _issue(
                "claim-binding-missing-required-claim",
                binding_set,
                ("bindings",),
                missing,
            )
        )


def _reconstruct_for_validation(
    raw_plan: DraftClaimBindingPlan,
    raw_context: ClaimBindingValidationContext,
) -> _AuthoritativeClaimBindingInputs:
    issues: list[DomainValidationIssue] = []
    plan = None
    context = None
    try:
        plan = DraftClaimBindingPlan.model_validate(
            raw_plan.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001  # public reconstruction containment
        issues.extend(
            _validation_error_issues(
                error, raw_plan, "claim-binding-invalid-reconstructed-plan"
            )
        )
    try:
        context = ClaimBindingValidationContext.model_validate(
            raw_context.model_dump(mode="python", warnings=False)
        )
    except Exception as error:  # noqa: BLE001  # public reconstruction containment
        issues.extend(
            _validation_error_issues(
                error, raw_context, "claim-binding-invalid-reconstructed-context"
            )
        )
    return _AuthoritativeClaimBindingInputs(plan, context, _ordered(issues))


def _validation_error_issues(error, artifact, fallback):
    details = error.errors() if isinstance(error, ValidationError) else ({"loc": ()},)
    return tuple(
        _issue(
            (
                str(item.get("type"))
                if str(item.get("type", "")).startswith("claim-binding-")
                else fallback
            ),
            _safe_reconstruction_artifact_reference(artifact),
            _safe_error_location(item.get("loc", ())),
        )
        for item in details
    )


def _safe_reconstruction_artifact_reference(artifact) -> str:
    """Return a bounded deterministic reference without exposing raw values."""

    try:
        value = getattr(artifact, "plan_reference", None)
    except Exception:  # noqa: BLE001  # hostile public-input properties are contained
        return _RECONSTRUCTION_ARTIFACT_FALLBACK
    return _safe_diagnostic_reference(value, fallback=_RECONSTRUCTION_ARTIFACT_FALLBACK)


def _safe_diagnostic_reference(value, *, fallback: str) -> str:
    """Normalize one bounded public issue reference or return its contract name."""

    if not isinstance(value, str):
        return fallback
    normalized = unicodedata.normalize("NFC", value)
    if (
        not normalized
        or len(normalized) > _MAX_DIAGNOSTIC_REFERENCE_LENGTH
        or any(character.isspace() for character in normalized)
        or "\\" in normalized
        or "/" in normalized
        or "://" in normalized
        or re.match(r"^[A-Za-z]:", normalized)
    ):
        return fallback
    return normalized


def _safe_error_location(value) -> tuple[str | int, ...]:
    """Normalize Pydantic locations without retaining arbitrary objects."""

    try:
        items = tuple(value)
    except TypeError:
        return ()
    normalized: list[str | int] = []
    for item in items:
        if isinstance(item, int) and not isinstance(item, bool):
            normalized.append(item)
        elif isinstance(item, str):
            token = unicodedata.normalize("NFC", item)
            normalized.append(
                token
                if token
                and len(token) <= _MAX_DIAGNOSTIC_REFERENCE_LENGTH
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", token)
                else "invalid-field"
            )
        else:
            normalized.append("invalid-field")
    return tuple(normalized)


def _ordered(issues) -> tuple[DomainValidationIssue, ...]:
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


__all__ = ("validate_draft_claim_binding_plan",)

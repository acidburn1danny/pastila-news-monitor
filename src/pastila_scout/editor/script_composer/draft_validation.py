"""Pure structural and contextual validation for Phase 4.1 draft plans."""

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from .draft_identity import (
    draft_section_identity,
    draft_structure_identity,
    transition_slot_identity,
)
from .draft_models import (
    DraftSection,
    DraftStructure,
    DraftValidationContext,
    draft_semantic_fingerprint,
)
from .errors import DomainValidationError, DomainValidationIssue


@dataclass(frozen=True, slots=True)
class _AuthoritativeDraftValidationInputs:
    draft: DraftStructure | None
    context: DraftValidationContext | None
    issues: tuple[DomainValidationIssue, ...]


def _issue(
    code: str,
    artifact,
    path: tuple[str | int, ...] = (),
    related: tuple[str, ...] = (),
) -> DomainValidationIssue:
    reference = getattr(
        artifact,
        "section_reference",
        getattr(
            artifact,
            "transition_reference",
            getattr(artifact, "identity", type(artifact).__name__),
        ),
    )
    return DomainValidationIssue(
        code=code,
        artifact_reference=reference,
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
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return tuple(sorted(duplicates))


def _reference_issues(section: DraftSection) -> list[DomainValidationIssue]:
    issues: list[DomainValidationIssue] = []
    classifications = (
        ("required_claim_references", section.required_claim_references),
        ("optional_claim_references", section.optional_claim_references),
        ("required_evidence_references", section.required_evidence_references),
        ("optional_evidence_references", section.optional_evidence_references),
    )
    for name, values in classifications:
        if duplicates := _duplicates(values):
            issues.append(
                _issue(
                    f"draft-duplicate-{name.removesuffix('_references').replace('_', '-')}-reference",
                    section,
                    (name,),
                    duplicates,
                )
            )
    for kind in ("claim", "evidence"):
        required = getattr(section, f"required_{kind}_references")
        optional = getattr(section, f"optional_{kind}_references")
        if overlap := tuple(sorted(set(required) & set(optional))):
            issues.append(
                _issue(
                    f"draft-duplicate-{kind}-reference",
                    section,
                    (f"optional_{kind}_references",),
                    overlap,
                )
            )
    return issues


def draft_structure_invariant_issues(
    draft: DraftStructure,
) -> tuple[DomainValidationIssue, ...]:
    """Return stable local integrity issues without external state."""

    issues: list[DomainValidationIssue] = []
    sections = draft.sections
    section_references = tuple(item.section_reference for item in sections)
    if duplicates := _duplicates(item.identity for item in sections):
        issues.append(
            _issue("draft-duplicate-section-identity", draft, ("sections",), duplicates)
        )
    if duplicates := _duplicates(section_references):
        issues.append(
            _issue(
                "draft-duplicate-section-reference", draft, ("sections",), duplicates
            )
        )
    if duplicates := _duplicates(str(item.order_index) for item in sections):
        issues.append(
            _issue("draft-duplicate-section-order", draft, ("sections",), duplicates)
        )
    expected_orders = tuple(range(len(sections)))
    actual_orders = tuple(item.order_index for item in sections)
    if actual_orders != expected_orders:
        issues.append(_issue("draft-invalid-section-order", draft, ("sections",)))
    if draft.section_references != section_references:
        issues.append(
            _issue(
                "draft-section-reference-order-mismatch",
                draft,
                ("section_references",),
            )
        )

    known_sections = set(section_references)
    transitions = draft.transitions
    transition_slots: dict[tuple[str, str], list[str]] = {}
    for field in ("identity", "transition_reference", "fingerprint"):
        if duplicates := _duplicates(str(getattr(item, field)) for item in transitions):
            issues.append(
                _issue(
                    f"draft-duplicate-transition-{field.replace('_', '-')}",
                    draft,
                    ("transitions",),
                    duplicates,
                )
            )
    for transition in transitions:
        transition_slots.setdefault(
            (transition.from_section, transition.to_section), []
        ).append(transition.transition_reference)
        if transition.from_section == transition.to_section:
            issues.append(
                _issue(
                    "draft-self-transition",
                    transition,
                    ("to_section",),
                    (transition.from_section,),
                )
            )
        missing = tuple(
            sorted(
                item
                for item in (transition.from_section, transition.to_section)
                if item not in known_sections
            )
        )
        if missing:
            issues.append(
                _issue("draft-orphan-transition", transition, related=missing)
            )
        source = next(
            (
                item
                for item in sections
                if item.section_reference == transition.from_section
            ),
            None,
        )
        destination = next(
            (
                item
                for item in sections
                if item.section_reference == transition.to_section
            ),
            None,
        )
        if (
            source is not None
            and destination is not None
            and (
                source.transition_after != transition.transition_reference
                or destination.transition_before != transition.transition_reference
            )
        ):
            issues.append(
                _issue(
                    "draft-transition-endpoint-participation-mismatch",
                    transition,
                    related=(transition.from_section, transition.to_section),
                )
            )
    for slot, references in sorted(transition_slots.items()):
        if len(references) > 1:
            issues.append(
                _issue(
                    "draft-transition-slot-collision",
                    draft,
                    ("transitions",),
                    tuple(sorted((*slot, *references))),
                )
            )

    transitions_by_reference = {item.transition_reference: item for item in transitions}
    for section in sections:
        issues.extend(_reference_issues(section))
        for field, expected_side in (
            ("transition_before", "to_section"),
            ("transition_after", "from_section"),
        ):
            reference = getattr(section, field)
            if reference is None:
                continue
            transition = transitions_by_reference.get(reference)
            if transition is None:
                issues.append(
                    _issue(
                        "draft-missing-transition-reference",
                        section,
                        (field,),
                        (reference,),
                    )
                )
            elif getattr(transition, expected_side) != section.section_reference:
                issues.append(
                    _issue(
                        "draft-transition-section-mismatch",
                        section,
                        (field,),
                        (reference,),
                    )
                )

    artifacts = (*sections, *transitions)
    if duplicates := _duplicates(item.fingerprint for item in artifacts):
        issues.append(_issue("draft-duplicate-fingerprint", draft, related=duplicates))
    return _ordered(issues)


def validate_draft_structure(
    draft: DraftStructure,
    context: DraftValidationContext | None = None,
) -> tuple[DomainValidationIssue, ...]:
    """Validate local seals/linkage and optional upstream reference ownership."""

    reconstructed = _reconstruct_for_validation(draft, context)
    if reconstructed.issues:
        return reconstructed.issues
    validated_draft = reconstructed.draft
    validated_context = reconstructed.context
    assert validated_draft is not None

    issues = list(draft_structure_invariant_issues(validated_draft))
    identities = (
        (validated_draft, draft_structure_identity),
        *((item, draft_section_identity) for item in validated_draft.sections),
        *((item, transition_slot_identity) for item in validated_draft.transitions),
    )
    for artifact, identity_function in identities:
        if artifact.identity != identity_function(artifact):
            issues.append(_issue("draft-identity-mismatch", artifact, ("identity",)))
        if artifact.fingerprint != draft_semantic_fingerprint(artifact):
            issues.append(
                _issue("draft-fingerprint-mismatch", artifact, ("fingerprint",))
            )

    if validated_context is not None:
        scopes = {
            item.normalized_input_reference: item
            for item in validated_context.normalized_input_scopes
        }
        scope = scopes.get(validated_draft.normalized_input_reference)
        if scope is None:
            issues.append(
                _issue(
                    "draft-missing-normalized-input-reference",
                    validated_draft,
                    ("normalized_input_reference",),
                )
            )
        if scope is None:
            return _ordered(issues)

        plans = {
            item.execution_plan_reference: item.execution_plan_fingerprint
            for item in scope.execution_plans
        }
        global_plan_references = {
            item.execution_plan_reference
            for candidate_scope in validated_context.normalized_input_scopes
            for item in candidate_scope.execution_plans
        }
        if validated_draft.execution_plan_reference not in plans:
            code = (
                "draft-cross-normalized-input-execution-plan-ownership"
                if validated_draft.execution_plan_reference in global_plan_references
                else "draft-missing-execution-plan-reference"
            )
            issues.append(
                _issue(
                    code,
                    validated_draft,
                    ("execution_plan_reference",),
                )
            )
        elif (
            plans[validated_draft.execution_plan_reference]
            != validated_draft.execution_plan_fingerprint
        ):
            issues.append(
                _issue(
                    "draft-execution-plan-fingerprint-mismatch",
                    validated_draft,
                    ("execution_plan_fingerprint",),
                )
            )
        for index, section in enumerate(validated_draft.sections):
            for kind, allowed, globally_allowed in (
                (
                    "claim",
                    frozenset(scope.claim_references),
                    {
                        reference
                        for candidate_scope in validated_context.normalized_input_scopes
                        for reference in candidate_scope.claim_references
                    },
                ),
                (
                    "evidence",
                    frozenset(scope.evidence_references),
                    {
                        reference
                        for candidate_scope in validated_context.normalized_input_scopes
                        for reference in candidate_scope.evidence_references
                    },
                ),
            ):
                references = (
                    *getattr(section, f"required_{kind}_references"),
                    *getattr(section, f"optional_{kind}_references"),
                )
                if missing := tuple(sorted(set(references) - allowed)):
                    cross_owned = tuple(
                        reference
                        for reference in missing
                        if reference in globally_allowed
                    )
                    unknown = tuple(
                        reference
                        for reference in missing
                        if reference not in globally_allowed
                    )
                    if cross_owned:
                        issues.append(
                            _issue(
                                f"draft-cross-normalized-input-{kind}-ownership",
                                section,
                                ("sections", index, f"{kind}_references"),
                                cross_owned,
                            )
                        )
                    if not unknown:
                        continue
                    issues.append(
                        _issue(
                            f"draft-missing-{kind}-reference",
                            section,
                            ("sections", index, f"{kind}_references"),
                            unknown,
                        )
                    )
    return _ordered(issues)


def _reconstruct_for_validation(
    raw_draft: DraftStructure,
    raw_context: DraftValidationContext | None,
) -> _AuthoritativeDraftValidationInputs:
    issues: list[DomainValidationIssue] = []
    validated_draft: DraftStructure | None = None
    validated_context: DraftValidationContext | None = None
    try:
        validated_draft = DraftStructure.model_validate(
            raw_draft.model_dump(mode="python", warnings=False)
        )
    except (ValidationError, AttributeError, TypeError, ValueError) as error:
        issues.extend(
            _validation_error_issues(
                error, raw_draft, "draft-invalid-reconstructed-model-contract"
            )
        )
    if raw_context is not None:
        try:
            validated_context = DraftValidationContext.model_validate(
                raw_context.model_dump(mode="python", warnings=False)
            )
        except (ValidationError, AttributeError, TypeError, ValueError) as error:
            issues.extend(
                _validation_error_issues(
                    error,
                    raw_context,
                    "draft-invalid-reconstructed-context-contract",
                )
            )
    return _AuthoritativeDraftValidationInputs(
        draft=validated_draft,
        context=validated_context,
        issues=_ordered(issues),
    )


def _validation_error_issues(
    error: Exception,
    artifact,
    code: str,
) -> tuple[DomainValidationIssue, ...]:
    details = error.errors() if isinstance(error, ValidationError) else ({"loc": ()},)
    return _ordered(
        _issue(
            (
                str(item.get("type"))
                if str(item.get("type", "")).startswith("draft-")
                else code
            ),
            artifact,
            tuple(item.get("loc", ())),
        )
        for item in details
    )


def require_valid_draft_structure(
    draft: DraftStructure,
    context: DraftValidationContext | None = None,
) -> None:
    """Raise the public aggregate error when a draft is invalid."""

    if issues := validate_draft_structure(draft, context):
        raise DomainValidationError(issues)


def construct_draft_structure(
    payload: dict[str, Any], context: DraftValidationContext | None = None
) -> DraftStructure:
    """Parse and fully validate one external draft-structure payload."""

    try:
        draft = DraftStructure.model_validate(payload)
    except ValidationError as error:
        issues = tuple(
            DomainValidationIssue(
                code=str(item["type"]),
                artifact_reference=str(payload.get("identity", "DraftStructure")),
                artifact_type="DraftStructure",
                field_reference=".".join(map(str, item["loc"])),
                field_path=tuple(item["loc"]),
                message_key=str(item["type"]),
            )
            for item in sorted(
                error.errors(), key=lambda item: tuple(map(str, item["loc"]))
            )
        )
        raise DomainValidationError(issues) from None
    require_valid_draft_structure(draft, context)
    return draft


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


__all__ = (
    "construct_draft_structure",
    "require_valid_draft_structure",
    "validate_draft_structure",
)

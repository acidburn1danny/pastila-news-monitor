"""Pure structured validation for Module 2.9 domain artifacts."""

from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from .canonical import semantic_fingerprint
from .errors import DomainValidationError, DomainValidationIssue
from .identity import (
    provider_request_identity,
    provider_response_identity,
    revision_request_identity,
    revision_result_identity,
    script_beat_identity,
    script_paragraph_identity,
    script_segment_identity,
    script_sentence_identity,
    text_span_identity,
)
from .invariants import (
    INVARIANT_FIELD_PATHS,
    attribution_invariant_violations,
    provider_request_invariant_violations,
    provider_response_invariant_violations,
)
from .models import (
    AttributionRealization,
    FrozenDomainModel,
    GeneratedClaimReference,
    ProviderGenerationRequest,
    ProviderGenerationResponse,
    ResolvedGenerationPolicySnapshot,
    RevisionExecutionResult,
    RevisionRequest,
    SatirePermission,
    ScriptBeat,
    ScriptParagraph,
    ScriptSegment,
    ScriptSentence,
    TextSpanReference,
    TextualUnitLineage,
)
from .vocabularies import ProviderExecutionStatus, ProviderFailureReason

PRIMARY_FINGERPRINT_FIELDS = {
    "AuthorityReference": "semantic_fingerprint",
    "GenerationProfile": "profile_fingerprint",
    "ResolvedGenerationPolicySnapshot": "policy_fingerprint",
    "ProviderGenerationRequest": "request_fingerprint",
    "ProviderGeneratedUnit": "unit_fingerprint",
    "ProviderPartialResponse": "partial_fingerprint",
    "ProviderGenerationResponse": "response_fingerprint",
    "ProviderResponseAcceptance": "acceptance_fingerprint",
    "VerifiedTextSpan": "span_fingerprint",
    "VerifiedSourceMaterial": "source_fingerprint",
    "TextSpanReference": "span_fingerprint",
    "ApprovedClaim": "claim_fingerprint",
    "SourceSpanReference": "reference_fingerprint",
    "GeneratedClaimReference": "claim_fingerprint",
    "AttributionRealization": "attribution_fingerprint",
    "DeliveryAnnotation": "annotation_fingerprint",
    "GenerationInstruction": "instruction_fingerprint",
    "GenerationConstraint": "constraint_fingerprint",
    "SatirePermission": "permission_fingerprint",
    "GenerationDecision": "decision_fingerprint",
    "GenerationConflict": "conflict_fingerprint",
    "GenerationTraceEntry": "trace_entry_fingerprint",
    "GenerationTraceability": "traceability_fingerprint",
    "ScriptSentence": "sentence_fingerprint",
    "ScriptParagraph": "paragraph_fingerprint",
    "ScriptBeat": "beat_fingerprint",
    "ScriptSegment": "segment_fingerprint",
    "Transition": "transition_fingerprint",
    "Callback": "callback_fingerprint",
    "ScriptDraft": "script_draft_fingerprint",
    "RevisionAuthority": "authority_fingerprint",
    "RevisionRequest": "request_fingerprint",
    "RevisionExecutionResult": "result_fingerprint",
    "TextualUnitLineage": "lineage_fingerprint",
    "ScriptCompositionInputBundle": "input_fingerprint",
}


def validate_artifact(artifact: FrozenDomainModel) -> tuple[DomainValidationIssue, ...]:
    """Recursively validate semantic fingerprints and deterministic identities."""
    issues: list[DomainValidationIssue] = []
    _walk_artifact(artifact, (), set(), set(), issues)
    return tuple(issues)


def construct_artifact[ArtifactT: FrozenDomainModel](
    model_type: type[ArtifactT], payload: dict[str, Any]
) -> ArtifactT:
    """Construct a contract through the stable public validation boundary."""
    try:
        return model_type.model_validate(payload)
    except ValidationError as error:
        issues = tuple(
            DomainValidationIssue(
                code=(
                    str(detail["type"])
                    if str(detail["type"]) in INVARIANT_FIELD_PATHS
                    else "contract-validation-failed"
                ),
                artifact_reference=_payload_artifact_reference(model_type, payload),
                artifact_type=model_type.__name__,
                field_reference=".".join(
                    str(item)
                    for item in (
                        INVARIANT_FIELD_PATHS.get(str(detail["type"]))
                        or tuple(detail["loc"])
                    )
                ),
                field_path=(
                    INVARIANT_FIELD_PATHS.get(str(detail["type"]))
                    or tuple(detail["loc"])
                ),
                message_key=str(detail["type"]),
            )
            for detail in sorted(
                error.errors(), key=lambda item: tuple(map(str, item["loc"]))
            )
        )
        raise DomainValidationError(issues) from None


def _walk_artifact(
    artifact: FrozenDomainModel,
    path: tuple[str | int, ...],
    seen: set[int],
    active: set[int],
    issues: list[DomainValidationIssue],
) -> None:
    identity = id(artifact)
    if identity in active:
        issues.append(
            DomainValidationIssue(
                "artifact-cycle-detected",
                _artifact_reference(artifact),
                artifact_type=type(artifact).__name__,
                field_path=path,
            )
        )
        return
    if identity in seen:
        return
    seen.add(identity)
    active.add(identity)
    reference = _artifact_reference(artifact)
    field = PRIMARY_FINGERPRINT_FIELDS.get(type(artifact).__name__)
    if field and getattr(artifact, field) != semantic_fingerprint(artifact):
        issues.append(
            DomainValidationIssue(
                "fingerprint-mismatch",
                reference,
                field,
                type(artifact).__name__,
                path + (field,),
            )
        )
    expected_identity = _expected_identity(artifact)
    if expected_identity is not None:
        identity_field, expected = expected_identity
        if getattr(artifact, identity_field) != expected:
            issues.append(
                DomainValidationIssue(
                    "identity-mismatch",
                    reference,
                    identity_field,
                    type(artifact).__name__,
                    path + (identity_field,),
                )
            )
    for violation in _local_invariant_violations(artifact):
        issues.append(
            DomainValidationIssue(
                violation.code,
                reference,
                ".".join(str(item) for item in violation.field_path),
                type(artifact).__name__,
                path + violation.field_path,
            )
        )
    for name in sorted(artifact.__class__.model_fields):
        _walk_value(getattr(artifact, name), path + (name,), seen, active, issues)
    active.remove(identity)


def _walk_value(value, path, seen, active, issues) -> None:
    if isinstance(value, FrozenDomainModel):
        _walk_artifact(value, path, seen, active, issues)
    elif isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            _walk_value(item, path + (index,), seen, active, issues)
    elif isinstance(value, dict):
        for key in sorted(value, key=str):
            _walk_value(value[key], path + (str(key),), seen, active, issues)


def require_valid_artifact(artifact: FrozenDomainModel) -> None:
    """Raise one structured error containing all pure validation issues."""
    if issues := validate_artifact(artifact):
        raise DomainValidationError(issues)


def validate_text_span(
    span: TextSpanReference, sentence: ScriptSentence
) -> tuple[DomainValidationIssue, ...]:
    """Validate exact NFC Unicode-code-point ownership of a sentence substring."""
    issues: list[DomainValidationIssue] = []
    if span.parent_sentence_reference != sentence.script_sentence_id:
        issues.append(
            DomainValidationIssue(
                "text-span-parent-mismatch",
                span.text_span_id,
                "parent_sentence_reference",
            )
        )
    if span.end_offset > len(sentence.text):
        issues.append(
            DomainValidationIssue("text-span-out-of-bounds", span.text_span_id)
        )
    elif sentence.text[span.start_offset : span.end_offset] != span.referenced_text:
        issues.append(
            DomainValidationIssue("text-span-substring-mismatch", span.text_span_id)
        )
    return tuple(issues) + validate_artifact(span)


def validate_text_span_collection(
    spans: Iterable[TextSpanReference], sentence: ScriptSentence
) -> tuple[DomainValidationIssue, ...]:
    """Reject crossing spans while allowing reuse and nesting."""
    ordered = sorted(
        spans,
        key=lambda item: (
            item.start_offset,
            -item.end_offset,
            item.binding_classification,
            item.text_span_id,
        ),
    )
    issues = [issue for span in ordered for issue in validate_text_span(span, sentence)]
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if (
                left.start_offset
                < right.start_offset
                < left.end_offset
                < right.end_offset
            ):
                issues.append(
                    DomainValidationIssue(
                        "crossing-text-spans",
                        left.text_span_id,
                        related_references=(right.text_span_id,),
                    )
                )
    return tuple(issues)


def validate_text_span_bindings(
    bindings: Iterable[GeneratedClaimReference | AttributionRealization],
) -> tuple[DomainValidationIssue, ...]:
    """Reject duplicate semantic evidence edges while allowing span reuse."""
    issues: list[DomainValidationIssue] = []
    seen: set[tuple[str, str, str]] = set()
    for binding in bindings:
        span = binding.text_span_reference.text_span_id
        if isinstance(binding, GeneratedClaimReference):
            edges = (
                (span, claim, source)
                for claim in binding.approved_claim_references
                for source in binding.source_span_references
            )
            reference = binding.generated_claim_reference_id
        else:
            edges = (
                (span, binding.approved_claim_reference, binding.source_reference),
            )
            reference = binding.attribution_realization_id
        for edge in edges:
            if edge in seen:
                issues.append(
                    DomainValidationIssue("duplicate-evidence-edge", reference)
                )
            seen.add(edge)
    return tuple(issues)


def validate_provider_lineage(
    request: ProviderGenerationRequest, response: ProviderGenerationResponse
) -> tuple[DomainValidationIssue, ...]:
    """Validate request-response lineage and response target membership."""
    issues = list(validate_artifact(request)) + list(validate_artifact(response))
    if (
        response.originating_request_identity != request.provider_generation_request_id
        or response.originating_request_fingerprint != request.request_fingerprint
    ):
        issues.append(
            DomainValidationIssue(
                "provider-lineage-mismatch",
                response.provider_generation_response_id,
            )
        )
    segments = set(request.target_segment_references)
    beats = set(request.target_beat_references)
    for unit in response.structured_generated_units:
        if (
            unit.target_segment_reference not in segments
            or unit.target_beat_reference not in beats
        ):
            issues.append(
                DomainValidationIssue(
                    "provider-unit-target-mismatch",
                    unit.provider_generated_unit_id,
                )
            )
    if response.partial_response is not None:
        targets = segments | beats
        partial = response.partial_response
        classified = (
            set(partial.completed_target_references)
            | set(partial.missing_mandatory_target_references)
            | set(partial.missing_optional_target_references)
            | set(partial.rejected_unit_target_references)
        )
        if not classified.issubset(targets):
            issues.append(
                DomainValidationIssue(
                    "partial-target-outside-request",
                    partial.provider_partial_response_id,
                )
            )
        mandatory = {
            reference
            for constraint in request.generation_constraints
            if constraint.mandatory
            for reference in constraint.target_references
            if reference in targets
        }
        if set(partial.missing_mandatory_target_references) - mandatory:
            issues.append(
                DomainValidationIssue(
                    "partial-mandatory-classification-mismatch",
                    partial.provider_partial_response_id,
                )
            )
    if (
        response.execution_status == ProviderExecutionStatus.SUCCESS
        and request.target_beat_references
        and not response.structured_generated_units
    ):
        issues.append(
            DomainValidationIssue(
                "empty-success-response", response.provider_generation_response_id
            )
        )
    segment_positions = {
        reference: position
        for position, reference in enumerate(request.target_segment_references)
    }
    beat_positions = {
        reference: position
        for position, reference in enumerate(request.target_beat_references)
    }
    order = [
        (
            segment_positions.get(item.target_segment_reference, 10**9),
            beat_positions.get(item.target_beat_reference, 10**9),
            item.paragraph_ordinal,
            item.sentence_ordinal,
            item.provider_generated_unit_id,
        )
        for item in response.structured_generated_units
    ]
    if order != sorted(order):
        issues.append(
            DomainValidationIssue(
                "provider-unit-order-mismatch",
                response.provider_generation_response_id,
            )
        )
    return tuple(issues)


def validate_script_unit_identity(
    artifact: ScriptSegment | ScriptBeat | ScriptParagraph | ScriptSentence,
    *,
    composition_plan_fingerprint: str | None = None,
    request_fingerprint: str | None = None,
    composition_segment_reference: str | None = None,
    composition_beat_reference: str | None = None,
    paragraph_ordinal: int | None = None,
) -> tuple[DomainValidationIssue, ...]:
    """Validate a textual unit against the external lineage in its frozen seed."""
    expected: str
    field: str
    if isinstance(artifact, ScriptSegment):
        if composition_plan_fingerprint is None:
            raise ValueError("composition_plan_fingerprint is required")
        expected = script_segment_identity(
            composition_plan_fingerprint,
            artifact.composition_segment_reference,
            artifact.position,
        )
        field = "script_segment_id"
    elif isinstance(artifact, ScriptBeat):
        if (
            composition_plan_fingerprint is None
            or composition_segment_reference is None
        ):
            raise ValueError("composition plan and segment lineage are required")
        expected = script_beat_identity(
            composition_plan_fingerprint,
            composition_segment_reference,
            artifact.composition_beat_reference,
            artifact.beat_position,
        )
        field = "script_beat_id"
    elif isinstance(artifact, ScriptParagraph):
        if request_fingerprint is None or None in {
            composition_segment_reference,
            composition_beat_reference,
        }:
            raise ValueError("request, segment, and beat lineage are required")
        expected = script_paragraph_identity(
            request_fingerprint,
            composition_segment_reference,
            composition_beat_reference,
            artifact.paragraph_position,
        )
        field = "script_paragraph_id"
    else:
        if (
            request_fingerprint is None
            or paragraph_ordinal is None
            or None
            in {
                composition_segment_reference,
                composition_beat_reference,
            }
        ):
            raise ValueError(
                "request, segment, beat, and paragraph lineage are required"
            )
        expected = script_sentence_identity(
            request_fingerprint,
            composition_segment_reference,
            composition_beat_reference,
            paragraph_ordinal,
            artifact.sentence_position,
        )
        field = "script_sentence_id"
    if getattr(artifact, field) == expected:
        return ()
    return (
        DomainValidationIssue(
            "identity-mismatch", _artifact_reference(artifact), field
        ),
    )


def validate_satire_permissions(
    policy: ResolvedGenerationPolicySnapshot,
) -> tuple[DomainValidationIssue, ...]:
    """Detect equally specific contradictory satire permissions."""
    issues: list[DomainValidationIssue] = []
    by_scope: dict[tuple[str, str], list[SatirePermission]] = {}
    for permission in policy.satire_permissions:
        by_scope.setdefault(
            (permission.target_scope.value, permission.target_reference), []
        ).append(permission)
    for permissions in by_scope.values():
        if len({item.permission_state for item in permissions}) > 1:
            issues.append(
                DomainValidationIssue(
                    "contradictory-satire-permission",
                    policy.resolved_generation_policy_id,
                    related_references=tuple(
                        sorted(item.satire_permission_id for item in permissions)
                    ),
                )
            )
    return tuple(issues)


def validate_preserved_units(
    result: RevisionExecutionResult,
    prior_units: dict[str, TextualUnitLineage],
    resulting_units: dict[str, TextualUnitLineage],
) -> tuple[DomainValidationIssue, ...]:
    """Validate preserved identity/fingerprint continuity without executing revision."""
    issues: list[DomainValidationIssue] = []
    for preserved in result.preserved_textual_units:
        before = prior_units.get(preserved.textual_unit_reference)
        after = resulting_units.get(preserved.textual_unit_reference)
        if before != preserved or after != preserved:
            issues.append(
                DomainValidationIssue(
                    "preserved-unit-mismatch",
                    result.revision_execution_result_id,
                    related_references=(preserved.textual_unit_reference,),
                )
            )
    return tuple(issues)


def normalize_provider_status(value: str) -> ProviderExecutionStatus:
    """Normalize unknown external statuses without leaking provider vocabulary."""
    try:
        return ProviderExecutionStatus(value)
    except ValueError:
        return ProviderExecutionStatus.UNKNOWN


def normalize_provider_failure(value: str) -> ProviderFailureReason:
    try:
        return ProviderFailureReason(value)
    except ValueError:
        return ProviderFailureReason.UNKNOWN_PROVIDER_FAILURE


def _expected_identity(artifact):
    if isinstance(artifact, ProviderGenerationRequest):
        return "provider_generation_request_id", provider_request_identity(artifact)
    if isinstance(artifact, ProviderGenerationResponse):
        return "provider_generation_response_id", provider_response_identity(artifact)
    if isinstance(artifact, TextSpanReference):
        return (
            "text_span_id",
            text_span_identity(
                artifact.parent_sentence_reference,
                artifact.start_offset,
                artifact.end_offset,
                artifact.binding_classification,
                artifact.referenced_text,
            ),
        )
    if isinstance(artifact, RevisionRequest):
        return "revision_request_id", revision_request_identity(artifact)
    if isinstance(artifact, RevisionExecutionResult):
        return "revision_execution_result_id", revision_result_identity(artifact)
    return None


def _artifact_reference(artifact: FrozenDomainModel) -> str:
    for name in artifact.__class__.model_fields:
        if name.endswith("_id"):
            return str(getattr(artifact, name))
    return type(artifact).__name__


def _payload_artifact_reference(
    model_type: type[FrozenDomainModel], payload: dict[str, Any]
) -> str:
    for name in model_type.model_fields:
        if name.endswith("_id") and isinstance(payload.get(name), str):
            return payload[name]
    return model_type.__name__


def _local_invariant_violations(artifact: FrozenDomainModel):
    if isinstance(artifact, ProviderGenerationRequest):
        return provider_request_invariant_violations(artifact)
    if isinstance(artifact, ProviderGenerationResponse):
        return provider_response_invariant_violations(artifact)
    if isinstance(artifact, AttributionRealization):
        return attribution_invariant_violations(artifact)
    return ()


__all__ = (
    "DomainValidationError",
    "DomainValidationIssue",
    "construct_artifact",
    "normalize_provider_failure",
    "normalize_provider_status",
    "require_valid_artifact",
    "validate_artifact",
    "validate_preserved_units",
    "validate_provider_lineage",
    "validate_satire_permissions",
    "validate_script_unit_identity",
    "validate_text_span",
    "validate_text_span_bindings",
    "validate_text_span_collection",
)

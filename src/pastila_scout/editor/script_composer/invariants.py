"""Shared pure invariants used by construction and explicit validation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InvariantViolation:
    """Stable local invariant violation independent of model infrastructure."""

    code: str
    field_path: tuple[str | int, ...]


INVARIANT_FIELD_PATHS = {
    "provider-instruction-references-mismatch": ("generation_instruction_references",),
    "provider-constraint-references-mismatch": ("generation_constraint_references",),
    "attribution-span-parent-mismatch": (
        "text_span_reference",
        "parent_sentence_reference",
    ),
    "provider-execution-status-mismatch": ("provider_execution_reference", "status"),
    "provider-execution-lineage-mismatch": (
        "provider_execution_reference",
        "request_fingerprint",
    ),
    "provider-failure-reason-mismatch": (
        "provider_execution_reference",
        "failure_reason",
    ),
    "provider-success-has-partial": ("partial_response",),
    "provider-success-has-failure": ("failure_reason",),
    "provider-success-not-accepted": ("validation_status",),
    "provider-partial-payload-required": ("partial_response",),
    "provider-partial-acceptance-invalid": ("validation_status",),
    "provider-non-partial-has-payload": ("partial_response",),
    "provider-failure-claims-acceptance": ("validation_status",),
    "provider-failure-reason-required": ("failure_reason",),
    "provider-failure-reason-inapplicable": ("failure_reason",),
    "provider-unit-slot-duplicate": ("structured_generated_units",),
}


def provider_request_invariant_violations(request) -> tuple[InvariantViolation, ...]:
    """Return reference/artifact consistency violations for a provider request."""
    issues: list[InvariantViolation] = []
    if set(request.generation_instruction_references) != {
        item.generation_instruction_id for item in request.generation_instructions
    }:
        issues.append(
            InvariantViolation(
                "provider-instruction-references-mismatch",
                ("generation_instruction_references",),
            )
        )
    if set(request.generation_constraint_references) != {
        item.generation_constraint_id for item in request.generation_constraints
    }:
        issues.append(
            InvariantViolation(
                "provider-constraint-references-mismatch",
                ("generation_constraint_references",),
            )
        )
    return tuple(issues)


def attribution_invariant_violations(attribution) -> tuple[InvariantViolation, ...]:
    """Return ownership violations for an attribution realization."""
    if (
        attribution.text_span_reference.parent_sentence_reference
        == attribution.script_sentence_reference
    ):
        return ()
    return (
        InvariantViolation(
            "attribution-span-parent-mismatch",
            INVARIANT_FIELD_PATHS["attribution-span-parent-mismatch"],
        ),
    )


def provider_response_invariant_violations(
    response,
) -> tuple[InvariantViolation, ...]:
    """Return every local provider-response consistency violation."""
    issues: list[InvariantViolation] = []
    execution = response.provider_execution_reference
    status = _value(response.execution_status)
    failure = _value(response.failure_reason)
    validation = _value(response.validation_status)
    if _value(execution.status) != status:
        issues.append(
            InvariantViolation(
                "provider-execution-status-mismatch",
                ("provider_execution_reference", "status"),
            )
        )
    if execution.request_fingerprint != response.originating_request_fingerprint:
        issues.append(
            InvariantViolation(
                "provider-execution-lineage-mismatch",
                ("provider_execution_reference", "request_fingerprint"),
            )
        )
    if _value(execution.failure_reason) != failure:
        issues.append(
            InvariantViolation(
                "provider-failure-reason-mismatch",
                ("provider_execution_reference", "failure_reason"),
            )
        )
    if status == "success":
        if response.partial_response is not None:
            issues.append(
                InvariantViolation(
                    "provider-success-has-partial", ("partial_response",)
                )
            )
        if failure != "none":
            issues.append(
                InvariantViolation("provider-success-has-failure", ("failure_reason",))
            )
        if validation != "accepted":
            issues.append(
                InvariantViolation(
                    "provider-success-not-accepted", ("validation_status",)
                )
            )
    elif status == "partial":
        if response.partial_response is None:
            issues.append(
                InvariantViolation(
                    "provider-partial-payload-required", ("partial_response",)
                )
            )
        if validation not in {"accepted_partial", "rejected"}:
            issues.append(
                InvariantViolation(
                    "provider-partial-acceptance-invalid", ("validation_status",)
                )
            )
    else:
        if response.partial_response is not None:
            issues.append(
                InvariantViolation(
                    "provider-non-partial-has-payload", ("partial_response",)
                )
            )
        if validation in {"accepted", "accepted_partial"}:
            issues.append(
                InvariantViolation(
                    "provider-failure-claims-acceptance", ("validation_status",)
                )
            )
        if failure == "none":
            issues.append(
                InvariantViolation(
                    "provider-failure-reason-required", ("failure_reason",)
                )
            )
        expected = {
            "unavailable": "provider_unavailable",
            "timeout": "timeout",
            "retry_exhausted": "retry_exhausted",
            "malformed_response": "malformed_payload",
            "schema_mismatch": "schema_validation_failed",
            "lineage_mismatch": "lineage_validation_failed",
            "unknown": "unknown_provider_failure",
        }.get(status)
        if expected is not None and failure != expected:
            issues.append(
                InvariantViolation(
                    "provider-failure-reason-inapplicable", ("failure_reason",)
                )
            )
    slots = [
        (
            item.target_segment_reference,
            item.target_beat_reference,
            item.paragraph_ordinal,
            item.sentence_ordinal,
            _value(item.unit_kind),
        )
        for item in response.structured_generated_units
    ]
    if len(slots) != len(set(slots)):
        issues.append(
            InvariantViolation(
                "provider-unit-slot-duplicate", ("structured_generated_units",)
            )
        )
    return tuple(issues)


def _value(value):
    return getattr(value, "value", value)


__all__ = (
    "INVARIANT_FIELD_PATHS",
    "InvariantViolation",
    "attribution_invariant_violations",
    "provider_request_invariant_violations",
    "provider_response_invariant_violations",
)

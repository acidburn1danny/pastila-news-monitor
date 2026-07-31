"""Derived readiness for editorial composition plans."""

from .models import (
    CompositionInputBundle,
    CompositionReadiness,
    CompositionValidationFinding,
    FindingSeverity,
)


def derive_readiness(
    bundle: CompositionInputBundle,
    findings: tuple[CompositionValidationFinding, ...],
) -> CompositionReadiness:
    """Derive readiness using the frozen precedence contract."""
    dependency_states = {item.readiness for item in bundle.upstream_dependencies}
    if CompositionReadiness.BLOCKED in dependency_states or any(
        item.blocking or item.severity == FindingSeverity.ERROR for item in findings
    ):
        return CompositionReadiness.BLOCKED
    if CompositionReadiness.REQUIRES_EDITOR_REVIEW in dependency_states or any(
        item.editor_review_required for item in findings
    ):
        return CompositionReadiness.REQUIRES_EDITOR_REVIEW
    if CompositionReadiness.READY_WITH_ADVISORIES in dependency_states or any(
        item.severity in {FindingSeverity.WARNING, FindingSeverity.ADVISORY}
        for item in findings
    ):
        return CompositionReadiness.READY_WITH_ADVISORIES
    return CompositionReadiness.READY


__all__ = ("derive_readiness",)

"""Canonical identities and fingerprints for Phase 4.3 composition."""

from .canonical import semantic_fingerprint
from .identity import derive_identity
from .section_composition_models import (
    ComposedSection,
    DraftSectionCompositionPlan,
    SectionCompositionDomainModel,
)


def _semantic_payload(
    value: SectionCompositionDomainModel, *, exclude_fingerprint: bool
) -> dict:
    excluded = {"fingerprint"} if exclude_fingerprint else set()
    payload = value.model_dump(mode="python", exclude=excluded, warnings=False)
    if isinstance(value, ComposedSection):
        payload["composed_claims"] = {
            str(index): claim for index, claim in enumerate(value.composed_claims)
        }
    elif isinstance(value, DraftSectionCompositionPlan):
        payload["composed_sections"] = {
            str(index): section for index, section in enumerate(value.composed_sections)
        }
    return payload


def _identity(kind: str, value: SectionCompositionDomainModel) -> str:
    payload = _semantic_payload(value, exclude_fingerprint=True)
    payload.pop("identity", None)
    return derive_identity(kind, payload)


def compute_composed_claim_identity(value: SectionCompositionDomainModel) -> str:
    """Return the deterministic identity of one composed claim."""

    return _identity("composed-claim", value)


def compute_composed_section_identity(value: SectionCompositionDomainModel) -> str:
    """Return the deterministic identity of one composed section."""

    return _identity("composed-section", value)


def compute_draft_section_composition_plan_identity(
    value: SectionCompositionDomainModel,
) -> str:
    """Return the deterministic identity of one composition plan."""

    return _identity("draft-section-composition-plan", value)


def section_composition_fingerprint(value: SectionCompositionDomainModel) -> str:
    """Return a canonical SHA-256 seal excluding only the seal itself."""

    return semantic_fingerprint(_semantic_payload(value, exclude_fingerprint=True))


compute_composed_claim_fingerprint = section_composition_fingerprint
compute_composed_section_fingerprint = section_composition_fingerprint
compute_draft_section_composition_plan_fingerprint = section_composition_fingerprint


__all__ = (
    "compute_composed_claim_fingerprint",
    "compute_composed_claim_identity",
    "compute_composed_section_fingerprint",
    "compute_composed_section_identity",
    "compute_draft_section_composition_plan_fingerprint",
    "compute_draft_section_composition_plan_identity",
)

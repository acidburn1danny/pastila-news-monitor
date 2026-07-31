"""Deterministic identities for Module 2.9 Phase 4.1 draft artifacts."""

from .draft_models import _draft_semantic_payload
from .identity import derive_identity


def _identity(kind: str, value) -> str:
    payload = _draft_semantic_payload(value, exclude_fingerprint=True)
    payload.pop("identity", None)
    return derive_identity(kind, payload)


def draft_structure_identity(value) -> str:
    """Return the canonical identity for a draft structure."""

    return _identity("draft-structure", value)


def draft_section_identity(value) -> str:
    """Return the canonical identity for a draft section."""

    return _identity("draft-section", value)


def transition_slot_identity(value) -> str:
    """Return the canonical identity for a transition slot."""

    return _identity("draft-transition", value)


__all__ = (
    "draft_section_identity",
    "draft_structure_identity",
    "transition_slot_identity",
)

"""Deterministic identities for Module 2.9 Phase 4.2 claim bindings."""

from .claim_binding_models import _claim_binding_semantic_payload
from .identity import derive_identity


def _identity(kind: str, value) -> str:
    payload = _claim_binding_semantic_payload(value, exclude_fingerprint=True)
    payload.pop("identity", None)
    return derive_identity(kind, payload)


def claim_binding_identity(value) -> str:
    """Return the canonical identity for one claim binding."""

    return _identity("claim-binding", value)


def section_claim_binding_set_identity(value) -> str:
    """Return the canonical identity for one section binding set."""

    return _identity("section-claim-binding-set", value)


def draft_claim_binding_plan_identity(value) -> str:
    """Return the canonical identity for one draft binding plan."""

    return _identity("draft-claim-binding-plan", value)


__all__ = (
    "claim_binding_identity",
    "draft_claim_binding_plan_identity",
    "section_claim_binding_set_identity",
)

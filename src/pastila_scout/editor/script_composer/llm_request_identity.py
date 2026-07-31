"""Canonical identities and fingerprints for Phase 5.1 semantic requests."""

from .canonical import semantic_fingerprint
from .identity import derive_identity
from .llm_request_models import (
    DraftLLMRequestPlan,
    LLMRequestDomainModel,
    LLMRequestSection,
)


def _semantic_payload(value: LLMRequestDomainModel, *, exclude_fingerprint: bool):
    excluded = {"fingerprint"} if exclude_fingerprint else set()
    payload = value.model_dump(mode="python", exclude=excluded, warnings=False)
    if isinstance(value, LLMRequestSection):
        payload["request_claims"] = {
            str(index): claim for index, claim in enumerate(value.request_claims)
        }
    elif isinstance(value, DraftLLMRequestPlan):
        payload["request_sections"] = {
            str(index): section for index, section in enumerate(value.request_sections)
        }
    return payload


def _identity(kind: str, value: LLMRequestDomainModel) -> str:
    payload = _semantic_payload(value, exclude_fingerprint=True)
    payload.pop("identity", None)
    return derive_identity(kind, payload)


def derive_llm_request_claim_identity(value: LLMRequestDomainModel) -> str:
    """Return the deterministic identity for one request claim."""

    return _identity("llm-request-claim", value)


def derive_llm_request_section_identity(value: LLMRequestDomainModel) -> str:
    """Return the deterministic identity for one request section."""

    return _identity("llm-request-section", value)


def derive_draft_llm_request_plan_identity(value: LLMRequestDomainModel) -> str:
    """Return the deterministic identity for one request plan."""

    return _identity("draft-llm-request-plan", value)


def llm_request_fingerprint(value: LLMRequestDomainModel) -> str:
    """Return the canonical SHA-256 seal excluding only the seal itself."""

    return semantic_fingerprint(_semantic_payload(value, exclude_fingerprint=True))


derive_llm_request_claim_fingerprint = llm_request_fingerprint
derive_llm_request_section_fingerprint = llm_request_fingerprint
derive_draft_llm_request_plan_fingerprint = llm_request_fingerprint


__all__ = (
    "derive_draft_llm_request_plan_fingerprint",
    "derive_draft_llm_request_plan_identity",
    "derive_llm_request_claim_fingerprint",
    "derive_llm_request_claim_identity",
    "derive_llm_request_section_fingerprint",
    "derive_llm_request_section_identity",
)

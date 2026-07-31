"""Deterministic identities and fingerprints for Phase 6.1."""

from .canonical import semantic_fingerprint
from .identity import derive_identity
from .llm_execution_models import (
    DraftLLMExecutionPlan,
    LLMExecutionDomainModel,
    LLMExecutionMessage,
    LLMExecutionRequest,
)


def _semantic_payload(value: LLMExecutionDomainModel, *, exclude_fingerprint: bool):
    excluded = {"fingerprint"} if exclude_fingerprint else set()
    payload = value.model_dump(mode="python", exclude=excluded, warnings=False)
    if isinstance(value, LLMExecutionRequest):
        payload["execution_messages"] = {
            str(index): message
            for index, message in enumerate(value.execution_messages)
        }
    elif isinstance(value, DraftLLMExecutionPlan):
        payload["execution_requests"] = {
            str(index): request
            for index, request in enumerate(value.execution_requests)
        }
    return payload


def _identity(kind: str, value: LLMExecutionDomainModel) -> str:
    payload = _semantic_payload(value, exclude_fingerprint=True)
    payload.pop("identity", None)
    return derive_identity(kind, payload)


def llm_execution_fingerprint(value: LLMExecutionDomainModel) -> str:
    """Return the canonical semantic SHA-256 fingerprint for an artifact."""

    return semantic_fingerprint(_semantic_payload(value, exclude_fingerprint=True))


def derive_llm_execution_message_identity(value: LLMExecutionMessage) -> str:
    """Derive one execution-message identity from all semantic fields."""

    return _identity("llm-execution-message", value)


def derive_llm_execution_request_identity(value: LLMExecutionRequest) -> str:
    """Derive one execution-request identity from all semantic fields."""

    return _identity("llm-execution-request", value)


def derive_draft_llm_execution_plan_identity(value: DraftLLMExecutionPlan) -> str:
    """Derive one execution-plan identity from all semantic fields."""

    return _identity("draft-llm-execution-plan", value)


def derive_llm_execution_message_fingerprint(value: LLMExecutionMessage) -> str:
    """Derive one execution-message semantic fingerprint."""

    return llm_execution_fingerprint(value)


def derive_llm_execution_request_fingerprint(value: LLMExecutionRequest) -> str:
    """Derive one execution-request semantic fingerprint."""

    return llm_execution_fingerprint(value)


def derive_draft_llm_execution_plan_fingerprint(value: DraftLLMExecutionPlan) -> str:
    """Derive one execution-plan semantic fingerprint."""

    return llm_execution_fingerprint(value)


__all__ = (
    "derive_draft_llm_execution_plan_fingerprint",
    "derive_draft_llm_execution_plan_identity",
    "derive_llm_execution_message_fingerprint",
    "derive_llm_execution_message_identity",
    "derive_llm_execution_request_fingerprint",
    "derive_llm_execution_request_identity",
)

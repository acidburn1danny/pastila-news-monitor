"""Canonical identities and fingerprints for Phase 5.2 prompt renderings."""

from .canonical import semantic_fingerprint
from .identity import derive_identity
from .prompt_rendering_models import (
    DraftRenderedPromptPlan,
    RenderedPromptDomainModel,
    RenderedPromptSection,
)


def _semantic_payload(value: RenderedPromptDomainModel, *, exclude_fingerprint: bool):
    excluded = {"fingerprint"} if exclude_fingerprint else set()
    payload = value.model_dump(mode="python", exclude=excluded, warnings=False)
    if isinstance(value, RenderedPromptSection):
        payload["rendered_messages"] = {
            str(index): message for index, message in enumerate(value.rendered_messages)
        }
    elif isinstance(value, DraftRenderedPromptPlan):
        payload["rendered_sections"] = {
            str(index): section for index, section in enumerate(value.rendered_sections)
        }
    return payload


def _identity(kind: str, value: RenderedPromptDomainModel) -> str:
    payload = _semantic_payload(value, exclude_fingerprint=True)
    payload.pop("identity", None)
    return derive_identity(kind, payload)


def derive_rendered_prompt_message_identity(value: RenderedPromptDomainModel) -> str:
    """Return the deterministic identity for one rendered message."""

    return _identity("rendered-prompt-message", value)


def derive_rendered_prompt_section_identity(value: RenderedPromptDomainModel) -> str:
    """Return the deterministic identity for one rendered section."""

    return _identity("rendered-prompt-section", value)


def derive_draft_rendered_prompt_plan_identity(
    value: RenderedPromptDomainModel,
) -> str:
    """Return the deterministic identity for one rendered plan."""

    return _identity("draft-rendered-prompt-plan", value)


def rendered_prompt_fingerprint(value: RenderedPromptDomainModel) -> str:
    """Return the canonical SHA-256 seal excluding only the seal itself."""

    return semantic_fingerprint(_semantic_payload(value, exclude_fingerprint=True))


derive_rendered_prompt_message_fingerprint = rendered_prompt_fingerprint
derive_rendered_prompt_section_fingerprint = rendered_prompt_fingerprint
derive_draft_rendered_prompt_plan_fingerprint = rendered_prompt_fingerprint


__all__ = (
    "derive_draft_rendered_prompt_plan_fingerprint",
    "derive_draft_rendered_prompt_plan_identity",
    "derive_rendered_prompt_message_fingerprint",
    "derive_rendered_prompt_message_identity",
    "derive_rendered_prompt_section_fingerprint",
    "derive_rendered_prompt_section_identity",
)

"""Opt-in provider-neutral AI boundary for event-candidate verification."""

from .composition import compose_event_verification_provider
from .prompt import build_event_verification_task, serialize_event_verification_task
from .provider import ProviderNeutralEventVerificationProviderV1

__all__ = (
    "ProviderNeutralEventVerificationProviderV1",
    "build_event_verification_task",
    "compose_event_verification_provider",
    "serialize_event_verification_task",
)

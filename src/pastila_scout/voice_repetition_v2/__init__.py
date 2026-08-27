"""Authoritative Voice V2 repetition and atomic acceptance."""

from .ledger import (
    VoiceRepetitionIntegrityError,
    derive_repetition_snapshot_v1,
    effective_uses_v1,
    finalize_ledger_v1,
    finalize_order_authority_v1,
)
from .models import *

_ACCEPTANCE_EXPORTS = {
    "SimulatedAcceptanceCrash",
    "VoiceAcceptanceIntegrityError",
    "VoiceAtomicAcceptanceStoreV1",
    "finalize_acceptance_request_v1",
    "finalize_candidate_v1",
}
_LIFECYCLE_EXPORTS = {
    "publish_episode_uses_v1",
    "remove_unpublished_commentary_v1",
}


def __getattr__(name: str):
    if name in _ACCEPTANCE_EXPORTS:
        from . import acceptance

        return getattr(acceptance, name)
    if name in _LIFECYCLE_EXPORTS:
        from . import lifecycle

        return getattr(lifecycle, name)
    raise AttributeError(name)

__all__ = [
    "SimulatedAcceptanceCrash",
    "VoiceAcceptanceIntegrityError",
    "VoiceAtomicAcceptanceStoreV1",
    "VoiceRepetitionIntegrityError",
    "derive_repetition_snapshot_v1",
    "effective_uses_v1",
    "finalize_acceptance_request_v1",
    "finalize_candidate_v1",
    "finalize_ledger_v1",
    "finalize_order_authority_v1",
    "publish_episode_uses_v1",
    "remove_unpublished_commentary_v1",
]

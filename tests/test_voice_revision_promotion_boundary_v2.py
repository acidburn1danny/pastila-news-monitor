from types import SimpleNamespace

import pytest

from pastila_scout.voice_canonical_state_v2 import (
    CanonicalVoiceLifecycleV2,
    CanonicalVoicePersistenceError,
)
from pastila_scout.voice_revision_promotion_v2 import AcceptedVoiceRevisionPromoterV2


class _MissingProjectStore:
    def load(self):
        return None


def test_promotion_rejects_nonterminal_voice_revision_before_project_mutation(tmp_path):
    promoter = AcceptedVoiceRevisionPromoterV2(
        project_store=_MissingProjectStore(), root=tmp_path
    )
    state = SimpleNamespace(lifecycle=CanonicalVoiceLifecycleV2.ELIGIBILITY_AVAILABLE)

    with pytest.raises(CanonicalVoicePersistenceError, match="nonterminal"):
        promoter.promote(state, expected_source_revision_identity="sha256:source")


def test_terminal_promotion_fails_closed_when_active_project_is_missing(tmp_path):
    promoter = AcceptedVoiceRevisionPromoterV2(
        project_store=_MissingProjectStore(), root=tmp_path
    )
    state = SimpleNamespace(lifecycle=CanonicalVoiceLifecycleV2.ACCEPTED_COMMENTARY)

    with pytest.raises(CanonicalVoicePersistenceError, match="unavailable"):
        promoter.promote(state, expected_source_revision_identity="sha256:source")

from datetime import UTC, datetime

import pytest

from pastila_scout.desktop_v1.voice_adjudication_actions import (
    VoiceDesktopAdjudicationActionV1,
)
from pastila_scout.desktop_v1.voice_adjudication_workflow import (
    VoiceDesktopAdjudicationCoordinatorV1,
)
from pastila_scout.voice_adjudication_v2 import VoiceAdjudicationError


class _MissingStore:
    def load(self, event_id):
        return None


class _Service:
    store = _MissingStore()


def test_desktop_adjudication_fails_closed_without_persisted_owner_state():
    action = VoiceDesktopAdjudicationActionV1(
        event_id=7,
        action="finalize_facts",
        owner_identity="desktop-owner",
        occurred_at=datetime(2026, 8, 27, tzinfo=UTC),
    )

    with pytest.raises(VoiceAdjudicationError, match="unavailable"):
        VoiceDesktopAdjudicationCoordinatorV1(_Service()).dispatch(action)

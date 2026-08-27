from pastila_scout.voice_ordinary_bootstrap_v2 import (
    OrdinaryPersistedStoryVoiceBootstrapV2,
    OrdinaryVoiceBootstrapStatusV2,
)


class _MissingProjectStore:
    def load(self):
        return None


class _UnusedCanonicalStore:
    pass


class _UnusedAdjudication:
    pass


def test_missing_persisted_story_fails_closed_without_execution():
    bootstrap = OrdinaryPersistedStoryVoiceBootstrapV2(
        project_store=_MissingProjectStore(),
        canonical_store=_UnusedCanonicalStore(),
        adjudication=_UnusedAdjudication(),
    )

    result = bootstrap.reevaluate(17)

    assert result.event_id == 17
    assert result.status is OrdinaryVoiceBootstrapStatusV2.INTEGRITY_FAILURE
    assert result.diagnostic_code == "active_project_missing"
    assert result.state_identity is None

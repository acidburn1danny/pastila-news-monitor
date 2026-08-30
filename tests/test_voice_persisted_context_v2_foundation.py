from __future__ import annotations

import sys

from pastila_scout.voice_canonical_state_v2 import CanonicalVoiceWorkspaceStoreV2
from pastila_scout.voice_governed_context_v2 import VoiceGovernedContextV2
from pastila_scout.voice_persisted_context_v2 import (
    PersistedStoryGovernedContextLoaderV2,
)


def test_empty_persisted_loader_is_desktop_neutral_and_non_executing(tmp_path) -> None:
    workflow_was_loaded = "pastila_scout.desktop_v1.voice_v2_workflow" in sys.modules
    activation_was_loaded = (
        "pastila_scout.voice_executor_v2.production_activation" in sys.modules
    )

    project = (tmp_path / "episode.pastila").resolve()
    project.write_text("{}", encoding="utf-8")
    store = CanonicalVoiceWorkspaceStoreV2(
        project_path=project, project_identity="project:synthetic"
    )
    loader = PersistedStoryGovernedContextLoaderV2(store)

    assert loader.load(101) is None
    assert (
        "pastila_scout.desktop_v1.voice_v2_workflow" in sys.modules
    ) is workflow_was_loaded
    assert (
        "pastila_scout.voice_executor_v2.production_activation" in sys.modules
    ) is activation_was_loaded
    assert not hasattr(VoiceGovernedContextV2, "execute")

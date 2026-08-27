from __future__ import annotations

from pastila_scout.desktop_v1.voice_v2_workflow import (
    VoiceDesktopContextRegistryV2,
    VoiceDesktopGovernedContextV2,
)
from pastila_scout.voice_governed_context_v2 import VoiceGovernedContextV2


def test_desktop_context_is_exact_neutral_contract_alias() -> None:
    assert VoiceDesktopGovernedContextV2 is VoiceGovernedContextV2
    registry = VoiceDesktopContextRegistryV2()
    assert registry.load(101) is None

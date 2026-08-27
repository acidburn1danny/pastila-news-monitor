from __future__ import annotations

import sys

from pastila_scout.voice_executor_v2 import (
    RENDERER_IDENTITY,
    ZERO_ACTIVATION_POLICY_V1,
    DeterministicVoiceExecutorV2,
)


def test_zero_activation_executor_is_importable_without_production_binding() -> None:
    assert "pastila_scout.voice_deterministic_v2.production_renderer" not in sys.modules
    assert "pastila_scout.voice_executor_v2.production_activation" not in sys.modules

    executor = DeterministicVoiceExecutorV2(
        activation_policy=ZERO_ACTIVATION_POLICY_V1
    )
    capability = executor.inspect_capability()

    assert capability.renderer_identity == RENDERER_IDENTITY
    assert capability.model_calls == 0
    assert capability.provider_calls == 0
    assert capability.model_loads == 0
    assert ZERO_ACTIVATION_POLICY_V1.active_expression_count == 0
    assert ZERO_ACTIVATION_POLICY_V1.active_surface_count == 0

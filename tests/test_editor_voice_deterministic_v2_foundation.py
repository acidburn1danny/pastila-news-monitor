from __future__ import annotations

from pastila_scout.editor_voice_deterministic_v2 import (
    EditorDeterministicVoiceApplicationServiceV2,
    EditorDeterministicVoiceStateV2,
)
from pastila_scout.voice_eligibility_v2.engine import _sealed
from pastila_scout.voice_eligibility_v2.models import VoiceEligibilityResultV1
from pastila_scout.voice_executor_v2 import ZERO_ACTIVATION_POLICY_V1


ZERO = "sha256:" + "0" * 64


class StaticExecutor:
    def inspect_capability(self):
        from pastila_scout.voice_executor_v2 import DeterministicVoiceExecutorV2

        return DeterministicVoiceExecutorV2(
            activation_policy=ZERO_ACTIVATION_POLICY_V1
        ).inspect_capability()

    def execute(self, _request):
        raise AssertionError("foundation verification must not execute")


def test_empty_eligibility_presents_safe_no_program_without_execution() -> None:
    provisional = VoiceEligibilityResultV1(
        fact_atom_bundle_identity="sha256:" + "1" * 64,
        repetition_snapshot_identity="sha256:" + "2" * 64,
        mechanic_outcomes=(),
        program_outcomes=(),
        shortlist=(),
        result_identity=ZERO,
    )
    result = provisional.model_copy(
        update={"result_identity": _sealed(provisional, "result_identity")}
    )
    service = EditorDeterministicVoiceApplicationServiceV2(
        executor=StaticExecutor(), activation_policy=ZERO_ACTIVATION_POLICY_V1
    )

    interaction = service.present_programs(result)
    assert interaction.state is EditorDeterministicVoiceStateV2.NO_ELIGIBLE_PROGRAM
    assert interaction.acceptance_enabled is False

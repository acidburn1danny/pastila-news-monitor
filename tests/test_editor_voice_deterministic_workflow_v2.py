from __future__ import annotations

from datetime import UTC, datetime

from pastila_scout.desktop_v1.voice_v2_composition import compose_voice_v2_production
from pastila_scout.editor_voice_deterministic_v2 import (
    EditorDeterministicVoiceApplicationServiceV2,
    EditorDeterministicVoiceStateV2,
)
from pastila_scout.expression_catalog_v2.eligibility import _sealed as expression_sealed
from pastila_scout.expression_catalog_v2.eligibility_models import (
    CommentaryRelationshipV1,
    ExpressionCandidateV1,
    ExpressionEligibilityResultV1,
    ExpressionSelectionKindV1,
)
from pastila_scout.voice_deterministic_v2.models import MechanicIdV1
from pastila_scout.voice_eligibility_v2.engine import (
    _sealed as voice_sealed,
)
from pastila_scout.voice_eligibility_v2.engine import (
    finalize_repetition_snapshot,
)
from pastila_scout.voice_eligibility_v2.models import (
    ZERO_IDENTITY,
    ProgramCandidateV1,
    SelectionKindV1,
    VoiceEligibilityResultV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_executor_v2 import (
    ZERO_ACTIVATION_POLICY_V1,
    DeterministicVoiceExecutorV2,
)

SHA = "sha256:" + "1" * 64
NOW = datetime(2026, 8, 23, tzinfo=UTC)


def _snapshot():
    return finalize_repetition_snapshot(
        VoiceRepetitionSnapshotV1(
            current_episode_ordinal=1,
            current_story_position=1,
            snapshot_identity=ZERO_IDENTITY,
        )
    )


def _program_result(snapshot):
    candidate = ProgramCandidateV1(
        candidate_id=SHA,
        program_id="NUMERIC_EXPECTATION_LADDER_PROGRAM_01_V1",
        mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
        cadence_signature="cadence",
        surface_ids=(),
        repetition_signature="signature",
    )
    provisional = VoiceEligibilityResultV1(
        fact_atom_bundle_identity=SHA,
        repetition_snapshot_identity=snapshot.snapshot_identity,
        mechanic_outcomes=(),
        program_outcomes=(),
        shortlist=(candidate,),
        result_identity=ZERO_IDENTITY,
    )
    return provisional.model_copy(
        update={"result_identity": voice_sealed(provisional, "result_identity")}
    )


def _service():
    executor = DeterministicVoiceExecutorV2(activation_policy=ZERO_ACTIVATION_POLICY_V1)
    return EditorDeterministicVoiceApplicationServiceV2(
        executor=executor, activation_policy=ZERO_ACTIVATION_POLICY_V1
    )


def test_program_selection_and_none_create_separate_finalized_receipts() -> None:
    service, snapshot = _service(), _snapshot()
    result = _program_result(snapshot)
    presentation = service.present_programs(result)

    assert (
        presentation.state is EditorDeterministicVoiceStateV2.PROGRAM_SELECTION_REQUIRED
    )
    assert presentation.choices[-1].label == "Fără comentariu"
    selected = service.select_program(
        result=result,
        snapshot=snapshot,
        candidate_identity=SHA,
        owner_identity="owner",
        selected_at=NOW,
    )
    omitted = service.select_program(
        result=result,
        snapshot=snapshot,
        candidate_identity=None,
        owner_identity="owner",
        selected_at=NOW,
    )
    assert selected.selection_kind is SelectionKindV1.PROGRAM
    assert omitted.selection_kind is SelectionKindV1.NONE
    assert selected.receipt_identity != omitted.receipt_identity


def test_zero_activation_hides_even_proof_approved_expression() -> None:
    service, snapshot = _service(), _snapshot()
    program = _program_result(snapshot)
    candidate = ExpressionCandidateV1(
        candidate_id=SHA,
        expression_id="ro-expression-v1:2e5417acdb78ee504d4b",
        expression_family_identity="family",
        relationship=CommentaryRelationshipV1.DELAYED_ACTION_AFTER_OUTCOME,
        relation_binding_identity=SHA,
        selected_program_candidate_id=SHA,
        surface_id="surface",
        exact_surface="Suprafață aprobată în dovadă.",
        surface_utf8_sha256="1" * 64,
        repetition_identity="repetition",
    )
    provisional = ExpressionEligibilityResultV1(
        fact_atom_bundle_identity=SHA,
        program_eligibility_result_identity=program.result_identity,
        repetition_snapshot_identity=snapshot.snapshot_identity,
        outcomes=(),
        shortlist=(candidate,),
    )
    result = provisional.model_copy(
        update={"result_identity": expression_sealed(provisional, "result_identity")}
    )
    presentation = service.present_expressions(result)
    receipt = service.select_expression(
        result=result,
        snapshot=snapshot,
        candidate_identity=None,
        owner_identity="owner",
        selected_at=NOW,
    )

    assert presentation.state is EditorDeterministicVoiceStateV2.NO_ELIGIBLE_EXPRESSION
    assert [item.label for item in presentation.choices] == ["Fără expresie"]
    assert receipt.selection_kind is ExpressionSelectionKindV1.NONE


def test_production_composition_is_v2_model_free_and_zero_active() -> None:
    composition = compose_voice_v2_production()
    capability = composition.executor.inspect_capability()

    assert capability.backend_kind == "deterministic_renderer"
    assert (
        capability.model_calls
        == capability.provider_calls
        == capability.model_loads
        == 0
    )
    assert ZERO_ACTIVATION_POLICY_V1.active_expression_count == 0
    assert ZERO_ACTIVATION_POLICY_V1.active_surface_count == 0

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.desktop_v1.voice_v2_composition import compose_voice_v2_production
from pastila_scout.desktop_v1.voice_v2_interaction import VoiceDesktopActionInputV2
from pastila_scout.desktop_v1.voice_v2_workflow import (
    VoiceDesktopGovernedContextV2,
    VoiceDesktopWorkflowCoordinatorV2,
)
from pastila_scout.expression_catalog_v2.eligibility import (
    _sealed as expression_sealed,
)
from pastila_scout.expression_catalog_v2.eligibility import (
    finalize_expression_selection_receipt,
)
from pastila_scout.expression_catalog_v2.eligibility_models import (
    ExpressionEligibilityResultV1,
    ExpressionOwnerSelectionReceiptV1,
    ExpressionSelectionKindV1,
)
from pastila_scout.voice_deterministic_v2 import (
    FROZEN_PROOF_CASES_V1,
    build_frozen_realization_ir,
)
from pastila_scout.voice_eligibility_v2.engine import (
    _sealed as voice_sealed,
)
from pastila_scout.voice_eligibility_v2.engine import (
    finalize_repetition_snapshot,
    finalize_selection_receipt,
)
from pastila_scout.voice_eligibility_v2.models import (
    ZERO_IDENTITY,
    ProgramCandidateV1,
    SelectionKindV1,
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_executor_v2 import (
    FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1,
    RENDERER_IDENTITY,
    ZERO_ACTIVATION_POLICY_V1,
    DeterministicVoiceExecutorV2,
    ProofOnlyDeterministicVoiceExecutorV2,
    VoiceDeterministicPreviewSidecarStoreV2,
    build_preview_sidecar_v2,
    finalize_request_v2,
)
from pastila_scout.voice_executor_v2.models import (
    DeterministicTerminalKindV2,
    VoiceDeterministicExecutionRequestV2,
)
from pastila_scout.voice_fact_atoms_v2 import (
    VoiceFactAtomBundleV1,
    finalize_bundle_identity,
)
from pastila_scout.voice_workflow_v2.models import VoiceStoryBindingV1

SHA = "sha256:" + "1" * 64
NOW = datetime(2026, 8, 23, tzinfo=UTC)
EVIDENCE = Path("tests/fixtures/voice_deterministic_v2/frozen_proof_cases")


def _base(*, selected: bool, expression_none: bool = False):
    binding = VoiceStoryBindingV1(
        story_material_reference="story:1",
        semantic_draft_revision_identity=SHA,
        event_id=1,
        factual_summary_sha256=SHA,
        event_authority_identity=SHA,
    )
    bundle = finalize_bundle_identity(
        VoiceFactAtomBundleV1(
            revision=1,
            semantic_draft_revision_identity=SHA,
            event_id=1,
            story_position=1,
            factual_summary_identity=SHA,
            event_authority_identity=SHA,
            candidates=(),
            atoms=(),
            bundle_identity=ZERO_IDENTITY,
        )
    )
    snapshot = finalize_repetition_snapshot(
        VoiceRepetitionSnapshotV1(
            current_episode_ordinal=1,
            current_story_position=1,
            snapshot_identity=ZERO_IDENTITY,
        )
    )
    case = FROZEN_PROOF_CASES_V1["P1"]
    candidate = ProgramCandidateV1(
        candidate_id=SHA,
        program_id=case.realization_program_id,
        mechanic_id=case.mechanic_id,
        cadence_signature="cadence",
        surface_ids=(),
        repetition_signature="signature",
    )
    provisional = VoiceEligibilityResultV1(
        fact_atom_bundle_identity=bundle.bundle_identity,
        repetition_snapshot_identity=snapshot.snapshot_identity,
        mechanic_outcomes=(),
        program_outcomes=(),
        shortlist=(candidate,),
        result_identity=ZERO_IDENTITY,
    )
    eligibility = provisional.model_copy(
        update={"result_identity": voice_sealed(provisional, "result_identity")}
    )
    receipt = finalize_selection_receipt(
        VoiceOwnerSelectionReceiptV1(
            fact_atom_bundle_identity=bundle.bundle_identity,
            eligibility_result_identity=eligibility.result_identity,
            repetition_snapshot_identity=snapshot.snapshot_identity,
            shortlist_candidate_ids=(candidate.candidate_id,),
            selection_kind=(
                SelectionKindV1.PROGRAM if selected else SelectionKindV1.NONE
            ),
            selected_candidate_id=(candidate.candidate_id if selected else None),
            selector_identity="owner",
            selected_at=NOW,
            receipt_identity=ZERO_IDENTITY,
        ),
        result=eligibility,
        snapshot=snapshot,
    )
    expression_result = expression_receipt = None
    if expression_none:
        provisional_expression = ExpressionEligibilityResultV1(
            fact_atom_bundle_identity=bundle.bundle_identity,
            program_eligibility_result_identity=eligibility.result_identity,
            repetition_snapshot_identity=snapshot.snapshot_identity,
            outcomes=(),
            shortlist=(),
        )
        expression_result = provisional_expression.model_copy(
            update={
                "result_identity": expression_sealed(
                    provisional_expression, "result_identity"
                )
            }
        )
        expression_receipt = finalize_expression_selection_receipt(
            ExpressionOwnerSelectionReceiptV1(
                fact_atom_bundle_identity=bundle.bundle_identity,
                expression_eligibility_result_identity=expression_result.result_identity,
                repetition_snapshot_identity=snapshot.snapshot_identity,
                shortlist_candidate_ids=(),
                selection_kind=ExpressionSelectionKindV1.NONE,
                selector_identity="owner",
                selected_at=NOW,
            ),
            result=expression_result,
            snapshot=snapshot,
        )
    request = VoiceDeterministicExecutionRequestV2(
        story_binding=binding,
        fact_atom_bundle=bundle,
        program_eligibility=eligibility,
        program_selection=receipt,
        expression_eligibility=expression_result,
        expression_selection=expression_receipt,
        repetition_snapshot=snapshot,
        activation_policy=ZERO_ACTIVATION_POLICY_V1,
        proof_activation_authority=(
            FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1 if selected else None
        ),
        expected_renderer_identity=RENDERER_IDENTITY,
        ir=(build_frozen_realization_ir("P1", EVIDENCE) if selected else None),
    )
    return finalize_request_v2(request)


def test_v2_capability_is_truthful_model_free_and_coexists_with_v1() -> None:
    from pastila_scout.editor_voice_application_v2 import UnavailableVoiceExecutorV1

    capability = DeterministicVoiceExecutorV2(
        activation_policy=ZERO_ACTIVATION_POLICY_V1
    ).inspect_capability()

    assert capability.backend_kind == "deterministic_renderer"
    assert (
        capability.model_calls
        == capability.provider_calls
        == capability.model_loads
        == 0
    )
    assert ZERO_ACTIVATION_POLICY_V1.active_expression_count == 0
    assert ZERO_ACTIVATION_POLICY_V1.active_surface_count == 0
    assert capability.proof_activation_authority_identity is None
    assert (
        UnavailableVoiceExecutorV1().inspect_capability().availability == "unavailable"
    )


def test_frozen_proof_authority_is_versioned_complete_and_deterministic() -> None:
    authority = FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1

    assert authority.authority_scope == "proof_only"
    assert not authority.production_eligible
    assert not authority.ordinary_story_eligible
    assert tuple(item.proof_id for item in authority.entries) == tuple(
        f"P{ordinal}" for ordinal in range(1, 9)
    )
    assert type(authority).model_validate_json(authority.model_dump_json()) == authority


def test_proof_ir_requires_explicit_exact_frozen_authority() -> None:
    executor = DeterministicVoiceExecutorV2(activation_policy=ZERO_ACTIVATION_POLICY_V1)
    governed = _base(selected=True, expression_none=True)
    missing = finalize_request_v2(
        governed.model_copy(update={"proof_activation_authority": None})
    )

    rejected = executor.execute(missing)
    accepted = executor.execute(governed)

    assert rejected.kind is DeterministicTerminalKindV2.INTEGRITY_FAILURE
    assert rejected.failure_code == "proof_activation_not_authorized"
    assert accepted.kind is DeterministicTerminalKindV2.GENERATED
    assert ZERO_ACTIVATION_POLICY_V1.active_expression_count == 0
    assert ZERO_ACTIVATION_POLICY_V1.active_surface_count == 0


def test_proof_executor_advertises_only_frozen_proof_authority() -> None:
    capability = ProofOnlyDeterministicVoiceExecutorV2(
        proof_activation_authority=FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1
    ).inspect_capability()

    assert (
        capability.proof_activation_authority_identity
        == FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1.authority_identity
    )
    assert (
        capability.activation_policy_identity
        == ZERO_ACTIVATION_POLICY_V1.policy_identity
    )
    assert (
        capability.model_calls
        == capability.provider_calls
        == capability.model_loads
        == 0
    )


def test_installed_workflow_load_selection_preview_and_reject_are_non_consuming() -> (
    None
):
    frozen_request = _base(selected=True, expression_none=True)
    accepted = []

    class AcceptanceStore:
        def accept(self, request):
            accepted.append(request)

    def execution_request(program, expression):
        return finalize_request_v2(
            frozen_request.model_copy(
                update={
                    "program_selection": program,
                    "expression_selection": expression,
                }
            )
        )

    composition = compose_voice_v2_production()
    composition.application.executor = ProofOnlyDeterministicVoiceExecutorV2(
        proof_activation_authority=FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1
    )
    composition.context_registry.publish(
        VoiceDesktopGovernedContextV2(
            event_id=1,
            program_eligibility=frozen_request.program_eligibility,
            repetition_snapshot=frozen_request.repetition_snapshot,
            expression_eligibility_for_program=lambda _receipt: (
                frozen_request.expression_eligibility
            ),
            execution_request=execution_request,
            acceptance_store=AcceptanceStore(),
            acceptance_request=lambda preview: preview,
        )
    )
    coordinator = composition.desktop_workflow
    refreshed = coordinator.dispatch(VoiceDesktopActionInputV2("load", 1))
    selected = coordinator.dispatch(VoiceDesktopActionInputV2("select_program", 1, SHA))
    no_expression = coordinator.dispatch(
        VoiceDesktopActionInputV2("select_expression", 1, None)
    )
    preview_a = coordinator.dispatch(VoiceDesktopActionInputV2("preview", 1))
    preview_b = coordinator.dispatch(VoiceDesktopActionInputV2("preview", 1))
    rejected = coordinator.dispatch(VoiceDesktopActionInputV2("reject", 1))
    coordinator.dispatch(VoiceDesktopActionInputV2("preview", 1))
    accepted_presentation = coordinator.dispatch(VoiceDesktopActionInputV2("accept", 1))

    assert refreshed.program_choices[-1][1] == "Fără comentariu"
    assert selected.expression_choices == (("NONE", "Fără expresie"),)
    assert no_expression.preview_enabled
    assert preview_a.preview_text == preview_b.preview_text
    assert preview_a.accept_enabled and preview_b.accept_enabled
    assert not rejected.accept_enabled
    assert len(accepted) == 1
    assert not accepted_presentation.accept_enabled
    capability = composition.application.executor.inspect_capability()
    assert (
        capability.model_calls,
        capability.provider_calls,
        capability.model_loads,
    ) == (
        0,
        0,
        0,
    )


def test_installed_workflow_none_and_stale_accept_fail_closed() -> None:
    frozen_request = _base(selected=True, expression_none=True)
    composition = compose_voice_v2_production()
    context = VoiceDesktopGovernedContextV2(
        event_id=1,
        program_eligibility=frozen_request.program_eligibility,
        repetition_snapshot=frozen_request.repetition_snapshot,
        expression_eligibility_for_program=lambda _receipt: (
            frozen_request.expression_eligibility
        ),
        execution_request=lambda _program, _expression: frozen_request,
        acceptance_store=object(),
        acceptance_request=lambda preview: preview,
    )
    coordinator = VoiceDesktopWorkflowCoordinatorV2(
        application=composition.application,
        load_context=lambda _event_id: context,
        owner_identity="owner",
    )
    coordinator.dispatch(VoiceDesktopActionInputV2("refresh", 1))
    omitted = coordinator.dispatch(VoiceDesktopActionInputV2("select_program", 1, None))
    stale = coordinator.dispatch(VoiceDesktopActionInputV2("accept", 1))

    assert "Fără comentariu" in omitted.interaction.message
    assert stale.interaction.state.value == "integrity_failure"
    assert stale.interaction.diagnostic_code == "stale_preview"
    assert not stale.accept_enabled


def test_none_receipts_are_first_class_and_safe_abstention_is_not_failure() -> None:
    executor = DeterministicVoiceExecutorV2(activation_policy=ZERO_ACTIVATION_POLICY_V1)
    result = executor.execute(_base(selected=False))

    assert result.kind is DeterministicTerminalKindV2.SAFELY_ABSTAINED
    assert result.reason_code == "owner_selected_no_commentary"
    assert result.acceptance_blocked
    assert result.model_calls == result.provider_calls == result.model_loads == 0

    generated = ProofOnlyDeterministicVoiceExecutorV2(
        proof_activation_authority=FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1
    ).execute(_base(selected=True, expression_none=True))
    assert generated.kind is DeterministicTerminalKindV2.GENERATED
    assert generated.rendered_utf8
    assert generated.provenance


def test_stale_request_is_integrity_failure_and_blocks_acceptance() -> None:
    executor = DeterministicVoiceExecutorV2(activation_policy=ZERO_ACTIVATION_POLICY_V1)
    request = _base(selected=False).model_copy(update={"request_identity": SHA})
    result = executor.execute(request)

    assert result.kind is DeterministicTerminalKindV2.INTEGRITY_FAILURE
    assert result.failure_code == "request_identity_mismatch"
    assert result.acceptance_blocked


def test_preview_round_trip_is_canonical_and_consumes_no_repetition(tmp_path) -> None:
    request = _base(selected=True, expression_none=True)
    result = ProofOnlyDeterministicVoiceExecutorV2(
        proof_activation_authority=FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1
    ).execute(request)
    sidecar = build_preview_sidecar_v2(request=request, result=result)
    store = VoiceDeterministicPreviewSidecarStoreV2(tmp_path / "voice-preview-v2.json")
    store.save(sidecar)

    assert store.load() == sidecar
    assert sidecar.preview_only
    assert not sidecar.authored_v2_mutated
    assert not sidecar.repetition_budget_consumed

    payload = json.loads(store.path.read_text(encoding="utf-8"))
    payload["schema_version"] = "999"
    store.path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        store.load()

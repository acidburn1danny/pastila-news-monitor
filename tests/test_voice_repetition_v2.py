from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.editor.generation.semantic_draft_v2 import (
    AuthorityDensityV2,
    FactualNucleusBindingV2,
    FactualSummaryV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
    SemanticStoryV2,
)
from pastila_scout.voice_deterministic_v2 import (
    FROZEN_PROOF_CASES_V1,
    build_frozen_realization_ir,
)
from pastila_scout.voice_eligibility_v2.engine import (
    _sealed as voice_sealed,
)
from pastila_scout.voice_eligibility_v2.engine import (
    finalize_selection_receipt,
)
from pastila_scout.voice_eligibility_v2.models import (
    ZERO_IDENTITY,
    ProgramCandidateV1,
    SelectionKindV1,
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
)
from pastila_scout.voice_executor_v2 import (
    FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1,
    RENDERER_IDENTITY,
    ZERO_ACTIVATION_POLICY_V1,
    ProofOnlyDeterministicVoiceExecutorV2,
    build_preview_sidecar_v2,
    finalize_request_v2,
)
from pastila_scout.voice_executor_v2.models import VoiceDeterministicExecutionRequestV2
from pastila_scout.voice_fact_atoms_v2 import (
    VoiceFactAtomBundleV1,
    finalize_bundle_identity,
)
from pastila_scout.voice_repetition_v2 import (
    SimulatedAcceptanceCrash,
    VoiceAcceptanceIntegrityError,
    VoiceAtomicAcceptanceStoreV1,
    derive_repetition_snapshot_v1,
    effective_uses_v1,
    finalize_acceptance_request_v1,
    finalize_candidate_v1,
    finalize_ledger_v1,
    finalize_order_authority_v1,
    publish_episode_uses_v1,
    remove_unpublished_commentary_v1,
)
from pastila_scout.voice_repetition_v2.models import (
    ZERO,
    AcceptanceCandidatePreviewV1,
    EpisodeOrderAuthorityV1,
    PublicationStateV1,
    RepetitionLedgerEventKindV1,
    RepetitionLedgerEventV1,
    VoiceAcceptanceRequestV1,
    VoiceRepetitionLedgerV1,
)
from pastila_scout.voice_workflow_v2 import (
    VoiceStoryBindingV1,
    semantic_draft_revision_identity,
    sha256_identity,
)

NOW = datetime(2026, 8, 23, 12, tzinfo=UTC)
SHA = "sha256:" + "1" * 64
EVIDENCE = Path("tests/fixtures/voice_deterministic_v2/frozen_proof_cases")


def _draft() -> PastilaEditorSemanticDraftV2:
    summary = FactualSummaryV2(
        text="Faptul principal este confirmat.",
        authority_bundle_identity=SHA,
        authority_density=AuthorityDensityV2.STANDARD,
        nucleus_bindings=(
            FactualNucleusBindingV2(
                nucleus_id="n1", sentence_number=1, authority_fact_ids=("f1",)
            ),
        ),
        model_identifier="pastila-editor-core-v1.2-experimental",
        provider="ollama",
        validation_receipt="receipt",
    )
    return PastilaEditorSemanticDraftV2.assemble(
        episode_id="episode-1",
        mode=SemanticDraftModeV2.CORE_ONLY,
        stories=(
            SemanticStoryV2(
                event_id=1,
                position=1,
                factual_summary=summary,
                acid_commentary_status="absent_voice_layer_unavailable",
            ),
        ),
    )


def _order(*, events=(1,)):
    return finalize_order_authority_v1(
        EpisodeOrderAuthorityV1(
            episode_id="episode-1",
            episode_ordinal=1,
            ordered_event_ids=events,
            publication_state=PublicationStateV1.UNPUBLISHED,
        )
    )


def _acceptance_request(draft, ledger, order, *, key="accept-1", replacement=None):
    revision = semantic_draft_revision_identity(draft)
    summary = draft.stories[0].factual_summary
    bundle = finalize_bundle_identity(
        VoiceFactAtomBundleV1(
            revision=1,
            semantic_draft_revision_identity=revision,
            event_id=1,
            story_position=1,
            factual_summary_identity=sha256_identity(summary.text),
            event_authority_identity=SHA,
            candidates=(),
            atoms=(),
            bundle_identity=ZERO_IDENTITY,
        )
    )
    envelope = derive_repetition_snapshot_v1(
        ledger=ledger, order_authority=order, event_id=1
    )
    case = FROZEN_PROOF_CASES_V1["P1"]
    candidate = ProgramCandidateV1(
        candidate_id=SHA,
        program_id=case.realization_program_id,
        mechanic_id=case.mechanic_id,
        cadence_signature="numeric-ladder",
        surface_ids=("P1-owner-surface",),
        repetition_signature="P1-signature",
    )
    provisional = VoiceEligibilityResultV1(
        fact_atom_bundle_identity=bundle.bundle_identity,
        repetition_snapshot_identity=envelope.snapshot.snapshot_identity,
        mechanic_outcomes=(),
        program_outcomes=(),
        shortlist=(candidate,),
        result_identity=ZERO_IDENTITY,
    )
    eligibility = provisional.model_copy(
        update={"result_identity": voice_sealed(provisional, "result_identity")}
    )
    selection = finalize_selection_receipt(
        VoiceOwnerSelectionReceiptV1(
            fact_atom_bundle_identity=bundle.bundle_identity,
            eligibility_result_identity=eligibility.result_identity,
            repetition_snapshot_identity=envelope.snapshot.snapshot_identity,
            shortlist_candidate_ids=(SHA,),
            selection_kind=SelectionKindV1.PROGRAM,
            selected_candidate_id=SHA,
            selector_identity="owner",
            selected_at=NOW,
            receipt_identity=ZERO_IDENTITY,
        ),
        result=eligibility,
        snapshot=envelope.snapshot,
    )
    execution = finalize_request_v2(
        VoiceDeterministicExecutionRequestV2(
            story_binding=VoiceStoryBindingV1(
                story_material_reference="story:1",
                semantic_draft_revision_identity=revision,
                event_id=1,
                factual_summary_sha256=sha256_identity(summary.text),
                event_authority_identity=SHA,
            ),
            fact_atom_bundle=bundle,
            program_eligibility=eligibility,
            program_selection=selection,
            repetition_snapshot=envelope.snapshot,
            activation_policy=ZERO_ACTIVATION_POLICY_V1,
            proof_activation_authority=FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1,
            expected_renderer_identity=RENDERER_IDENTITY,
            ir=build_frozen_realization_ir("P1", EVIDENCE),
        )
    )
    result = ProofOnlyDeterministicVoiceExecutorV2(
        proof_activation_authority=FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1
    ).execute(execution)
    preview = build_preview_sidecar_v2(request=execution, result=result)
    governed = finalize_candidate_v1(
        AcceptanceCandidatePreviewV1(
            preview=preview,
            execution_request=execution,
            order_authority_identity=order.authority_identity,
        )
    )
    return finalize_acceptance_request_v1(
        VoiceAcceptanceRequestV1(
            idempotency_key=key,
            draft=draft,
            candidate=governed,
            order_authority=order,
            owner_identity="owner",
            accepted_at=NOW,
            replaces_commit_identity=replacement,
        )
    )


def test_previews_and_reloads_do_not_consume_repetition(tmp_path) -> None:
    store = VoiceAtomicAcceptanceStoreV1(tmp_path)
    initial = store.current_ledger()
    request = _acceptance_request(_draft(), initial, _order())

    assert effective_uses_v1(store.current_ledger()) == ()
    assert request.candidate.preview.repetition_budget_consumed is False
    assert effective_uses_v1(store.current_ledger()) == ()


def test_atomic_acceptance_commits_base_identifiers_without_expression(
    tmp_path,
) -> None:
    store = VoiceAtomicAcceptanceStoreV1(tmp_path)
    request = _acceptance_request(_draft(), store.current_ledger(), _order())
    receipt = store.accept(request)
    uses = effective_uses_v1(store.current_ledger())

    assert len(uses) == 1
    assert uses[0].mechanic_identity == "NUMERIC_EXPECTATION_LADDER_V1"
    assert uses[0].realization_program_identity
    assert uses[0].cadence_signature == "numeric-ladder"
    assert uses[0].expression_identity is None
    assert (
        receipt.committed_repetition_identity == store.current_ledger().ledger_identity
    )
    assert store.accept(request) == receipt
    assert len(effective_uses_v1(store.current_ledger())) == 1


@pytest.mark.parametrize("fault", ("draft", "ledger"))
def test_interrupted_acceptance_recovers_without_orphans(tmp_path, fault) -> None:
    store = VoiceAtomicAcceptanceStoreV1(tmp_path)
    request = _acceptance_request(_draft(), store.current_ledger(), _order())
    with pytest.raises(SimulatedAcceptanceCrash):
        store.accept(request, fault_after=fault)

    assert effective_uses_v1(store.current_ledger()) == ()
    receipt = store.recover(request)
    assert receipt == store.current_receipt()
    assert len(effective_uses_v1(store.current_ledger())) == 1


def test_changed_order_and_stale_snapshot_block_acceptance(tmp_path) -> None:
    store = VoiceAtomicAcceptanceStoreV1(tmp_path)
    request = _acceptance_request(_draft(), store.current_ledger(), _order())
    changed = finalize_order_authority_v1(
        request.order_authority.model_copy(
            update={"ordered_event_ids": (2, 1), "authority_identity": ZERO}
        )
    )
    stale = finalize_acceptance_request_v1(
        request.model_copy(
            update={"order_authority": changed, "request_identity": ZERO}
        )
    )
    with pytest.raises(VoiceAcceptanceIntegrityError, match="ordering"):
        store.accept(stale)


def test_unpublished_replacement_appends_revocation_and_new_commit(tmp_path) -> None:
    store = VoiceAtomicAcceptanceStoreV1(tmp_path)
    first_request = _acceptance_request(_draft(), store.current_ledger(), _order())
    first_receipt = store.accept(first_request)
    pointer = store.pointer.read_text(encoding="utf-8")
    draft_relative = __import__("json").loads(pointer)["draft_relative_path"]
    accepted_draft = PastilaEditorSemanticDraftV2.model_validate_json(
        (tmp_path / draft_relative).read_bytes()
    )
    first_use = effective_uses_v1(store.current_ledger())[0]
    replacement = _acceptance_request(
        accepted_draft,
        store.current_ledger(),
        _order(),
        key="accept-2",
        replacement=first_use.commit_identity,
    )
    second_receipt = store.accept(replacement)

    assert second_receipt != first_receipt
    assert len(effective_uses_v1(store.current_ledger())) == 1
    assert [item.event_kind for item in store.current_ledger().events][-2:] == [
        RepetitionLedgerEventKindV1.REVOKE,
        RepetitionLedgerEventKindV1.COMMIT,
    ]


def test_published_commit_cannot_be_revoked_and_corruption_fails_closed(
    tmp_path,
) -> None:
    store = VoiceAtomicAcceptanceStoreV1(tmp_path)
    store.accept(_acceptance_request(_draft(), store.current_ledger(), _order()))
    ledger = store.current_ledger()
    target = effective_uses_v1(ledger)[0].commit_identity
    publish = RepetitionLedgerEventV1(
        sequence=len(ledger.events) + 1,
        event_kind=RepetitionLedgerEventKindV1.PUBLISH,
        transaction_identity=SHA,
        target_commit_identity=target,
        actor_identity="publisher",
        reason="explicit publication authority",
        occurred_at=NOW,
    )
    published = finalize_ledger_v1(
        VoiceRepetitionLedgerV1(
            prior_ledger_identity=ledger.ledger_identity,
            events=ledger.events + (publish,),
        )
    )
    revoke = RepetitionLedgerEventV1(
        sequence=len(published.events) + 1,
        event_kind=RepetitionLedgerEventKindV1.REVOKE,
        transaction_identity=SHA,
        target_commit_identity=target,
        actor_identity="owner",
        reason="invalid removal",
        occurred_at=NOW,
    )
    with pytest.raises(ValidationError, match="impossible repetition revocation"):
        VoiceRepetitionLedgerV1(events=published.events + (revoke,))

    store.pointer.write_text("{}", encoding="utf-8")
    with pytest.raises(VoiceAcceptanceIntegrityError):
        store.current_ledger()


def test_owner_removal_creates_new_absent_revision_and_releases_unpublished_use(
    tmp_path,
) -> None:
    store = VoiceAtomicAcceptanceStoreV1(tmp_path)
    store.accept(_acceptance_request(_draft(), store.current_ledger(), _order()))
    target = effective_uses_v1(store.current_ledger())[0].commit_identity

    remove_unpublished_commentary_v1(
        store,
        commit_identity=target,
        owner_identity="owner",
        reason="owner_removed_commentary",
        removed_at=NOW,
    )

    assert effective_uses_v1(store.current_ledger()) == ()
    assert store.current_draft().stories[0].acid_commentary is None
    assert (
        store.current_draft().stories[0].acid_commentary_status
        == "absent_owner_removed"
    )


def test_explicit_publication_authority_makes_cooldown_history_immutable(
    tmp_path,
) -> None:
    store = VoiceAtomicAcceptanceStoreV1(tmp_path)
    store.accept(_acceptance_request(_draft(), store.current_ledger(), _order()))
    publish_episode_uses_v1(
        store,
        publication_authority_identity=SHA,
        publisher_identity="chief-editor",
        published_at=NOW,
    )
    use = effective_uses_v1(store.current_ledger())[0]
    assert use.publication_state is PublicationStateV1.PUBLISHED
    with pytest.raises(VoiceAcceptanceIntegrityError, match="unavailable"):
        remove_unpublished_commentary_v1(
            store,
            commit_identity=use.commit_identity,
            owner_identity="owner",
            reason="cannot_remove_published",
            removed_at=NOW,
        )

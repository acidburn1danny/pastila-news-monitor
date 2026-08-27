from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest

from pastila_scout.editor.generation.semantic_draft_v2 import (
    AuthorityDensityV2, FactualNucleusBindingV2, FactualSummaryV2,
    PastilaEditorSemanticDraftV2, SemanticDraftModeV2, SemanticStoryV2,
)
from pastila_scout.voice_deterministic_v2.models import (
    AcidCommentaryIRV1_1, IRDispositionV1, IRSpanV1, MechanicIdV1,
    ProvenanceClassV1, RenderedProvenanceSpanV1,
)
from pastila_scout.voice_eligibility_v2.engine import _sealed, finalize_selection_receipt
from pastila_scout.voice_eligibility_v2.models import (
    ProgramCandidateV1, SelectionKindV1, VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
)
from pastila_scout.voice_executor_v2 import (
    RENDERER_IDENTITY, ZERO_ACTIVATION_POLICY_V1, build_preview_sidecar_v2,
    finalize_request_v2,
)
from pastila_scout.voice_executor_v2.models import (
    DeterministicBackendKindV2, VoiceDeterministicExecutionRequestV2,
    VoiceGeneratedResultV2,
)
from pastila_scout.voice_fact_atoms_v2 import VoiceFactAtomBundleV1, finalize_bundle_identity
from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity
from pastila_scout.voice_governed_realization_v1 import GovernedRealizationReceiptV1
from pastila_scout.voice_repetition_v2 import (
    SimulatedAcceptanceCrash, VoiceAtomicAcceptanceStoreV1,
    derive_repetition_snapshot_v1, effective_uses_v1,
    finalize_acceptance_request_v1, finalize_candidate_v1,
    finalize_order_authority_v1, publish_episode_uses_v1,
    remove_unpublished_commentary_v1,
)
from pastila_scout.voice_repetition_v2.models import (
    AcceptanceCandidatePreviewV1, EpisodeOrderAuthorityV1, PublicationStateV1,
    VoiceAcceptanceRequestV1,
)
from pastila_scout.voice_workflow_v2 import (
    VoiceStoryBindingV1, semantic_draft_revision_identity, sha256_identity,
)

NOW = datetime(2026, 8, 27, 12, tzinfo=UTC)
ZERO = "sha256:" + "0" * 64
SHA = "sha256:" + "1" * 64
TEXT = "Comentariu imaginar, complet separat de afirmațiile factuale."


def _draft():
    summary = FactualSummaryV2(
        text="Faptul principal este confirmat.", authority_bundle_identity=SHA,
        authority_density=AuthorityDensityV2.STANDARD,
        nucleus_bindings=(FactualNucleusBindingV2(nucleus_id="n1", sentence_number=1, authority_fact_ids=("f1",)),),
        model_identifier="pastila-editor-core-v1.2-experimental", provider="ollama",
        validation_receipt="receipt",
    )
    return PastilaEditorSemanticDraftV2.assemble(
        episode_id="episode-1", mode=SemanticDraftModeV2.CORE_ONLY,
        stories=(SemanticStoryV2(event_id=1, position=1, factual_summary=summary,
            acid_commentary_status="absent_voice_layer_unavailable"),),
    )


def _sealed_model(value, field):
    return value.model_copy(update={field: canonical_identity(value.model_copy(update={field: ZERO}))})


def _request(store, key="accept-1"):
    draft = _draft(); revision = semantic_draft_revision_identity(draft)
    order = finalize_order_authority_v1(EpisodeOrderAuthorityV1(
        episode_id="episode-1", episode_ordinal=1, ordered_event_ids=(1,),
        publication_state=PublicationStateV1.UNPUBLISHED))
    bundle = finalize_bundle_identity(VoiceFactAtomBundleV1(
        revision=1, semantic_draft_revision_identity=revision, event_id=1,
        story_position=1, factual_summary_identity=sha256_identity(draft.stories[0].factual_summary.text),
        event_authority_identity=SHA, candidates=(), atoms=(), bundle_identity=ZERO))
    snapshot = derive_repetition_snapshot_v1(ledger=store.current_ledger(), order_authority=order, event_id=1).snapshot
    candidate = ProgramCandidateV1(candidate_id=SHA, program_id="SYNTHETIC_PROGRAM_V1",
        mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER, cadence_signature="synthetic",
        surface_ids=(), repetition_signature="synthetic")
    provisional = VoiceEligibilityResultV1(fact_atom_bundle_identity=bundle.bundle_identity,
        repetition_snapshot_identity=snapshot.snapshot_identity, mechanic_outcomes=(),
        program_outcomes=(), shortlist=(candidate,), result_identity=ZERO)
    eligibility = provisional.model_copy(update={"result_identity": _sealed(provisional, "result_identity")})
    selection = finalize_selection_receipt(VoiceOwnerSelectionReceiptV1(
        fact_atom_bundle_identity=bundle.bundle_identity, eligibility_result_identity=eligibility.result_identity,
        repetition_snapshot_identity=snapshot.snapshot_identity, shortlist_candidate_ids=(SHA,),
        selection_kind=SelectionKindV1.PROGRAM, selected_candidate_id=SHA,
        selector_identity="owner", selected_at=NOW, receipt_identity=ZERO), result=eligibility, snapshot=snapshot)
    output_sha = hashlib.sha256(TEXT.encode()).hexdigest()
    ir = AcidCommentaryIRV1_1(proof_id="P1", source_record_id="synthetic",
        realization_program_id="SYNTHETIC_PROGRAM_V1", realization_program_sha256="0"*64,
        mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER, disposition=IRDispositionV1.REALIZE,
        spans=(IRSpanV1(text=TEXT, provenance_class=ProvenanceClassV1.NONFACTUAL_COMIC_SURFACE,
            source_identity="synthetic-surface"),), repetition_signature="synthetic", expected_output_sha256=output_sha)
    execution = finalize_request_v2(VoiceDeterministicExecutionRequestV2(
        story_binding=VoiceStoryBindingV1(story_material_reference="story:1", semantic_draft_revision_identity=revision,
            event_id=1, factual_summary_sha256=sha256_identity(draft.stories[0].factual_summary.text), event_authority_identity=SHA),
        fact_atom_bundle=bundle, program_eligibility=eligibility, program_selection=selection,
        repetition_snapshot=snapshot, activation_policy=ZERO_ACTIVATION_POLICY_V1,
        expected_renderer_identity=RENDERER_IDENTITY, ir=ir))
    receipt = _sealed_model(GovernedRealizationReceiptV1(program_id="SYNTHETIC_PROGRAM_V1",
        model_identity="synthetic-model", factual_summary_sha256=hashlib.sha256(draft.stories[0].factual_summary.text.encode()).hexdigest(),
        raw_response_sha256=output_sha, commentary_sha256=output_sha,
        validation_codes=("synthetic",), receipt_identity=ZERO), "receipt_identity")
    result = _sealed_model(VoiceGeneratedResultV2(backend_kind=DeterministicBackendKindV2.GOVERNED_MODEL_REALIZER,
        renderer_identity=RENDERER_IDENTITY, request_identity=execution.request_identity,
        model_calls=1, provider_calls=1, model_loads=1, model_identity="synthetic-model",
        realization_receipt_identity=receipt.receipt_identity, realization_receipt=receipt,
        canonical_ir_identity=hashlib.sha256(b"synthetic-ir").hexdigest(), rendered_utf8=TEXT.encode(),
        rendered_sha256=output_sha, provenance=(RenderedProvenanceSpanV1(start=0,end=len(TEXT),
            provenance_class=ProvenanceClassV1.NONFACTUAL_COMIC_SURFACE, source_identity=receipt.receipt_identity),),
        validation_identity=SHA, result_identity=ZERO), "result_identity")
    preview = build_preview_sidecar_v2(request=execution, result=result)
    governed = finalize_candidate_v1(AcceptanceCandidatePreviewV1(preview=preview,
        execution_request=execution, order_authority_identity=order.authority_identity))
    return finalize_acceptance_request_v1(VoiceAcceptanceRequestV1(idempotency_key=key,
        draft=draft, candidate=governed, order_authority=order, owner_identity="owner", accepted_at=NOW))


def test_atomic_recovery_removal_and_publication_are_append_only(tmp_path):
    crashed = VoiceAtomicAcceptanceStoreV1(tmp_path / "recover")
    request = _request(crashed)
    with pytest.raises(SimulatedAcceptanceCrash): crashed.accept(request, fault_after="ledger")
    assert effective_uses_v1(crashed.current_ledger()) == ()
    receipt = crashed.recover(request)
    use = effective_uses_v1(crashed.current_ledger())[0]
    removal = remove_unpublished_commentary_v1(crashed, commit_identity=use.commit_identity,
        owner_identity="owner", reason="owner removal", removed_at=NOW)
    assert removal.removed_commit_identity == use.commit_identity
    assert effective_uses_v1(crashed.current_ledger()) == ()

    published = VoiceAtomicAcceptanceStoreV1(tmp_path / "publish")
    published.accept(_request(published, "accept-2"))
    publication = publish_episode_uses_v1(published, publication_authority_identity=SHA,
        publisher_identity="publisher", published_at=NOW)
    assert publication.published_commit_identities
    assert effective_uses_v1(published.current_ledger())[0].publication_state is PublicationStateV1.PUBLISHED

"""Restart-safe Desktop context loader backed by canonical Voice state."""

from __future__ import annotations

from datetime import UTC, datetime

from pastila_scout.expression_catalog_v2 import (
    evaluate_expression_eligibility_v1,
    load_expression_catalog_overlay_v2,
)
from pastila_scout.expression_retrieval_v1 import load_catalog_v1
from pastila_scout.voice_canonical_state_v2 import (
    CanonicalVoiceLifecycleV2,
    CanonicalVoicePersistenceError,
    CanonicalVoiceStoryStateV2,
    CanonicalVoiceWorkspaceStoreV2,
)
from pastila_scout.voice_deterministic_v2.production import (
    materialize_production_ir_v1_1,
)
from pastila_scout.voice_executor_v2 import (
    RENDERER_IDENTITY,
    ZERO_ACTIVATION_POLICY_V1,
    build_governed_execution_request_v2,
)
from pastila_scout.voice_executor_v2.models import VoiceProductionActivationPolicyV1
from pastila_scout.voice_executor_v2.persistence import build_preview_sidecar_v2
from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity
from pastila_scout.voice_governed_context_v2 import VoiceGovernedContextV2
from pastila_scout.voice_repetition_v2 import (
    finalize_acceptance_request_v1,
    finalize_candidate_v1,
)
from pastila_scout.voice_repetition_v2.models import (
    AcceptanceCandidatePreviewV1,
    VoiceAcceptanceRequestV1,
)
from pastila_scout.voice_workflow_v2 import semantic_draft_revision_identity


class _PromotingAcceptanceStore:
    def __init__(self, loader: PersistedStoryGovernedContextLoaderV2, event_id: int):
        self.loader = loader
        self.event_id = event_id

    def accept(self, request):
        receipt = self.loader.store.acceptance_store.accept(request)
        state = self.loader._required(self.event_id)
        promoted = self.loader.store.promote_acceptance(state, receipt)
        if self.loader.revision_promoter is not None:
            self.loader.revision_promoter.promote(
                promoted,
                expected_source_revision_identity=(
                    receipt.source_semantic_draft_revision_identity
                ),
            )
        return receipt


class PersistedStoryGovernedContextLoaderV2:
    """Reconstruct the complete execution context from one explicit story pointer."""

    def __init__(
        self,
        store: CanonicalVoiceWorkspaceStoreV2,
        revision_promoter=None,
        *,
        activation_policy: VoiceProductionActivationPolicyV1 = ZERO_ACTIVATION_POLICY_V1,
    ):
        self.store = store
        self.revision_promoter = revision_promoter
        self.activation_policy = activation_policy

    def _required(self, event_id: int) -> CanonicalVoiceStoryStateV2:
        state = self.store.load_story(event_id)
        if state is None:
            raise CanonicalVoicePersistenceError("no canonical Voice story state")
        return state

    def promote_removal(self, prior, receipt):
        """Promote one atomic owner removal and its exact absent Chief revision."""

        source_revision = semantic_draft_revision_identity(prior.authored_draft)
        promoted = self.store.promote_removal(prior, receipt)
        if self.revision_promoter is not None:
            self.revision_promoter.promote(
                promoted, expected_source_revision_identity=source_revision
            )
        return promoted

    def load(self, event_id: int) -> VoiceGovernedContextV2 | None:
        state = self.store.load_story(event_id)
        if state is None:
            return None
        if (
            state.lifecycle is CanonicalVoiceLifecycleV2.ACCEPTED_COMMENTARY
            and self.revision_promoter is not None
        ):
            self.revision_promoter.promote(
                state,
                expected_source_revision_identity=(
                    state.binding.semantic_draft_revision_identity
                ),
            )
        accepted_commentary = next(
            (
                story.acid_commentary.text
                for story in state.authored_draft.stories
                if story.event_id == event_id and story.acid_commentary is not None
            ),
            None,
        )

        def expression_for(program_receipt):
            current = self._required(event_id)
            if current.expression_eligibility is None:
                if (
                    current.activation_policy_identity
                    != self.activation_policy.policy_identity
                ):
                    raise CanonicalVoicePersistenceError(
                        "expression activation policy is stale"
                    )
                selected = next(
                    (
                        item
                        for item in current.program_eligibility.shortlist
                        if item.candidate_id == program_receipt.selected_candidate_id
                    ),
                    None,
                )
                if selected is None:
                    raise CanonicalVoicePersistenceError("program receipt is stale")
                expression_result = evaluate_expression_eligibility_v1(
                    bundle=current.fact_atom_bundle,
                    bindings=current.relationship_bindings,
                    program_result=current.program_eligibility,
                    selected_program_candidate=selected,
                    repetition_snapshot=current.repetition_snapshot,
                    overlay=load_expression_catalog_overlay_v2(),
                    catalog=load_catalog_v1(use_cache=False),
                )
                current = self.store.save_story(
                    current.model_copy(
                        update={
                            "expression_eligibility": expression_result,
                            "prior_state_identity": current.state_identity,
                            "state_identity": "sha256:" + "0" * 64,
                        }
                    )
                )
            selected_candidate_id = program_receipt.selected_candidate_id
            if selected_candidate_id is not None and any(
                item.selected_program_candidate_id != selected_candidate_id
                for item in current.expression_eligibility.shortlist
            ):
                raise CanonicalVoicePersistenceError(
                    "expression eligibility belongs to another program"
                )
            return current.expression_eligibility

        def persist_program(receipt):
            current = self._required(event_id)
            updated = current.model_copy(
                update={
                    "lifecycle": CanonicalVoiceLifecycleV2.PROGRAM_SELECTED,
                    "program_selection": receipt,
                    "expression_selection": None,
                    "execution_request": None,
                    "preview": None,
                    "prior_state_identity": current.state_identity,
                    "state_identity": "sha256:" + "0" * 64,
                }
            )
            self.store.save_story(updated)
            return self.load(event_id)

        def persist_expression(expression_result, receipt):
            current = self._required(event_id)
            updated = current.model_copy(
                update={
                    "lifecycle": CanonicalVoiceLifecycleV2.EXPRESSION_SELECTED_OR_NONE,
                    "expression_eligibility": expression_result,
                    "expression_selection": receipt,
                    "execution_request": None,
                    "preview": None,
                    "prior_state_identity": current.state_identity,
                    "state_identity": "sha256:" + "0" * 64,
                }
            )
            self.store.save_story(updated)
            return self.load(event_id)

        def execution_request(program_receipt, expression_receipt):
            current = self._required(event_id)
            candidate = next(
                (
                    item
                    for item in current.program_eligibility.shortlist
                    if item.candidate_id == program_receipt.selected_candidate_id
                ),
                None,
            )
            if candidate is None:
                raise CanonicalVoicePersistenceError("program receipt is stale")
            claim = next(
                (
                    item
                    for item in current.mechanic_claims
                    if item.mechanic_id is candidate.mechanic_id
                ),
                None,
            )
            if claim is None:
                raise CanonicalVoicePersistenceError("mechanic claim is missing")
            ir = materialize_production_ir_v1_1(
                story_binding=current.binding,
                bundle=current.fact_atom_bundle,
                eligibility=current.program_eligibility,
                mechanic_claim=claim,
                selection=program_receipt,
                repetition_snapshot=current.repetition_snapshot,
                atom_roles=claim.atom_roles,
                activation_policy_identity=self.activation_policy.policy_identity,
                renderer_identity=RENDERER_IDENTITY,
                relationship_binding_identities=tuple(
                    item.binding_identity for item in current.relationship_bindings
                ),
                expression_selection=expression_receipt,
            )
            return build_governed_execution_request_v2(
                story_binding=current.binding,
                fact_atom_bundle=current.fact_atom_bundle,
                relationship_bindings=current.relationship_bindings,
                program_eligibility=current.program_eligibility,
                mechanic_claim=claim,
                program_selection=program_receipt,
                expression_eligibility=current.expression_eligibility,
                expression_selection=expression_receipt,
                repetition_snapshot=current.repetition_snapshot,
                activation_policy=self.activation_policy,
                ir=ir,
            )

        def persist_preview(request, result):
            current = self._required(event_id)
            sidecar = build_preview_sidecar_v2(request=request, result=result)
            lifecycle = (
                CanonicalVoiceLifecycleV2.SAFE_ABSTENTION
                if result.kind.value == "safely_abstained"
                else CanonicalVoiceLifecycleV2.PREVIEW_AVAILABLE
            )
            updated = current.model_copy(
                update={
                    "lifecycle": lifecycle,
                    "execution_request": request,
                    "preview": sidecar,
                    "prior_state_identity": current.state_identity,
                    "state_identity": "sha256:" + "0" * 64,
                }
            )
            self.store.save_story(updated)
            return self.load(event_id)

        def acceptance_request(result):
            current = self._required(event_id)
            if (
                current.preview is None
                or current.execution_request is None
                or current.preview.terminal_result != result
            ):
                raise CanonicalVoicePersistenceError("preview is stale")
            candidate = finalize_candidate_v1(
                AcceptanceCandidatePreviewV1(
                    preview=current.preview,
                    execution_request=current.execution_request,
                    order_authority_identity=current.order_authority.authority_identity,
                )
            )
            return finalize_acceptance_request_v1(
                VoiceAcceptanceRequestV1(
                    idempotency_key=canonical_identity(
                        {
                            "event_id": event_id,
                            "preview": current.preview.sidecar_identity,
                            "owner": "desktop-owner",
                        }
                    ),
                    draft=current.authored_draft,
                    candidate=candidate,
                    order_authority=current.order_authority,
                    owner_identity="desktop-owner",
                    accepted_at=datetime.now(UTC),
                )
            )

        return VoiceGovernedContextV2(
            event_id=event_id,
            factual_summary=next(
                story.factual_summary.text
                for story in state.authored_draft.stories
                if story.event_id == event_id
            ),
            program_eligibility=state.program_eligibility,
            repetition_snapshot=state.repetition_snapshot,
            expression_eligibility_for_program=expression_for,
            execution_request=execution_request,
            acceptance_store=_PromotingAcceptanceStore(self, event_id),
            acceptance_request=acceptance_request,
            accepted_commentary_text=accepted_commentary,
            persist_program_selection=persist_program,
            persist_expression_selection=persist_expression,
            persist_preview=persist_preview,
        )


__all__ = ["PersistedStoryGovernedContextLoaderV2"]

"""Application service for explicit, model-free owner adjudication."""

from __future__ import annotations

import hashlib
import unicodedata
from datetime import datetime

from pastila_scout.voice_eligibility_v2 import (
    evaluate_voice_eligibility_v1,
    finalize_claim_identity,
)
from pastila_scout.voice_eligibility_v2.library import PROGRAM_SPECS_V1
from pastila_scout.voice_eligibility_v2.models import (
    AtomRoleBindingV1,
    MechanicEligibilityClaimV1,
)
from pastila_scout.voice_fact_atoms_v2 import (
    extract_surface_candidates,
    extract_typed_authority_candidates_v2,
)
from pastila_scout.voice_fact_atoms_v2.extraction_v2 import TypedAuthorityFieldInputV2
from pastila_scout.voice_fact_atoms_v2.models import (
    AuthorityPassageV1,
    CandidateKind,
    FactAtomV1,
    SurfaceCandidateV1,
    VoiceFactAtomBundleV1,
    VoiceFactAtomBundleV2,
)
from pastila_scout.voice_fact_atoms_v2.persistence import (
    canonical_identity,
    finalize_bundle_identity,
)
from pastila_scout.voice_workflow_v2.models import VoiceStoryBindingV1

from .models import (
    ZERO,
    AdjudicationLifecycleV1,
    AuthorityTextV1,
    CandidateOwnerDispositionV1,
    FactAtomOwnerDecisionRebindProvenanceV1,
    FactAtomOwnerReceiptV2,
    MechanicClaimOwnerReceiptV1,
    OwnerDecisionRebindAuthorizationV1,
    PriorCandidateProvenanceClassV1,
    VoiceStoryAdjudicationStateV1,
    VoiceStoryAdjudicationStateV2,
    VoiceStoryAdjudicationStateV3,
)
from .persistence import VoiceAdjudicationStoreV1


class VoiceAdjudicationError(ValueError):
    pass


def _seal(value, field="receipt_identity"):
    return value.model_copy(
        update={field: canonical_identity(value.model_copy(update={field: ZERO}))}
    )


def _seal_claim_receipt(value: MechanicClaimOwnerReceiptV1):
    normalized = value.model_copy(
        update={
            "receipt_identity": ZERO,
            "mechanic_claim": value.mechanic_claim.model_copy(
                update={"adjudication_receipt_identity": ZERO, "claim_identity": ZERO}
            ),
        }
    )
    receipt_identity = canonical_identity(normalized)
    claim = finalize_claim_identity(
        value.mechanic_claim.model_copy(
            update={"adjudication_receipt_identity": receipt_identity}
        )
    )
    return value.model_copy(
        update={"mechanic_claim": claim, "receipt_identity": receipt_identity}
    )


class VoiceAdjudicationApplicationServiceV1:
    def __init__(self, store: VoiceAdjudicationStoreV1):
        self.store = store
        self.model_calls = self.provider_calls = self.model_loads = 0

    def load_for_story(
        self,
        *,
        binding: VoiceStoryBindingV1,
        authority_texts: tuple[AuthorityTextV1, ...],
        extraction_fields: tuple[TypedAuthorityFieldInputV2, ...] | None = None,
        repetition_snapshot,
    ):
        state = self.store.load(binding.event_id)
        if state is None:
            return None
        current_authority = tuple(
            (item.authority_identity, item.source_identity, item.text_sha256)
            for item in authority_texts
        )
        persisted_authority = tuple(
            (item.authority_identity, item.source_identity, item.text_sha256)
            for item in state.authority_texts
        )
        if state.binding != binding:
            return self.mark_stale(state, reason="story_revision_or_binding_changed")
        if current_authority != persisted_authority:
            return self.mark_stale(state, reason="source_authority_changed")
        if isinstance(state, VoiceStoryAdjudicationStateV2):
            if extraction_fields is None or state.extraction_fields != extraction_fields:
                return self.mark_stale(state, reason="typed_extraction_authority_changed")
        elif extraction_fields is not None:
            return self.mark_stale(state, reason="extraction_input_contract_changed")
        if state.repetition_snapshot.snapshot_identity != (
            repetition_snapshot.snapshot_identity
        ):
            eligibility = None
            if state.lifecycle in {
                AdjudicationLifecycleV1.MECHANIC_CLAIMS_FINALIZED,
                AdjudicationLifecycleV1.NO_CLAIM,
            }:
                eligibility = evaluate_voice_eligibility_v1(
                    bundle=state.fact_atom_bundle,
                    claims=state.mechanic_claims,
                    repetition_snapshot=repetition_snapshot,
                )
            return self.store.save(
                state.model_copy(
                    update={
                        "repetition_snapshot": repetition_snapshot,
                        "eligibility": eligibility,
                        "prior_state_identity": state.state_identity,
                        "state_identity": ZERO,
                    }
                )
            )
        return state

    def begin(
        self,
        *,
        binding: VoiceStoryBindingV1,
        story_position: int,
        authority_texts: tuple[AuthorityTextV1, ...],
        repetition_snapshot,
    ) -> VoiceStoryAdjudicationStateV1:
        if any(
            item.text_sha256
            != "sha256:" + hashlib.sha256(item.text.encode()).hexdigest()
            for item in authority_texts
        ):
            raise VoiceAdjudicationError("authority text identity mismatch")
        event_authorities = {
            item.authority_identity
            for item in authority_texts
            if item.authority_class.value == "event_authority"
        }
        if event_authorities != {binding.event_authority_identity}:
            raise VoiceAdjudicationError("event authority binding mismatch")
        candidates = tuple(
            candidate
            for authority in authority_texts
            for candidate in extract_surface_candidates(
                authority_class=authority.authority_class,
                authority_identity=authority.authority_identity,
                source_identity=authority.source_identity,
                text=authority.text,
            )
        )
        bundle = finalize_bundle_identity(
            VoiceFactAtomBundleV1(
                revision=1,
                semantic_draft_revision_identity=(
                    binding.semantic_draft_revision_identity
                ),
                event_id=binding.event_id,
                story_position=story_position,
                factual_summary_identity=binding.factual_summary_sha256,
                event_authority_identity=binding.event_authority_identity,
                candidates=candidates,
                atoms=(),
                bundle_identity=ZERO,
            )
        )
        return self.store.save(
            VoiceStoryAdjudicationStateV1(
                lifecycle=AdjudicationLifecycleV1.CANDIDATES_EXTRACTED,
                binding=binding,
                authority_texts=authority_texts,
                candidates=candidates,
                fact_atom_bundle=bundle,
                repetition_snapshot=repetition_snapshot,
            )
        )

    def begin_v2(
        self,
        *,
        binding: VoiceStoryBindingV1,
        story_position: int,
        authority_texts: tuple[AuthorityTextV1, ...],
        extraction_fields: tuple[TypedAuthorityFieldInputV2, ...],
        repetition_snapshot,
    ) -> VoiceStoryAdjudicationStateV2:
        if any(
            item.text_sha256
            != "sha256:" + hashlib.sha256(item.text.encode()).hexdigest()
            for item in authority_texts
        ):
            raise VoiceAdjudicationError("authority text identity mismatch")
        if any(
            item.authority_identity != binding.event_authority_identity
            or item.authority_class.value != "event_authority"
            for item in extraction_fields
        ):
            raise VoiceAdjudicationError("typed extraction authority mismatch")
        candidates = extract_typed_authority_candidates_v2(extraction_fields)
        bundle = finalize_bundle_identity(
            VoiceFactAtomBundleV2(
                revision=1,
                semantic_draft_revision_identity=(
                    binding.semantic_draft_revision_identity
                ),
                event_id=binding.event_id,
                story_position=story_position,
                factual_summary_identity=binding.factual_summary_sha256,
                event_authority_identity=binding.event_authority_identity,
                candidates=candidates,
                atoms=(),
                bundle_identity=ZERO,
            )
        )
        return self.store.save(
            VoiceStoryAdjudicationStateV2(
                lifecycle=AdjudicationLifecycleV1.CANDIDATES_EXTRACTED,
                binding=binding,
                authority_texts=authority_texts,
                extraction_fields=extraction_fields,
                candidates=candidates,
                fact_atom_bundle=bundle,
                repetition_snapshot=repetition_snapshot,
            )
        )

    def add_exact_candidate(
        self,
        state: VoiceStoryAdjudicationStateV1,
        *,
        source_identity: str,
        start: int,
        end: int,
        kind: CandidateKind,
    ):
        sources = (
            state.extraction_fields
            if isinstance(state, VoiceStoryAdjudicationStateV2)
            else state.authority_texts
        )
        source = next(
            (item for item in sources if item.source_identity == source_identity), None
        )
        if source is None or start < 0 or end <= start or end > len(source.text):
            raise VoiceAdjudicationError("invalid owner-selected source span")
        passage = source.text[start:end]
        evidence = AuthorityPassageV1(
            authority_class=source.authority_class,
            authority_identity=source.authority_identity,
            source_identity=source_identity,
            passage=passage,
            start=start,
            end=end,
        )
        seed = {
            "owner_selected_exact_span": evidence.model_dump(mode="json"),
            "kind": kind.value,
        }
        identity = canonical_identity(seed)
        candidate = SurfaceCandidateV1(
            candidate_id=f"candidate:{identity}",
            kind=kind,
            evidence=evidence,
            normalized_key=unicodedata.normalize("NFKC", passage).casefold(),
            extraction_receipt_identity=identity,
        )
        if candidate.candidate_id in {item.candidate_id for item in state.candidates}:
            return state
        candidates = (*state.candidates, candidate)
        bundle = finalize_bundle_identity(
            state.fact_atom_bundle.model_copy(
                update={
                    "candidates": candidates,
                    "revision": state.fact_atom_bundle.revision + 1,
                    "bundle_identity": ZERO,
                }
            )
        )
        return self.store.save(
            state.model_copy(
                update={
                    "candidates": candidates,
                    "fact_atom_bundle": bundle,
                    "mechanic_claims": (),
                    "mechanic_claim_receipts": (),
                    "eligibility": None,
                    "prior_state_identity": state.state_identity,
                    "state_identity": ZERO,
                }
            )
        )

    def decide_fact_atom(
        self,
        state: VoiceStoryAdjudicationStateV1,
        *,
        candidate_identity: str,
        disposition: CandidateOwnerDispositionV1,
        atom: FactAtomV1 | None,
        adjudicator_identity: str,
        adjudicated_at: datetime,
        decision_rationale: str,
        governed_object_or_scope: str | None = None,
        actor_or_subject_atom_ids: tuple[str, ...] = (),
        chronology_atom_ids: tuple[str, ...] = (),
        uncertainty_target_atom_ids: tuple[str, ...] = (),
        attribution_atom_ids: tuple[str, ...] = (),
        supersession_reason: str | None = None,
    ):
        candidate = next(
            (
                item
                for item in state.candidates
                if item.candidate_id == candidate_identity
            ),
            None,
        )
        if candidate is None:
            raise VoiceAdjudicationError("unknown extraction candidate")
        if atom is not None and (
            atom.proposition != candidate.evidence.passage
            or atom.candidate_ids != (candidate.candidate_id,)
            or atom.evidence != (candidate.evidence,)
        ):
            raise VoiceAdjudicationError(
                "fact atom must preserve the exact source span"
            )
        prior = next(
            (
                item
                for item in reversed(state.fact_atom_receipts)
                if item.candidate_identity == candidate_identity
            ),
            None,
        )
        receipt = _seal(
            FactAtomOwnerReceiptV2(
                semantic_draft_revision_identity=(
                    state.binding.semantic_draft_revision_identity
                ),
                event_authority_identity=state.binding.event_authority_identity,
                candidate_identity=candidate_identity,
                exact_source_span_sha256="sha256:"
                + hashlib.sha256(candidate.evidence.passage.encode()).hexdigest(),
                disposition=disposition,
                resulting_atom=atom,
                governed_object_or_scope=governed_object_or_scope,
                actor_or_subject_atom_ids=actor_or_subject_atom_ids,
                chronology_atom_ids=chronology_atom_ids,
                uncertainty_target_atom_ids=uncertainty_target_atom_ids,
                attribution_atom_ids=attribution_atom_ids,
                adjudicator_identity=adjudicator_identity,
                adjudicated_at=adjudicated_at,
                decision_rationale=decision_rationale,
                prior_receipt_identity=prior.receipt_identity if prior else None,
                supersession_reason=supersession_reason if prior else None,
            )
        )
        latest = {
            item.candidate_identity: item
            for item in (*state.fact_atom_receipts, receipt)
        }
        atoms = tuple(
            item.resulting_atom
            for item in latest.values()
            if item.disposition is CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM
            and item.resulting_atom is not None
        )
        bundle = finalize_bundle_identity(
            state.fact_atom_bundle.model_copy(
                update={
                    "revision": state.fact_atom_bundle.revision + 1,
                    "atoms": atoms,
                    "adjudication_receipt_identities": tuple(
                        item.receipt_identity for item in latest.values()
                    ),
                    "bundle_identity": ZERO,
                }
            )
        )
        return self.store.save(
            state.model_copy(
                update={
                    "lifecycle": AdjudicationLifecycleV1.FACT_ATOMS_PARTIAL,
                    "fact_atom_receipts": (*state.fact_atom_receipts, receipt),
                    "fact_atom_bundle": bundle,
                    "mechanic_claim_receipts": (),
                    "mechanic_claims": (),
                    "eligibility": None,
                    "explicit_no_claim_reason": None,
                    "prior_state_identity": state.state_identity,
                    "state_identity": ZERO,
                }
            )
        )

    def rebind_fact_atom_owner_decision(
        self,
        state: VoiceStoryAdjudicationStateV2,
        *,
        prior_candidate_identity: str,
        prior_candidate_provenance_class: PriorCandidateProvenanceClassV1,
        target_candidate_identity: str,
        expected_source_identity: str,
        expected_field_name: str,
        expected_passage: str,
        expected_start: int,
        expected_end: int,
        expected_candidate_kind: CandidateKind,
        disposition: CandidateOwnerDispositionV1,
        decision_rationale: str,
        owner_authorization: OwnerDecisionRebindAuthorizationV1,
        adjudicator_identity: str,
        adjudicated_at: datetime,
        atom: FactAtomV1 | None = None,
        governed_object_or_scope: str | None = None,
    ) -> VoiceStoryAdjudicationStateV3:
        """Atomically persist one terminal receipt and its immutable rebind lineage."""
        if not isinstance(state, VoiceStoryAdjudicationStateV2):
            raise VoiceAdjudicationError("rebind requires typed extraction V2 state")
        if (
            state.fact_atom_bundle.extraction_policy_version
            != "voice-fact-candidate-extraction-v2"
        ):
            raise VoiceAdjudicationError("rebind target extraction policy mismatch")
        existing_provenance = (
            state.fact_atom_rebind_provenance
            if isinstance(state, VoiceStoryAdjudicationStateV3)
            else ()
        )
        if any(
            item.prior_candidate_identity == prior_candidate_identity
            or item.target_candidate_identity == target_candidate_identity
            for item in existing_provenance
        ):
            raise VoiceAdjudicationError("rebind mapping is not one-to-one")
        if any(
            item.candidate_identity == target_candidate_identity
            for item in state.fact_atom_receipts
        ):
            raise VoiceAdjudicationError("target candidate already has a receipt")
        candidate = next(
            (
                item
                for item in state.candidates
                if item.candidate_id == target_candidate_identity
            ),
            None,
        )
        field = next(
            (
                item
                for item in state.extraction_fields
                if item.source_identity == expected_source_identity
            ),
            None,
        )
        if candidate is None or field is None:
            raise VoiceAdjudicationError("rebind target candidate or field is missing")
        if (
            field.field_name != expected_field_name
            or field.text[expected_start:expected_end] != expected_passage
            or candidate.evidence.source_identity != expected_source_identity
            or candidate.evidence.passage != expected_passage
            or candidate.evidence.start != expected_start
            or candidate.evidence.end != expected_end
            or candidate.kind is not expected_candidate_kind
        ):
            raise VoiceAdjudicationError("rebind occurrence mismatch")
        if atom is not None and (
            atom.proposition != candidate.evidence.passage
            or atom.candidate_ids != (candidate.candidate_id,)
            or atom.evidence != (candidate.evidence,)
        ):
            raise VoiceAdjudicationError("fact atom must preserve the exact source span")
        receipt = _seal(
            FactAtomOwnerReceiptV2(
                semantic_draft_revision_identity=(
                    state.binding.semantic_draft_revision_identity
                ),
                event_authority_identity=state.binding.event_authority_identity,
                candidate_identity=target_candidate_identity,
                exact_source_span_sha256="sha256:"
                + hashlib.sha256(expected_passage.encode()).hexdigest(),
                disposition=disposition,
                resulting_atom=atom,
                governed_object_or_scope=governed_object_or_scope,
                adjudicator_identity=adjudicator_identity,
                adjudicated_at=adjudicated_at,
                decision_rationale=decision_rationale,
            )
        )
        provenance = _seal(
            FactAtomOwnerDecisionRebindProvenanceV1(
                story_identity=state.binding.semantic_draft_revision_identity,
                prior_candidate_identity=prior_candidate_identity,
                prior_candidate_provenance_class=(
                    prior_candidate_provenance_class
                ),
                target_candidate_identity=target_candidate_identity,
                source_identity=expected_source_identity,
                field_name=expected_field_name,
                passage=expected_passage,
                start=expected_start,
                end=expected_end,
                candidate_kind=expected_candidate_kind.value,
                disposition=disposition,
                decision_rationale=decision_rationale,
                owner_authorization=owner_authorization,
                target_receipt_identity=receipt.receipt_identity,
            ),
            field="provenance_identity",
        )
        receipts = (*state.fact_atom_receipts, receipt)
        latest = {item.candidate_identity: item for item in receipts}
        atoms = tuple(
            item.resulting_atom
            for item in latest.values()
            if item.disposition is CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM
            and item.resulting_atom is not None
        )
        bundle = finalize_bundle_identity(
            state.fact_atom_bundle.model_copy(
                update={
                    "revision": state.fact_atom_bundle.revision + 1,
                    "atoms": atoms,
                    "adjudication_receipt_identities": tuple(
                        item.receipt_identity for item in latest.values()
                    ),
                    "bundle_identity": ZERO,
                }
            )
        )
        payload = state.model_dump(mode="python")
        payload.update(
            {
                "schema_version": "3",
                "lifecycle": AdjudicationLifecycleV1.FACT_ATOMS_PARTIAL,
                "fact_atom_receipts": receipts,
                "fact_atom_rebind_provenance": (*existing_provenance, provenance),
                "fact_atom_bundle": bundle,
                "mechanic_claim_receipts": (),
                "mechanic_claims": (),
                "eligibility": None,
                "explicit_no_claim_reason": None,
                "prior_state_identity": state.state_identity,
                "state_identity": ZERO,
            }
        )
        # Validation precedes the single persistence call: no receipt-only or
        # provenance-only current state can become visible.
        rebound = VoiceStoryAdjudicationStateV3.model_validate(payload)
        return self.store.save(rebound)

    def finalize_fact_atoms(self, state):
        latest = {item.candidate_identity: item for item in state.fact_atom_receipts}
        active = [
            item
            for item in state.fact_atom_receipts
            if not any(
                newer.prior_receipt_identity == item.receipt_identity
                for newer in state.fact_atom_receipts
            )
        ]
        active_by_candidate: dict[str, list] = {}
        for item in active:
            active_by_candidate.setdefault(item.candidate_identity, []).append(item)
        if any(len(items) != 1 for items in active_by_candidate.values()):
            raise VoiceAdjudicationError(
                "candidate has duplicate active terminal receipts"
            )
        unresolved = [
            item.candidate_id
            for item in state.candidates
            if item.candidate_id not in latest
            or latest[item.candidate_id].disposition
            is CandidateOwnerDispositionV1.REQUIRES_QUALIFICATION
        ]
        if unresolved:
            raise VoiceAdjudicationError(
                "all extracted candidates require a terminal owner disposition"
            )
        return self.store.save(
            state.model_copy(
                update={
                    "lifecycle": AdjudicationLifecycleV1.FACT_ATOMS_FINALIZED,
                    "prior_state_identity": state.state_identity,
                    "state_identity": ZERO,
                }
            )
        )

    def adjudicate_mechanic_claim(
        self,
        state,
        *,
        mechanic_id,
        atom_roles: tuple[AtomRoleBindingV1, ...],
        satisfied_boundary_codes: tuple[str, ...],
        adjudicator_identity: str,
        adjudicated_at: datetime,
        supersession_reason: str | None = None,
    ):
        if state.lifecycle not in {
            AdjudicationLifecycleV1.FACT_ATOMS_FINALIZED,
            AdjudicationLifecycleV1.MECHANIC_CLAIMS_PARTIAL,
            AdjudicationLifecycleV1.MECHANIC_CLAIMS_FINALIZED,
        }:
            raise VoiceAdjudicationError("fact atoms are not finalized")
        known = {item.atom_id for item in state.fact_atom_bundle.atoms}
        referenced = {item for role in atom_roles for item in role.atom_ids}
        if not referenced <= known:
            raise VoiceAdjudicationError("mechanic claim references unapproved atom")
        role_names = tuple(item.role for item in atom_roles)
        matching_specs = tuple(
            item for item in PROGRAM_SPECS_V1 if item.mechanic_id is mechanic_id
        )
        if not any(
            set(role_names) == set(_required_roles(item.program_id))
            and set(item.required_boundary_codes) <= set(satisfied_boundary_codes)
            for item in matching_specs
        ):
            raise VoiceAdjudicationError(
                "mechanic role or boundary confirmation is not production-authorized"
            )
        prior = next(
            (
                item
                for item in reversed(state.mechanic_claim_receipts)
                if item.mechanic_claim.mechanic_id is mechanic_id
            ),
            None,
        )
        provisional_claim = MechanicEligibilityClaimV1(
            fact_atom_bundle_identity=state.fact_atom_bundle.bundle_identity,
            mechanic_id=mechanic_id,
            atom_roles=atom_roles,
            satisfied_boundary_codes=tuple(sorted(set(satisfied_boundary_codes))),
            adjudication_receipt_identity=ZERO,
            claim_identity=ZERO,
        )
        receipt = _seal_claim_receipt(
            MechanicClaimOwnerReceiptV1(
                semantic_draft_revision_identity=(
                    state.binding.semantic_draft_revision_identity
                ),
                fact_atom_bundle_identity=state.fact_atom_bundle.bundle_identity,
                mechanic_claim=provisional_claim,
                confirmed_role_bindings=atom_roles,
                confirmed_boundary_codes=tuple(sorted(set(satisfied_boundary_codes))),
                adjudicator_identity=adjudicator_identity,
                adjudicated_at=adjudicated_at,
                prior_receipt_identity=prior.receipt_identity if prior else None,
                supersession_reason=supersession_reason if prior else None,
            )
        )
        latest = {
            item.mechanic_claim.mechanic_id: item
            for item in (*state.mechanic_claim_receipts, receipt)
        }
        return self.store.save(
            state.model_copy(
                update={
                    "lifecycle": AdjudicationLifecycleV1.MECHANIC_CLAIMS_PARTIAL,
                    "mechanic_claim_receipts": (
                        *state.mechanic_claim_receipts,
                        receipt,
                    ),
                    "mechanic_claims": tuple(
                        item.mechanic_claim for item in latest.values()
                    ),
                    "eligibility": None,
                    "prior_state_identity": state.state_identity,
                    "state_identity": ZERO,
                }
            )
        )

    def finalize_claims(self, state):
        if not state.mechanic_claims:
            raise VoiceAdjudicationError(
                "claim finalization requires an explicit confirmed claim"
            )
        eligibility = evaluate_voice_eligibility_v1(
            bundle=state.fact_atom_bundle,
            claims=state.mechanic_claims,
            repetition_snapshot=state.repetition_snapshot,
        )
        return self.store.save(
            state.model_copy(
                update={
                    "lifecycle": AdjudicationLifecycleV1.MECHANIC_CLAIMS_FINALIZED,
                    "eligibility": eligibility,
                    "prior_state_identity": state.state_identity,
                    "state_identity": ZERO,
                }
            )
        )

    def choose_no_claim(self, state, *, reason: str):
        eligibility = evaluate_voice_eligibility_v1(
            bundle=state.fact_atom_bundle,
            claims=(),
            repetition_snapshot=state.repetition_snapshot,
        )
        return self.store.save(
            state.model_copy(
                update={
                    "lifecycle": AdjudicationLifecycleV1.NO_CLAIM,
                    "mechanic_claims": (),
                    "mechanic_claim_receipts": (),
                    "eligibility": eligibility,
                    "explicit_no_claim_reason": reason,
                    "prior_state_identity": state.state_identity,
                    "state_identity": ZERO,
                }
            )
        )

    def mark_stale(self, state, *, reason: str):
        return self.store.save(
            state.model_copy(
                update={
                    "lifecycle": AdjudicationLifecycleV1.STALE,
                    "eligibility": None,
                    "explicit_no_claim_reason": None,
                    "stale_reason": reason,
                    "prior_state_identity": state.state_identity,
                    "state_identity": ZERO,
                }
            )
        )


__all__ = ["VoiceAdjudicationApplicationServiceV1", "VoiceAdjudicationError"]


def _required_roles(program_id: str) -> tuple[str, ...]:
    """Frozen role names are owned by production materialization authority."""

    from pastila_scout.voice_deterministic_v2.production import (
        PRODUCTION_PROGRAM_BY_ID_V1,
    )

    return PRODUCTION_PROGRAM_BY_ID_V1[program_id].required_atom_roles

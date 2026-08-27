"""Desktop adapter over the owner-authoritative adjudication service."""

from __future__ import annotations

from pastila_scout.voice_adjudication_v2 import VoiceAdjudicationError
from pastila_scout.voice_fact_atoms_v2.models import FactAtomV1

from .voice_adjudication_actions import VoiceDesktopAdjudicationActionV1


class VoiceDesktopAdjudicationCoordinatorV1:
    def __init__(self, service):
        self.service = service

    def dispatch(self, value: VoiceDesktopAdjudicationActionV1):
        state = self.service.store.load(value.event_id)
        if state is None:
            raise VoiceAdjudicationError("adjudication state is unavailable")
        if value.action == "decide_fact":
            candidate = next(
                (
                    item
                    for item in state.candidates
                    if item.candidate_id == value.candidate_identity
                ),
                None,
            )
            if candidate is None:
                raise VoiceAdjudicationError("unknown extraction candidate")
            atom = None
            if value.atom_input is not None:
                atom = FactAtomV1(
                    atom_id=value.atom_input.atom_id,
                    kind=value.atom_input.atom_kind,
                    proposition=candidate.evidence.passage,
                    authority_class=candidate.evidence.authority_class,
                    evidence=(candidate.evidence,),
                    candidate_ids=(candidate.candidate_id,),
                    quantity=value.atom_input.quantity,
                    qualification_target_atom_ids=(
                        value.atom_input.qualification_target_atom_ids
                    ),
                    prohibits_event_projection=(
                        value.atom_input.prohibits_event_projection
                    ),
                )
            return self.service.decide_fact_atom(
                state,
                candidate_identity=value.candidate_identity,
                disposition=value.disposition,
                atom=atom,
                governed_object_or_scope=value.governed_object_or_scope,
                actor_or_subject_atom_ids=value.actor_or_subject_atom_ids,
                chronology_atom_ids=value.chronology_atom_ids,
                uncertainty_target_atom_ids=value.uncertainty_target_atom_ids,
                attribution_atom_ids=value.attribution_atom_ids,
                adjudicator_identity=value.owner_identity,
                adjudicated_at=value.occurred_at,
                decision_rationale=value.decision_rationale,
                supersession_reason=value.supersession_reason,
            )
        if value.action == "finalize_facts":
            return self.service.finalize_fact_atoms(state)
        if value.action == "confirm_mechanic_claim":
            return self.service.adjudicate_mechanic_claim(
                state,
                mechanic_id=value.mechanic_id,
                atom_roles=value.atom_roles,
                satisfied_boundary_codes=value.satisfied_boundary_codes,
                adjudicator_identity=value.owner_identity,
                adjudicated_at=value.occurred_at,
                supersession_reason=value.supersession_reason,
            )
        if value.action == "finalize_claims":
            return self.service.finalize_claims(state)
        if value.action == "choose_no_claim":
            return self.service.choose_no_claim(state, reason=value.no_claim_reason)
        raise VoiceAdjudicationError("unknown Desktop adjudication action")


__all__ = ["VoiceDesktopAdjudicationCoordinatorV1"]

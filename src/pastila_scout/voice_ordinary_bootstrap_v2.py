"""Fail-closed ordinary-story bootstrap for deterministic Voice V2."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pastila_scout.active_project_v1 import ActiveProjectStoreV1
from pastila_scout.editor.generation.semantic_draft_v2 import (
    PastilaEditorSemanticDraftV2,
)
from pastila_scout.editor_application_v1 import load_editor_operational_result_v1
from pastila_scout.editor_generation_authority_v1.canonical import (
    canonical_value,
    semantic_fingerprint,
)
from pastila_scout.event_authority_v1 import render_authority_segment
from pastila_scout.voice_adjudication_v2 import (
    AdjudicationLifecycleV1,
    AuthorityTextV1,
    CandidateOwnerDispositionV1,
)
from pastila_scout.voice_canonical_state_v2 import (
    ZERO,
    CanonicalVoiceLifecycleV2,
    CanonicalVoiceStoryStateV2,
    CanonicalVoiceWorkspaceStateV2,
    CanonicalVoiceWorkspaceStoreV2,
)
from pastila_scout.voice_deterministic_v2.models import MechanicIdV1
from pastila_scout.voice_eligibility_v2 import evaluate_voice_eligibility_v1
from pastila_scout.voice_eligibility_v2.models import AtomRoleBindingV1
from pastila_scout.voice_executor_v2 import ZERO_ACTIVATION_POLICY_V1
from pastila_scout.voice_executor_v2.models import VoiceProductionActivationPolicyV1
from pastila_scout.voice_fact_atoms_v2.extraction_v2 import TypedAuthorityFieldInputV2
from pastila_scout.voice_fact_atoms_v2.models import (
    AtomKind,
    AuthorityClass,
    CandidateKind,
    CompleteQuantityV1,
    FactAtomV1,
)
from pastila_scout.voice_repetition_v2 import (
    derive_repetition_snapshot_v1,
    finalize_order_authority_v1,
)
from pastila_scout.voice_repetition_v2.models import (
    EpisodeOrderAuthorityV1,
    PublicationStateV1,
)
from pastila_scout.voice_workflow_v2 import (
    semantic_draft_revision_identity,
    sha256_identity,
)
from pastila_scout.voice_workflow_v2.models import VoiceStoryBindingV1

_AUTOMATIC_POLICY_IDENTITY = "daily-use-high-confidence-numeric-v1"
_AUTOMATIC_ABSTENTION_PREFIX = "Deterministic daily-use policy abstained"
_QUANTITY_PARTS = re.compile(
    r"(?i)^(?:(aproximativ|circa|peste|cel puțin|maximum|minimum)\s+)?"
    r"(\d[\d. ,]*)"
    r"(?:%|\s+(?:de\s+)?(lei|euro|dolari|persoane|oameni|tranzacții|state|metri|ani|luni|zile|ore))$"
)


class OrdinaryVoiceBootstrapStatusV2(StrEnum):
    ADJUDICATION_REQUIRED = "adjudication_required"
    FACT_ADJUDICATION_INCOMPLETE = "fact_adjudication_incomplete"
    MECHANIC_ADJUDICATION_REQUIRED = "mechanic_adjudication_required"
    SAFE_NO_PROGRAM = "safe_no_program"
    ELIGIBILITY_AVAILABLE = "eligibility_available"
    STALE = "stale"
    INTEGRITY_FAILURE = "integrity_failure"


@dataclass(frozen=True, slots=True)
class OrdinaryVoiceBootstrapResultV2:
    event_id: int
    status: OrdinaryVoiceBootstrapStatusV2
    diagnostic_code: str
    state_identity: str | None = None


class OrdinaryPersistedStoryVoiceBootstrapV2:
    """Consumes persisted story and owner receipts; never infers semantic claims."""

    def __init__(
        self,
        *,
        project_store: ActiveProjectStoreV1,
        canonical_store,
        adjudication,
        activation_policy: VoiceProductionActivationPolicyV1 = ZERO_ACTIVATION_POLICY_V1,
        daily_use_automation: bool = False,
    ):
        self.project_store = project_store
        self.canonical_store: CanonicalVoiceWorkspaceStoreV2 = canonical_store
        self.adjudication = adjudication
        self.activation_policy = activation_policy
        self.daily_use_automation = daily_use_automation

    def reevaluate(self, event_id: int) -> OrdinaryVoiceBootstrapResultV2:
        try:
            # Voice refreshes also run while an Editor batch is active.  A normal
            # ``load()`` performs crash recovery by changing RUNNING work back to
            # PENDING, which can invalidate the batch between generation and
            # output persistence.  Runtime observers must never recover live work.
            runtime_loader = getattr(
                self.project_store, "load_runtime_state", self.project_store.load
            )
            project = runtime_loader()
            if project is None:
                return self._result(
                    event_id, "INTEGRITY_FAILURE", "active_project_missing"
                )
            material = next(
                (
                    item
                    for item in project.editor_materials
                    if item.event_id == event_id
                ),
                None,
            )
            event = next(
                (
                    item
                    for item in project.scout_input.ranked_events
                    if item.event_id == event_id
                ),
                None,
            )
            if (
                material is None
                or event is None
                or not material.output_path
                or not material.payload_sha256
            ):
                return self._result(
                    event_id, "INTEGRITY_FAILURE", "ordinary_story_missing"
                )
            loaded = load_editor_operational_result_v1(
                path=Path(material.output_path), payload_sha256=material.payload_sha256
            )
            draft = loaded.draft
            if type(draft) is not PastilaEditorSemanticDraftV2:
                return self._result(event_id, "INTEGRITY_FAILURE", "native_v2_required")
            story = next(
                (item for item in draft.stories if item.event_id == event_id), None
            )
            authority = event.event_authority_bundle
            if story is None or authority is None:
                return self._result(
                    event_id, "INTEGRITY_FAILURE", "event_authority_missing"
                )
            if semantic_fingerprint(canonical_value(authority)) != (
                story.factual_summary.authority_bundle_identity
            ):
                return self._result(
                    event_id, "INTEGRITY_FAILURE", "event_authority_identity_mismatch"
                )
            binding = VoiceStoryBindingV1(
                story_material_reference=material.reference,
                semantic_draft_revision_identity=semantic_draft_revision_identity(
                    draft
                ),
                event_id=event_id,
                factual_summary_sha256=sha256_identity(story.factual_summary.text),
                event_authority_identity=story.factual_summary.authority_bundle_identity,
            )
            authority_texts = tuple(
                self._authority_text(segment, binding) for segment in authority.segments
            )
            extraction_fields = tuple(
                field
                for segment in authority.segments
                for field in self._extraction_fields(segment, binding)
            )
            order = self._order(project, draft, event_id)
            snapshot = derive_repetition_snapshot_v1(
                ledger=self.canonical_store.acceptance_store.current_ledger(),
                order_authority=order,
                event_id=event_id,
            ).snapshot
            adjudication = self.adjudication.load_for_story(
                binding=binding,
                authority_texts=authority_texts,
                extraction_fields=extraction_fields,
                repetition_snapshot=snapshot,
            )
            if adjudication is None:
                adjudication = self.adjudication.begin_v2(
                    binding=binding,
                    story_position=order.ordered_event_ids.index(event_id) + 1,
                    authority_texts=authority_texts,
                    extraction_fields=extraction_fields,
                    repetition_snapshot=snapshot,
                )
                if self.daily_use_automation and not self._requires_owner_review(
                    adjudication
                ):
                    adjudication = self._automate_or_abstain(adjudication)
                else:
                    return self._result(
                        event_id,
                        "ADJUDICATION_REQUIRED",
                        "owner_fact_adjudication_required",
                    )
            lifecycle = adjudication.lifecycle
            if (
                self.daily_use_automation
                and lifecycle is AdjudicationLifecycleV1.NO_CLAIM
                and (adjudication.explicit_no_claim_reason or "").startswith(
                    _AUTOMATIC_ABSTENTION_PREFIX
                )
                and not self._requires_owner_review(adjudication)
            ):
                adjudication = self._automate_or_abstain(adjudication)
                lifecycle = adjudication.lifecycle
            if lifecycle is AdjudicationLifecycleV1.STALE:
                return self._result(
                    event_id, "STALE", adjudication.stale_reason or "adjudication_stale"
                )
            if lifecycle in {
                AdjudicationLifecycleV1.CANDIDATES_EXTRACTED,
                AdjudicationLifecycleV1.FACT_ATOMS_PARTIAL,
            }:
                if self.daily_use_automation and not self._requires_owner_review(
                    adjudication
                ):
                    adjudication = self._automate_or_abstain(adjudication)
                    lifecycle = adjudication.lifecycle
                else:
                    return self._result(
                        event_id,
                        "FACT_ADJUDICATION_INCOMPLETE",
                        "owner_fact_adjudication_incomplete",
                    )
            if lifecycle in {
                AdjudicationLifecycleV1.FACT_ATOMS_FINALIZED,
                AdjudicationLifecycleV1.MECHANIC_CLAIMS_PARTIAL,
            }:
                return self._result(
                    event_id,
                    "MECHANIC_ADJUDICATION_REQUIRED",
                    "owner_mechanic_adjudication_required",
                )
            if lifecycle not in {
                AdjudicationLifecycleV1.MECHANIC_CLAIMS_FINALIZED,
                AdjudicationLifecycleV1.NO_CLAIM,
            }:
                return self._result(
                    event_id, "INTEGRITY_FAILURE", "unknown_adjudication_lifecycle"
                )
            eligibility = evaluate_voice_eligibility_v1(
                bundle=adjudication.fact_atom_bundle,
                claims=adjudication.mechanic_claims,
                repetition_snapshot=snapshot,
            )
            if adjudication.eligibility != eligibility:
                return self._result(
                    event_id, "INTEGRITY_FAILURE", "adjudication_eligibility_mismatch"
                )
            existing = self.canonical_store.load_story(event_id)
            if existing is not None and self._is_current(
                existing,
                adjudication.state_identity,
                snapshot.snapshot_identity,
                order.authority_identity,
            ):
                status = (
                    "SAFE_NO_PROGRAM"
                    if not existing.program_eligibility.shortlist
                    else "ELIGIBILITY_AVAILABLE"
                )
                return self._result(
                    event_id, status, "canonical_state_reused", existing.state_identity
                )
            state = CanonicalVoiceStoryStateV2(
                lifecycle=CanonicalVoiceLifecycleV2.ELIGIBILITY_AVAILABLE,
                binding=binding,
                authored_draft=draft,
                fact_atom_bundle=adjudication.fact_atom_bundle,
                mechanic_claims=adjudication.mechanic_claims,
                repetition_snapshot=snapshot,
                program_eligibility=eligibility,
                order_authority=order,
                adjudication_state_identity=adjudication.state_identity,
                fact_atom_receipt_identities=tuple(
                    item.receipt_identity for item in adjudication.fact_atom_receipts
                ),
                mechanic_claim_receipt_identities=tuple(
                    item.receipt_identity
                    for item in adjudication.mechanic_claim_receipts
                ),
                activation_policy_identity=self.activation_policy.policy_identity,
            )
            if self.canonical_store.load_workspace() is None:
                self.canonical_store.save_workspace(
                    CanonicalVoiceWorkspaceStateV2(
                        project_identity=self.canonical_store.project_identity,
                        order_authority=order,
                    )
                )
            saved = self.canonical_store.save_story(state)
            workspace = self.canonical_store.load_workspace()
            if workspace is not None and workspace.order_authority != order:
                self.canonical_store.save_workspace(
                    workspace.model_copy(
                        update={"order_authority": order, "state_identity": ZERO}
                    )
                )
            status = (
                "SAFE_NO_PROGRAM"
                if not eligibility.shortlist
                else "ELIGIBILITY_AVAILABLE"
            )
            return self._result(
                event_id,
                status,
                "canonical_eligibility_persisted",
                saved.state_identity,
            )
        except (OSError, TypeError, ValueError) as exc:
            return self._result(
                event_id,
                "INTEGRITY_FAILURE",
                f"ordinary_story_bootstrap_failed:{type(exc).__name__}:{exc}",
            )

    @staticmethod
    def _result(event_id, status, code, identity=None):
        return OrdinaryVoiceBootstrapResultV2(
            event_id, OrdinaryVoiceBootstrapStatusV2[status], code, identity
        )

    @staticmethod
    def _requires_owner_review(adjudication) -> bool:
        ambiguous = {
            CandidateKind.ALLEGATION_MARKER,
            CandidateKind.UNCERTAINTY_MARKER,
        }
        return any(item.kind in ambiguous for item in adjudication.candidates)

    def _automate_or_abstain(self, state):
        automated = self._automate_high_confidence_numeric(state)
        if automated is not None:
            return automated
        if state.lifecycle is AdjudicationLifecycleV1.NO_CLAIM:
            return state
        return self.adjudication.choose_no_claim(
            state,
            reason=(
                f"{_AUTOMATIC_ABSTENTION_PREFIX} because no owner-independent "
                "mechanic path was authorized."
            ),
        )

    def _automate_high_confidence_numeric(self, state):
        """Adjudicate one explicit summary quantity without semantic inference."""

        latest_receipts = {
            item.candidate_identity: item for item in state.fact_atom_receipts
        }
        if state.mechanic_claim_receipts or any(
            item.disposition is not CandidateOwnerDispositionV1.REJECT
            for item in latest_receipts.values()
        ):
            return None
        disallowed = {
            CandidateKind.ALLEGATION_MARKER,
            CandidateKind.UNCERTAINTY_MARKER,
            CandidateKind.ATTRIBUTION_MARKER,
        }
        if any(item.kind in disallowed for item in state.candidates):
            return None
        fields = {item.source_identity: item for item in state.extraction_fields}
        quantities = tuple(
            item
            for item in state.candidates
            if item.kind is CandidateKind.COMPLETE_QUANTITY
            and fields[item.evidence.source_identity].field_name == "summary"
        )
        if not quantities:
            return None
        parsed_quantities = tuple(
            (
                item,
                _QUANTITY_PARTS.fullmatch(item.evidence.passage.strip()),
            )
            for item in quantities
        )
        if any(match is None for _, match in parsed_quantities):
            return None
        semantic_keys = {
            (
                (match.group(1) or "").casefold(),
                re.sub(r"[\s.,]", "", match.group(2)),
                match.group(3).casefold(),
            )
            for _, match in parsed_quantities
            if match is not None
        }
        if len(semantic_keys) != 1:
            return None
        quantity_candidate, match = parsed_quantities[0]
        assert match is not None
        if match.group(3).casefold() not in {"lei", "euro", "dolari"}:
            return None
        field = fields[quantity_candidate.evidence.source_identity]
        proposition = field.text.strip()
        if (
            proposition != field.text
            or len(proposition) > 500
            or len(proposition.split()) < 4
            or quantity_candidate.evidence.passage not in proposition
        ):
            return None
        state = self.adjudication.add_exact_candidate(
            state,
            source_identity=field.source_identity,
            start=0,
            end=len(field.text),
            kind=CandidateKind.EXACT_SPAN,
        )
        proposition_candidate = next(
            item
            for item in state.candidates
            if item.kind is CandidateKind.EXACT_SPAN
            and item.evidence.source_identity == field.source_identity
            and item.evidence.passage == proposition
        )
        approximation, numeric_surface, unit = match.groups()
        semantics = {
            None: "exact",
            "aproximativ": "approximate",
            "circa": "approximate",
            "peste": "lower_bound",
            "cel puțin": "lower_bound",
            "maximum": "upper_bound",
            "minimum": "lower_bound",
        }[approximation.casefold() if approximation else None]
        seed = hashlib.sha256(
            f"{state.binding.event_id}|{quantity_candidate.candidate_id}".encode()
        ).hexdigest()[:24]
        quantity_atom = FactAtomV1(
            atom_id=f"auto-quantity:{seed}",
            kind=AtomKind.COMPLETE_QUANTITY,
            proposition=quantity_candidate.evidence.passage,
            authority_class=AuthorityClass.EVENT,
            evidence=(quantity_candidate.evidence,),
            candidate_ids=(quantity_candidate.candidate_id,),
            quantity=CompleteQuantityV1(
                exact_surface=quantity_candidate.evidence.passage,
                numeric_surface=numeric_surface.strip(),
                approximation=approximation,
                bound_semantics=semantics,
                unit_or_currency=unit,
                subject_scope=proposition,
            ),
        )
        proposition_atom = FactAtomV1(
            atom_id=f"auto-proposition:{seed}",
            kind=AtomKind.EVENT_PROPOSITION,
            proposition=proposition,
            authority_class=AuthorityClass.EVENT,
            evidence=(proposition_candidate.evidence,),
            candidate_ids=(proposition_candidate.candidate_id,),
        )
        now = datetime.now(UTC)
        accepted = {
            quantity_candidate.candidate_id: quantity_atom,
            proposition_candidate.candidate_id: proposition_atom,
        }
        for candidate in state.candidates:
            if candidate.candidate_id in latest_receipts:
                continue
            atom = accepted.get(candidate.candidate_id)
            state = self.adjudication.decide_fact_atom(
                state,
                candidate_identity=candidate.candidate_id,
                disposition=(
                    CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM
                    if atom is not None
                    else CandidateOwnerDispositionV1.REJECT
                ),
                atom=atom,
                adjudicator_identity=_AUTOMATIC_POLICY_IDENTITY,
                adjudicated_at=now,
                decision_rationale=(
                    "Deterministic exact-span numeric policy accepted the governed atom."
                    if atom is not None
                    else "Deterministic numeric policy rejected a non-required surface candidate."
                ),
            )
        state = self.adjudication.finalize_fact_atoms(state)
        state = self.adjudication.adjudicate_mechanic_claim(
            state,
            mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
            atom_roles=(
                AtomRoleBindingV1(
                    role="complete_quantity", atom_ids=(quantity_atom.atom_id,)
                ),
                AtomRoleBindingV1(
                    role="quantity_object", atom_ids=(proposition_atom.atom_id,)
                ),
            ),
            satisfied_boundary_codes=(
                "no_value_judgment",
                "preserve_approximation_attribution_period_denominator_scope",
            ),
            adjudicator_identity=_AUTOMATIC_POLICY_IDENTITY,
            adjudicated_at=now,
        )
        return self.adjudication.finalize_claims(state)

    @staticmethod
    def _authority_text(segment, binding):
        text = render_authority_segment(segment)
        return AuthorityTextV1(
            authority_class=AuthorityClass.EVENT,
            authority_identity=binding.event_authority_identity,
            source_identity=f"article:{segment.article_id}:{segment.source_id}",
            text=text,
            text_sha256="sha256:" + hashlib.sha256(text.encode()).hexdigest(),
        )

    @staticmethod
    def _extraction_fields(segment, binding):
        result = []
        for field_name in ("title", "summary"):
            text = getattr(segment, field_name)
            if not text:
                continue
            result.append(
                TypedAuthorityFieldInputV2(
                    authority_class=AuthorityClass.EVENT,
                    authority_identity=binding.event_authority_identity,
                    article_id=segment.article_id,
                    source_id=segment.source_id,
                    field_name=field_name,
                    text=text,
                    text_sha256="sha256:"
                    + hashlib.sha256(text.encode("utf-8")).hexdigest(),
                )
            )
        return tuple(result)

    def _order(self, project, draft, event_id):
        workspace = self.canonical_store.load_workspace()
        if workspace is not None and event_id in (
            workspace.order_authority.ordered_event_ids
        ):
            return workspace.order_authority
        ordered = tuple(item.event_id for item in project.editor_materials)
        if event_id not in ordered:
            ordered = tuple(item.event_id for item in draft.stories)
        return finalize_order_authority_v1(
            EpisodeOrderAuthorityV1(
                episode_id=project.project_id,
                episode_ordinal=1,
                ordered_event_ids=ordered,
                publication_state=PublicationStateV1.UNPUBLISHED,
            )
        )

    def _is_current(
        self, state, adjudication_identity, snapshot_identity, order_identity
    ):
        return (
            state.adjudication_state_identity == adjudication_identity
            and state.repetition_snapshot.snapshot_identity == snapshot_identity
            and state.order_authority.authority_identity == order_identity
            and state.activation_policy_identity
            == self.activation_policy.policy_identity
            and state.lifecycle is CanonicalVoiceLifecycleV2.ELIGIBILITY_AVAILABLE
        )


__all__ = [
    "OrdinaryPersistedStoryVoiceBootstrapV2",
    "OrdinaryVoiceBootstrapResultV2",
    "OrdinaryVoiceBootstrapStatusV2",
]

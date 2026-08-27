from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from types import SimpleNamespace

from pastila_scout.contracts.scout_editor import (
    EventAuthorityBundleV1,
    EventAuthoritySegmentV1,
)
from pastila_scout.desktop_v1.voice_adjudication_actions import (
    VoiceDesktopAdjudicationActionV1,
)
from pastila_scout.desktop_v1.voice_v2_composition import compose_voice_v2_production
from pastila_scout.desktop_v1.voice_v2_interaction import VoiceDesktopActionInputV2
from pastila_scout.desktop_v1.voice_v2_workflow import VoiceDesktopContextRegistryV2
from pastila_scout.editor_generation_authority_v1.canonical import (
    canonical_value,
    semantic_fingerprint,
)
from pastila_scout.voice_adjudication_v2 import (
    AdjudicationLifecycleV1,
    CandidateOwnerDispositionV1,
)
from pastila_scout.voice_deterministic_v2.models import MechanicIdV1
from pastila_scout.voice_eligibility_v2.models import AtomRoleBindingV1
from pastila_scout.voice_fact_atoms_v2.models import (
    AtomKind,
    AuthorityClass,
    CandidateKind,
    CompleteQuantityV1,
    FactAtomV1,
)
from pastila_scout.voice_ordinary_bootstrap_v2 import (
    OrdinaryPersistedStoryVoiceBootstrapV2,
    OrdinaryVoiceBootstrapResultV2,
    OrdinaryVoiceBootstrapStatusV2,
)
from tests.voice_v2_synthetic_fixtures import (
    synthetic_canonical_state_v2,
    synthetic_canonical_store_v2,
)


class _ProjectStore:
    def __init__(self, project):
        self.project = project

    def load(self):
        raise AssertionError("live Voice refresh must not run startup recovery")

    def load_runtime_state(self):
        return self.project


def _bootstrap(
    tmp_path,
    monkeypatch,
    *,
    title="Fapt confirmat",
    summary="Proiectul costă aproximativ 37.000 de euro.",
    second_summary=None,
):
    draft = synthetic_canonical_state_v2().authored_draft
    material = SimpleNamespace(
        event_id=1,
        reference="material:1",
        output_path=str(tmp_path / "ordinary-v2.json"),
        payload_sha256="sha256:" + "a" * 64,
    )
    segment = EventAuthoritySegmentV1(
        article_id=1,
        source_id="source-1",
        source_name="Sursa",
        url="https://example.test/1",
        title=title,
        summary=summary,
        canonical=True,
        truncated=False,
    )
    segments = (segment,)
    if second_summary is not None:
        segments += (
            EventAuthoritySegmentV1(
                article_id=2,
                source_id="source-2",
                source_name="Sursa 2",
                url="https://example.test/2",
                title="Confirmare independentă",
                summary=second_summary,
                canonical=False,
                truncated=False,
            ),
        )
    authority = EventAuthorityBundleV1(
        authority_version="event-authority-bundle-v1",
        event_id=1,
        segments=segments,
    )
    story = draft.stories[0]
    story = story.model_copy(
        update={
            "factual_summary": story.factual_summary.model_copy(
                update={
                    "authority_bundle_identity": semantic_fingerprint(
                        canonical_value(authority)
                    )
                }
            )
        }
    )
    draft = type(draft).assemble(
        episode_id=draft.episode_id,
        mode=draft.mode,
        stories=(story,),
        provenance_references=draft.provenance_references,
        generation_receipts=draft.generation_receipts,
    )
    event = SimpleNamespace(
        event_id=1,
        event_authority_bundle=authority,
    )
    project = SimpleNamespace(
        project_id="project-1",
        editor_materials=(material,),
        scout_input=SimpleNamespace(ranked_events=(event,)),
    )
    monkeypatch.setattr(
        "pastila_scout.voice_ordinary_bootstrap_v2.load_editor_operational_result_v1",
        lambda **_: SimpleNamespace(draft=draft),
    )
    canonical = synthetic_canonical_store_v2(tmp_path)
    composition = compose_voice_v2_production(
        project_path=(tmp_path / "active-project.json").resolve(),
        project_identity="project-1",
    )
    bootstrap = OrdinaryPersistedStoryVoiceBootstrapV2(
        project_store=_ProjectStore(project),
        canonical_store=canonical,
        adjudication=composition.adjudication_application,
        activation_policy=composition.application.activation_policy,
    )
    return bootstrap, composition, canonical


def test_ordinary_story_requires_adjudication_then_safe_no_claim(tmp_path, monkeypatch):
    bootstrap, composition, canonical = _bootstrap(tmp_path, monkeypatch)
    first = bootstrap.reevaluate(1)
    assert first.status is OrdinaryVoiceBootstrapStatusV2.ADJUDICATION_REQUIRED, (
        first.diagnostic_code
    )
    state = composition.adjudication_store.load(1)
    assert state.lifecycle is AdjudicationLifecycleV1.CANDIDATES_EXTRACTED
    assert state.schema_version == "2"
    assert state.fact_atom_bundle.extraction_policy_version == (
        "voice-fact-candidate-extraction-v2"
    )
    assert all(":field:" in item.evidence.source_identity for item in state.candidates)
    assert all(
        item.evidence.passage not in {"Sursa", "Titlu", "Rezumat", "Publicat"}
        for item in state.candidates
    )

    no_claim = composition.adjudication_application.choose_no_claim(
        state, reason="Owner confirmed no safe mechanic claim."
    )
    second = bootstrap.reevaluate(1)
    assert second.status is OrdinaryVoiceBootstrapStatusV2.SAFE_NO_PROGRAM
    persisted = canonical.load_story(1)
    assert persisted.adjudication_state_identity == no_claim.state_identity
    assert persisted.program_eligibility.shortlist == ()
    assert bootstrap.reevaluate(1).state_identity == persisted.state_identity


def test_daily_use_automation_builds_high_confidence_numeric_eligibility(
    tmp_path, monkeypatch
):
    bootstrap, composition, canonical = _bootstrap(tmp_path, monkeypatch)
    bootstrap.daily_use_automation = True

    result = bootstrap.reevaluate(1)

    assert result.status is OrdinaryVoiceBootstrapStatusV2.ELIGIBILITY_AVAILABLE
    assert result.diagnostic_code == "canonical_eligibility_persisted"
    persisted = canonical.load_story(1)
    assert persisted.program_eligibility.shortlist
    adjudication = bootstrap.adjudication.store.load(1)
    assert adjudication.lifecycle is AdjudicationLifecycleV1.MECHANIC_CLAIMS_FINALIZED
    assert {item.kind for item in adjudication.fact_atom_bundle.atoms} == {
        AtomKind.COMPLETE_QUANTITY,
        AtomKind.EVENT_PROPOSITION,
    }
    assert all(
        item.adjudicator_identity == "daily-use-high-confidence-numeric-v1"
        for item in (
            *adjudication.fact_atom_receipts,
            *adjudication.mechanic_claim_receipts,
        )
    )
    composition.context_registry._bootstrap = bootstrap
    loaded = composition.desktop_workflow.dispatch(
        VoiceDesktopActionInputV2(action="load", event_id=1)
    )
    assert loaded.preview_text == ""
    assert canonical.acceptance_store.current_draft() is None
    presentation = composition.desktop_workflow.dispatch(
        VoiceDesktopActionInputV2(action="refresh", event_id=1)
    )
    assert presentation.interaction.title == "Comentariu acid: generat"
    assert presentation.preview_text
    repeated = composition.desktop_workflow.dispatch(
        VoiceDesktopActionInputV2(action="refresh", event_id=1)
    )
    assert repeated.interaction.title == "Comentariu acid: generat"
    assert repeated.preview_text == presentation.preview_text
    assert repeated.interaction.diagnostic_code is None


def test_context_registry_does_not_load_persisted_context_after_bootstrap_failure():
    class FailedBootstrap:
        @staticmethod
        def reevaluate(event_id):
            return OrdinaryVoiceBootstrapResultV2(
                event_id=event_id,
                status=OrdinaryVoiceBootstrapStatusV2.STALE,
                diagnostic_code="story_revision_or_binding_changed",
            )

    class PersistedLoader:
        @staticmethod
        def load(event_id):
            raise AssertionError(f"stale context loaded for {event_id}")

    registry = VoiceDesktopContextRegistryV2(PersistedLoader(), FailedBootstrap())

    assert registry.load(1) is None
    assert registry.bootstrap_result(1).status is OrdinaryVoiceBootstrapStatusV2.STALE


def test_daily_use_numeric_policy_upgrades_its_prior_safe_abstention(
    tmp_path, monkeypatch
):
    bootstrap, composition, _canonical = _bootstrap(tmp_path, monkeypatch)
    assert (
        bootstrap.reevaluate(1).status
        is OrdinaryVoiceBootstrapStatusV2.ADJUDICATION_REQUIRED
    )
    state = composition.adjudication_store.load(1)
    harmless = next(
        item for item in state.candidates if item.kind is CandidateKind.NAMED_ENTITY
    )
    state = composition.adjudication_application.decide_fact_atom(
        state,
        candidate_identity=harmless.candidate_id,
        disposition=CandidateOwnerDispositionV1.REJECT,
        atom=None,
        adjudicator_identity="owner",
        adjudicated_at=datetime(2026, 8, 25, tzinfo=UTC),
        decision_rationale="Owner rejected a fragment that is irrelevant to numeric automation.",
    )
    composition.adjudication_application.choose_no_claim(
        state,
        reason=(
            "Deterministic daily-use policy abstained because no "
            "owner-independent mechanic path was authorized."
        ),
    )
    bootstrap.daily_use_automation = True

    result = bootstrap.reevaluate(1)

    assert result.status is OrdinaryVoiceBootstrapStatusV2.ELIGIBILITY_AVAILABLE
    assert (
        composition.adjudication_store.load(1).lifecycle
        is AdjudicationLifecycleV1.MECHANIC_CLAIMS_FINALIZED
    )


def test_daily_use_numeric_policy_abstains_on_attributed_quantity(
    tmp_path, monkeypatch
):
    bootstrap, composition, canonical = _bootstrap(
        tmp_path,
        monkeypatch,
        summary="Potrivit raportului, proiectul costă 37.000 de euro.",
    )
    bootstrap.daily_use_automation = True

    result = bootstrap.reevaluate(1)

    assert result.status is OrdinaryVoiceBootstrapStatusV2.SAFE_NO_PROGRAM
    assert canonical.load_story(1).program_eligibility.shortlist == ()
    assert (
        composition.adjudication_store.load(1).lifecycle
        is AdjudicationLifecycleV1.NO_CLAIM
    )


def test_daily_use_numeric_policy_accepts_identical_multi_source_quantity(
    tmp_path, monkeypatch
):
    summary = "Proiectul costă aproximativ 37.000 de euro."
    bootstrap, _composition, canonical = _bootstrap(
        tmp_path,
        monkeypatch,
        summary=summary,
        second_summary=summary,
    )
    bootstrap.daily_use_automation = True

    result = bootstrap.reevaluate(1)

    assert result.status is OrdinaryVoiceBootstrapStatusV2.ELIGIBILITY_AVAILABLE
    assert canonical.load_story(1).program_eligibility.shortlist


def test_daily_use_numeric_policy_rejects_conflicting_multi_source_qualifiers(
    tmp_path, monkeypatch
):
    bootstrap, _composition, canonical = _bootstrap(
        tmp_path,
        monkeypatch,
        summary="Proiectul costă aproximativ 37.000 de euro.",
        second_summary="Proiectul costă peste 37.000 de euro.",
    )
    bootstrap.daily_use_automation = True

    result = bootstrap.reevaluate(1)

    assert result.status is OrdinaryVoiceBootstrapStatusV2.SAFE_NO_PROGRAM
    assert canonical.load_story(1).program_eligibility.shortlist == ()


def test_daily_use_money_program_rejects_non_monetary_quantity(tmp_path, monkeypatch):
    summary = "Republica marchează 35 de ani de independență."
    bootstrap, _composition, canonical = _bootstrap(
        tmp_path,
        monkeypatch,
        summary=summary,
        second_summary=summary,
    )
    bootstrap.daily_use_automation = True

    result = bootstrap.reevaluate(1)

    assert result.status is OrdinaryVoiceBootstrapStatusV2.SAFE_NO_PROGRAM
    assert canonical.load_story(1).program_eligibility.shortlist == ()


def test_desktop_reports_adjudication_required_truthfully(tmp_path, monkeypatch):
    bootstrap, composition, _ = _bootstrap(tmp_path, monkeypatch)
    composition.context_registry._bootstrap = bootstrap
    presentation = composition.desktop_workflow.dispatch(
        VoiceDesktopActionInputV2(action="refresh", event_id=1)
    )
    assert presentation.interaction.title == "Comentariu acid: adjudicare necesară"
    assert "Confirmă faptele" in presentation.interaction.message
    completed = composition.desktop_workflow.dispatch(
        VoiceDesktopAdjudicationActionV1(
            event_id=1,
            action="choose_no_claim",
            owner_identity="desktop-owner",
            occurred_at=datetime(2026, 8, 23, tzinfo=UTC),
            no_claim_reason="Owner confirmed no safe construction.",
        )
    )
    assert completed.interaction.title == "Comentariu acid: fără construcție eligibilă"
    assert (
        composition.adjudication_store.load(1).lifecycle
        is AdjudicationLifecycleV1.NO_CLAIM
    )


def test_finalized_claim_bootstraps_real_program_eligibility(tmp_path, monkeypatch):
    bootstrap, composition, canonical = _bootstrap(tmp_path, monkeypatch)
    assert (
        bootstrap.reevaluate(1).status
        is OrdinaryVoiceBootstrapStatusV2.ADJUDICATION_REQUIRED
    )
    service = composition.adjudication_application
    state = composition.adjudication_store.load(1)
    source = next(
        item for item in state.extraction_fields if item.field_name == "summary"
    )
    proposition = "Proiectul costă aproximativ 37.000 de euro."
    quantity = "aproximativ 37.000 de euro"
    for surface, kind in (
        (proposition, CandidateKind.EXACT_SPAN),
        (quantity, CandidateKind.COMPLETE_QUANTITY),
    ):
        start = source.text.index(surface)
        state = service.add_exact_candidate(
            state,
            source_identity=source.source_identity,
            start=start,
            end=start + len(surface),
            kind=kind,
        )
    candidates = {item.evidence.passage: item for item in state.candidates}
    proposition_candidate = candidates[proposition]
    quantity_candidate = candidates[quantity]
    proposition_atom = FactAtomV1(
        atom_id="event-proposition",
        kind=AtomKind.EVENT_PROPOSITION,
        proposition=proposition,
        authority_class=AuthorityClass.EVENT,
        evidence=(proposition_candidate.evidence,),
        candidate_ids=(proposition_candidate.candidate_id,),
    )
    quantity_atom = FactAtomV1(
        atom_id="complete-quantity",
        kind=AtomKind.COMPLETE_QUANTITY,
        proposition=quantity,
        authority_class=AuthorityClass.EVENT,
        evidence=(quantity_candidate.evidence,),
        candidate_ids=(quantity_candidate.candidate_id,),
        quantity=CompleteQuantityV1(
            exact_surface=quantity,
            numeric_surface="37.000",
            approximation="aproximativ",
            bound_semantics="approximate",
            unit_or_currency="euro",
            subject_scope="project cost",
        ),
    )
    now = datetime(2026, 8, 23, tzinfo=UTC)
    for candidate, atom in (
        (proposition_candidate, proposition_atom),
        (quantity_candidate, quantity_atom),
    ):
        state = service.decide_fact_atom(
            state,
            candidate_identity=candidate.candidate_id,
            disposition=CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM,
            atom=atom,
            adjudicator_identity="owner",
            adjudicated_at=now,
            decision_rationale="Owner accepted this exact atom.",
        )
    decided = {item.candidate_identity for item in state.fact_atom_receipts}
    for remaining in state.candidates:
        if remaining.candidate_id not in decided:
            state = service.decide_fact_atom(
                state,
                candidate_identity=remaining.candidate_id,
                disposition=CandidateOwnerDispositionV1.REJECT,
                atom=None,
                adjudicator_identity="owner",
                adjudicated_at=now,
                decision_rationale="Owner rejected the residual candidate.",
            )
    state = service.finalize_fact_atoms(state)
    state = service.adjudicate_mechanic_claim(
        state,
        mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
        atom_roles=(
            AtomRoleBindingV1(
                role="complete_quantity", atom_ids=("complete-quantity",)
            ),
            AtomRoleBindingV1(role="quantity_object", atom_ids=("event-proposition",)),
        ),
        satisfied_boundary_codes=(
            "no_value_judgment",
            "preserve_approximation_attribution_period_denominator_scope",
        ),
        adjudicator_identity="owner",
        adjudicated_at=now,
    )
    finalized = service.finalize_claims(state)
    revised_claim_state = composition.desktop_adjudication.dispatch(
        VoiceDesktopAdjudicationActionV1(
            event_id=1,
            action="confirm_mechanic_claim",
            mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
            atom_roles=(
                AtomRoleBindingV1(
                    role="complete_quantity", atom_ids=("complete-quantity",)
                ),
                AtomRoleBindingV1(
                    role="quantity_object", atom_ids=("event-proposition",)
                ),
            ),
            satisfied_boundary_codes=(
                "no_value_judgment",
                "preserve_approximation_attribution_period_denominator_scope",
            ),
            owner_identity="desktop-owner",
            occurred_at=now,
            supersession_reason="Owner reconfirmed the exact role bindings.",
        )
    )
    assert (
        revised_claim_state.mechanic_claim_receipts[-1].prior_receipt_identity
        is not None
    )
    finalized = composition.desktop_adjudication.dispatch(
        VoiceDesktopAdjudicationActionV1(
            event_id=1,
            action="finalize_claims",
            owner_identity="desktop-owner",
            occurred_at=now,
        )
    )
    result = bootstrap.reevaluate(1)
    assert result.status is OrdinaryVoiceBootstrapStatusV2.ELIGIBILITY_AVAILABLE
    persisted = canonical.load_story(1)
    assert persisted.adjudication_state_identity == finalized.state_identity
    assert persisted.program_eligibility.shortlist
    assert persisted.expression_eligibility is None
    composition.context_registry._bootstrap = bootstrap
    composition.desktop_workflow.daily_use_automation = False
    refreshed = composition.desktop_workflow.dispatch(
        VoiceDesktopActionInputV2(action="refresh", event_id=1)
    )
    assert refreshed.program_choices
    selected = composition.desktop_workflow.dispatch(
        VoiceDesktopActionInputV2(
            action="select_program",
            event_id=1,
            candidate_identity=refreshed.program_choices[0][0],
        )
    )
    assert selected.expression_choices == (("NONE", "Fără expresie"),)
    expression_none = composition.desktop_workflow.dispatch(
        VoiceDesktopActionInputV2(
            action="select_expression", event_id=1, candidate_identity=None
        )
    )
    assert expression_none.preview_enabled
    preview = composition.desktop_workflow.dispatch(
        VoiceDesktopActionInputV2(action="preview", event_id=1)
    )
    assert preview.preview_text
    assert canonical.load_story(1).execution_request is not None


def test_production_import_path_loads_no_proof_modules():
    code = """
import sys
from pastila_scout.voice_executor_v2 import DeterministicVoiceExecutorV2
from pastila_scout.voice_deterministic_v2.production import PRODUCTION_PROGRAMS_V1
from pastila_scout.voice_deterministic_v2.production_renderer import render_production_deterministic_voice_v2
assert DeterministicVoiceExecutorV2
assert len(PRODUCTION_PROGRAMS_V1) == 12
assert render_production_deterministic_voice_v2
for name in (
    'pastila_scout.voice_deterministic_v2.library',
    'pastila_scout.voice_deterministic_v2.proof',
    'pastila_scout.voice_deterministic_v2.renderer',
):
    assert name not in sys.modules, name
"""
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from pastila_scout.desktop_v1.voice_v2_composition import compose_voice_v2_production
from pastila_scout.desktop_v1.voice_v2_interaction import VoiceDesktopActionInputV2
from pastila_scout.desktop_v1.voice_v2_workflow import VoiceDesktopWorkflowCoordinatorV2
from pastila_scout.editor.generation.semantic_draft_v2 import (
    AuthorityDensityV2,
    FactualNucleusBindingV2,
    FactualSummaryV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
    SemanticStoryV2,
)
from pastila_scout.editor_voice_deterministic_v2 import (
    EditorDeterministicVoiceApplicationServiceV2,
)
from pastila_scout.expression_catalog_v2.eligibility import (
    _sealed as expression_sealed,
)
from pastila_scout.expression_catalog_v2.eligibility_models import (
    ExpressionEligibilityResultV1,
)
from pastila_scout.voice_canonical_state_v2 import (
    CanonicalVoiceLifecycleV2,
    CanonicalVoicePersistenceError,
    CanonicalVoiceStoryStateV2,
    CanonicalVoiceWorkspaceStateV2,
    CanonicalVoiceWorkspaceStoreV2,
    UnknownCanonicalVoiceVersionError,
    resolve_voice_workspace_root,
)
from pastila_scout.voice_eligibility_v2 import (
    ZERO_IDENTITY,
    evaluate_voice_eligibility_v1,
    finalize_claim_identity,
)
from pastila_scout.voice_executor_v2 import (
    ZERO_ACTIVATION_POLICY_V1,
    DeterministicVoiceExecutorV2,
)
from pastila_scout.voice_fact_atoms_v2 import finalize_bundle_identity
from pastila_scout.voice_governed_realization_v1 import GovernedNumericRealizerV1
from pastila_scout.voice_persisted_context_v2 import (
    PersistedStoryGovernedContextLoaderV2,
)
from pastila_scout.voice_repetition_v2 import (
    finalize_order_authority_v1,
    remove_unpublished_commentary_v1,
)
from pastila_scout.voice_repetition_v2.models import (
    EpisodeOrderAuthorityV1,
    PublicationStateV1,
)
from pastila_scout.voice_workflow_v2 import (
    semantic_draft_revision_identity,
    sha256_identity,
)
from tests.test_voice_production_materialization_v2 import _context


def _state():
    summary = FactualSummaryV2(
        text="Faptul principal este confirmat.",
        authority_bundle_identity="sha256:" + "1" * 64,
        authority_density=AuthorityDensityV2.STANDARD,
        nucleus_bindings=(
            FactualNucleusBindingV2(
                nucleus_id="n1", sentence_number=1, authority_fact_ids=("f1",)
            ),
        ),
        model_identifier="core-v1.2",
        provider="test",
        validation_receipt="receipt",
    )
    draft = PastilaEditorSemanticDraftV2.assemble(
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
    revision = semantic_draft_revision_identity(draft)
    binding, bundle, _, _, snapshot, _roles, claim = _context(
        "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1"
    )
    binding = binding.model_copy(
        update={
            "semantic_draft_revision_identity": revision,
            "factual_summary_sha256": sha256_identity(summary.text),
        }
    )
    bundle = finalize_bundle_identity(
        bundle.model_copy(
            update={
                "semantic_draft_revision_identity": revision,
                "factual_summary_identity": binding.factual_summary_sha256,
                "bundle_identity": ZERO_IDENTITY,
            }
        )
    )
    claim = finalize_claim_identity(
        claim.model_copy(
            update={
                "fact_atom_bundle_identity": bundle.bundle_identity,
                "claim_identity": ZERO_IDENTITY,
            }
        )
    )
    eligibility = evaluate_voice_eligibility_v1(
        bundle=bundle,
        claims=(claim,),
        repetition_snapshot=snapshot,
        requested_program_ids=("NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1",),
    )
    expression = ExpressionEligibilityResultV1(
        fact_atom_bundle_identity=bundle.bundle_identity,
        program_eligibility_result_identity=eligibility.result_identity,
        repetition_snapshot_identity=snapshot.snapshot_identity,
        outcomes=(),
        shortlist=(),
    )
    expression = expression.model_copy(
        update={"result_identity": expression_sealed(expression, "result_identity")}
    )
    order = finalize_order_authority_v1(
        EpisodeOrderAuthorityV1(
            episode_id="episode-1",
            episode_ordinal=1,
            ordered_event_ids=(1,),
            publication_state=PublicationStateV1.UNPUBLISHED,
        )
    )
    return CanonicalVoiceStoryStateV2(
        lifecycle=CanonicalVoiceLifecycleV2.ELIGIBILITY_AVAILABLE,
        binding=binding,
        authored_draft=draft,
        fact_atom_bundle=bundle,
        mechanic_claims=(claim,),
        repetition_snapshot=snapshot,
        program_eligibility=eligibility,
        expression_eligibility=expression,
        order_authority=order,
    )


def _store(tmp_path):
    project = (tmp_path / "active-project.json").resolve()
    return CanonicalVoiceWorkspaceStoreV2(
        project_path=project, project_identity="project-1"
    )


def test_canonical_root_no_state_and_explicit_pointer_round_trip(tmp_path):
    store = _store(tmp_path)
    assert store.root == resolve_voice_workspace_root(
        (tmp_path / "active-project.json").resolve()
    )
    assert store.load_story(1) is None
    saved = store.save_story(_state())
    workspace = store.save_workspace(
        CanonicalVoiceWorkspaceStateV2(
            project_identity="project-1",
            order_authority=saved.order_authority,
            story_pointer_identities=(),
        )
    )
    saved = store.save_story(saved)
    assert store.load_story(1) == saved
    assert store.load_workspace().order_authority == workspace.order_authority

    composition = compose_voice_v2_production(
        project_path=store.project_path, project_identity="project-1"
    )
    assert composition.canonical_store is not None
    assert composition.persisted_context_loader is not None
    assert composition.context_registry.load(1).event_id == 1

    unrelated = store.root / "stories" / "1" / "revisions" / "latest.json"
    unrelated.write_text("{}", encoding="utf-8")
    assert store.load_story(1) == saved


def test_unknown_corrupt_and_orphan_pointers_fail_closed(tmp_path):
    store = _store(tmp_path)
    store.save_story(_state())
    pointer = store.root / "stories" / "1" / "current.json"
    payload = json.loads(pointer.read_text(encoding="utf-8"))
    payload["schema_version"] = "999"
    pointer.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(UnknownCanonicalVoiceVersionError):
        store.load_story(1)

    store = _store(tmp_path / "orphan")
    store.save_story(_state())
    pointer = store.root / "stories" / "1" / "current.json"
    payload = json.loads(pointer.read_text(encoding="utf-8"))
    payload["state_relative_path"] = "revisions/missing.json"
    pointer.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(CanonicalVoicePersistenceError):
        store.load_story(1)


def test_restart_loader_persists_selection_preview_and_atomic_acceptance(tmp_path):
    store = _store(tmp_path)
    state = store.save_story(_state())
    store.save_workspace(
        CanonicalVoiceWorkspaceStateV2(
            project_identity="project-1",
            order_authority=state.order_authority,
        )
    )
    store.save_story(state)
    loader = PersistedStoryGovernedContextLoaderV2(store)
    executor = DeterministicVoiceExecutorV2(activation_policy=ZERO_ACTIVATION_POLICY_V1)
    coordinator = VoiceDesktopWorkflowCoordinatorV2(
        application=EditorDeterministicVoiceApplicationServiceV2(
            executor=executor, activation_policy=ZERO_ACTIVATION_POLICY_V1
        ),
        load_context=loader.load,
        owner_identity="desktop-owner",
    )
    coordinator.dispatch(VoiceDesktopActionInputV2("refresh", 1))
    candidate = state.program_eligibility.shortlist[0].candidate_id
    coordinator.dispatch(VoiceDesktopActionInputV2("select_program", 1, candidate))
    assert store.load_story(1).lifecycle is CanonicalVoiceLifecycleV2.PROGRAM_SELECTED
    coordinator.dispatch(VoiceDesktopActionInputV2("select_expression", 1, None))
    assert (
        store.load_story(1).lifecycle
        is CanonicalVoiceLifecycleV2.EXPRESSION_SELECTED_OR_NONE
    )
    preview = coordinator.dispatch(VoiceDesktopActionInputV2("preview", 1))
    assert preview.accept_enabled
    persisted_preview = store.load_story(1)
    assert persisted_preview.lifecycle is CanonicalVoiceLifecycleV2.PREVIEW_AVAILABLE
    assert PersistedStoryGovernedContextLoaderV2(store).load(1) is not None
    coordinator.dispatch(VoiceDesktopActionInputV2("accept", 1))
    accepted = store.load_story(1)
    assert accepted.lifecycle is CanonicalVoiceLifecycleV2.ACCEPTED_COMMENTARY
    assert accepted.authored_draft.stories[0].acid_commentary is not None
    assert store.acceptance_store.current_draft() == accepted.authored_draft
    assert executor.inspect_capability().model_calls == 0

    committed = store.acceptance_store.current_ledger().events[-1].commit
    assert committed is not None
    removal = remove_unpublished_commentary_v1(
        store.acceptance_store,
        commit_identity=committed.commit_identity,
        owner_identity="desktop-owner",
        reason="owner removed",
        removed_at=datetime(2026, 8, 23, tzinfo=UTC),
    )
    removed = store.promote_removal(accepted, removal)
    assert removed.lifecycle is CanonicalVoiceLifecycleV2.OWNER_REMOVED_COMMENTARY
    assert removed.authored_draft.stories[0].acid_commentary is None
    assert (
        CanonicalVoiceWorkspaceStoreV2(
            project_path=store.project_path, project_identity="project-1"
        ).load_story(1)
        == removed
    )


def test_governed_model_preview_receipt_survives_atomic_acceptance(tmp_path):
    store = _store(tmp_path)
    state = store.save_story(_state())
    store.save_workspace(
        CanonicalVoiceWorkspaceStateV2(
            project_identity="project-1", order_authority=state.order_authority
        )
    )
    loader = PersistedStoryGovernedContextLoaderV2(store)
    executor = DeterministicVoiceExecutorV2(activation_policy=ZERO_ACTIVATION_POLICY_V1)
    realizer = GovernedNumericRealizerV1(
        lambda _prompt: (
            json.dumps(
                {
                    "decision": "commentary",
                    "commentary": (
                        "În imaginația mea, ștampila își comandă deja un podium. "
                        "Mai lipsește doar covorul roșu!"
                    ),
                },
                ensure_ascii=False,
            ),
            "pastila-editor-core-v1.2-experimental",
        )
    )
    coordinator = VoiceDesktopWorkflowCoordinatorV2(
        application=EditorDeterministicVoiceApplicationServiceV2(
            executor=executor, activation_policy=ZERO_ACTIVATION_POLICY_V1
        ),
        load_context=loader.load,
        owner_identity="desktop-owner",
        governed_realizer=realizer,
        governed_realizer_required=True,
    )

    coordinator.dispatch(VoiceDesktopActionInputV2("refresh", 1))
    candidate = state.program_eligibility.shortlist[0].candidate_id
    coordinator.dispatch(VoiceDesktopActionInputV2("select_program", 1, candidate))
    coordinator.dispatch(VoiceDesktopActionInputV2("select_expression", 1, None))
    preview = coordinator.dispatch(VoiceDesktopActionInputV2("preview", 1))

    assert preview.accept_enabled
    terminal = store.load_story(1).preview.terminal_result
    assert terminal.backend_kind.value == "governed_model_realizer"
    assert terminal.realization_receipt is not None
    assert terminal.model_calls == terminal.provider_calls == terminal.model_loads == 1

    coordinator.dispatch(VoiceDesktopActionInputV2("accept", 1))
    commentary = store.load_story(1).authored_draft.stories[0].acid_commentary
    assert commentary.text == preview.preview_text
    assert commentary.execution_provenance.backend_kind == "model"
    assert commentary.execution_provenance.model_calls == 1


@pytest.mark.parametrize(
    ("lifecycle", "changes"),
    (
        (
            CanonicalVoiceLifecycleV2.STALE_REEVALUATION_REQUIRED,
            {"stale_reason": "authority_revision_changed"},
        ),
        (
            CanonicalVoiceLifecycleV2.INTEGRITY_FAILURE,
            {"integrity_failure_code": "orphan_pointer"},
        ),
    ),
)
def test_terminal_nonaccepted_lifecycle_states_round_trip(tmp_path, lifecycle, changes):
    store = _store(tmp_path)
    state = _state().model_copy(update={"lifecycle": lifecycle, **changes})
    saved = store.save_story(state)
    assert store.load_story(1) == saved

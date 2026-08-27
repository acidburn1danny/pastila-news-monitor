"""Production composition for the installed deterministic Voice V2 backend."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from pastila_scout.editor_voice_deterministic_v2 import (
    EditorDeterministicVoiceApplicationServiceV2,
)
from pastila_scout.experimental_core_v1_2 import (
    MODEL_ID as CORE_V1_2_MODEL_ID,
)
from pastila_scout.experimental_core_v1_2 import (
    ExperimentalCoreV12Executor,
)
from pastila_scout.voice_adjudication_v2 import (
    VoiceAdjudicationApplicationServiceV1,
    VoiceAdjudicationStoreV1,
)
from pastila_scout.voice_canonical_state_v2 import CanonicalVoiceWorkspaceStoreV2
from pastila_scout.voice_executor_v2 import (
    BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1,
    DeterministicVoiceExecutorV2,
)
from pastila_scout.voice_governed_realization_v1 import (
    GovernedNumericRealizerV1,
    build_core_v1_2_generator,
)
from pastila_scout.voice_ordinary_bootstrap_v2 import (
    OrdinaryPersistedStoryVoiceBootstrapV2,
)
from pastila_scout.voice_persisted_context_v2 import (
    PersistedStoryGovernedContextLoaderV2,
)
from pastila_scout.voice_revision_promotion_v2 import AcceptedVoiceRevisionPromoterV2

from .voice_adjudication_workflow import VoiceDesktopAdjudicationCoordinatorV1
from .voice_v2_workflow import (
    VoiceDesktopContextRegistryV2,
    VoiceDesktopWorkflowCoordinatorV2,
)


@dataclass(frozen=True, slots=True)
class VoiceV2ProductionComposition:
    executor: DeterministicVoiceExecutorV2
    application: EditorDeterministicVoiceApplicationServiceV2
    context_registry: VoiceDesktopContextRegistryV2
    desktop_workflow: VoiceDesktopWorkflowCoordinatorV2
    canonical_store: CanonicalVoiceWorkspaceStoreV2 | None = None
    persisted_context_loader: PersistedStoryGovernedContextLoaderV2 | None = None
    adjudication_store: VoiceAdjudicationStoreV1 | None = None
    adjudication_application: VoiceAdjudicationApplicationServiceV1 | None = None
    ordinary_story_bootstrap: OrdinaryPersistedStoryVoiceBootstrapV2 | None = None
    desktop_adjudication: VoiceDesktopAdjudicationCoordinatorV1 | None = None


def compose_voice_v2_production(
    *,
    project_path: Path | None = None,
    project_identity: str | None = None,
    project_store=None,
    settings=None,
) -> VoiceV2ProductionComposition:
    if (project_path is None) != (project_identity is None):
        raise ValueError("project path and identity must be supplied together")
    activation_policy = BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1
    executor = DeterministicVoiceExecutorV2(activation_policy=activation_policy)
    application = EditorDeterministicVoiceApplicationServiceV2(
        executor=executor,
        activation_policy=activation_policy,
    )
    canonical_store = (
        CanonicalVoiceWorkspaceStoreV2(
            project_path=project_path, project_identity=project_identity
        )
        if project_path is not None and project_identity is not None
        else None
    )
    revision_promoter = (
        AcceptedVoiceRevisionPromoterV2(
            project_store=project_store, root=canonical_store.root
        )
        if project_store is not None and canonical_store is not None
        else None
    )
    persisted_context_loader = (
        PersistedStoryGovernedContextLoaderV2(
            canonical_store, revision_promoter, activation_policy=activation_policy
        )
        if canonical_store is not None
        else None
    )
    adjudication_store = (
        VoiceAdjudicationStoreV1(canonical_store.root)
        if canonical_store is not None
        else None
    )
    adjudication_application = (
        VoiceAdjudicationApplicationServiceV1(adjudication_store)
        if adjudication_store is not None
        else None
    )
    ordinary_story_bootstrap = (
        OrdinaryPersistedStoryVoiceBootstrapV2(
            project_store=project_store,
            canonical_store=canonical_store,
            adjudication=adjudication_application,
            activation_policy=activation_policy,
            daily_use_automation=True,
        )
        if project_store is not None
        and canonical_store is not None
        and adjudication_application is not None
        else None
    )
    context_registry = VoiceDesktopContextRegistryV2(
        persisted_context_loader, ordinary_story_bootstrap
    )
    governed_realizer = None
    if (
        settings is not None
        and getattr(settings, "editor_default_model", None) == CORE_V1_2_MODEL_ID
    ):
        project_root = Path(
            getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3])
        )
        local_executor = ExperimentalCoreV12Executor(
            project_root=project_root, max_output_tokens=500
        )
        governed_realizer = GovernedNumericRealizerV1(
            build_core_v1_2_generator(
                executor=local_executor,
                timeout_seconds=float(settings.editor_timeout_seconds),
            )
        )
    desktop_adjudication = (
        VoiceDesktopAdjudicationCoordinatorV1(adjudication_application)
        if adjudication_application is not None
        else None
    )
    return VoiceV2ProductionComposition(
        executor=executor,
        application=application,
        context_registry=context_registry,
        canonical_store=canonical_store,
        persisted_context_loader=persisted_context_loader,
        adjudication_store=adjudication_store,
        adjudication_application=adjudication_application,
        ordinary_story_bootstrap=ordinary_story_bootstrap,
        desktop_adjudication=desktop_adjudication,
        desktop_workflow=VoiceDesktopWorkflowCoordinatorV2(
            application=application,
            load_context=context_registry.load,
            owner_identity="desktop-owner",
            load_bootstrap_result=context_registry.bootstrap_result,
            adjudication_coordinator=desktop_adjudication,
            daily_use_automation=True,
            governed_realizer=governed_realizer,
            governed_realizer_required=settings is not None,
        ),
    )


__all__ = ["VoiceV2ProductionComposition", "compose_voice_v2_production"]

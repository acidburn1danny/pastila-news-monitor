"""Synthetic, zero-provider fixtures shared by Voice V2 integration tests."""

import hashlib

from pastila_scout.editor.generation.semantic_draft_v2 import (
    AuthorityDensityV2,
    FactualNucleusBindingV2,
    FactualSummaryV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
    SemanticStoryV2,
)
from pastila_scout.expression_catalog_v2.eligibility import _sealed
from pastila_scout.expression_catalog_v2.eligibility_models import (
    ExpressionEligibilityResultV1,
)
from pastila_scout.voice_adjudication_v2 import (
    AuthorityTextV1,
    VoiceAdjudicationApplicationServiceV1,
    VoiceAdjudicationStoreV1,
)
from pastila_scout.voice_canonical_state_v2 import (
    CanonicalVoiceLifecycleV2,
    CanonicalVoiceStoryStateV2,
    CanonicalVoiceWorkspaceStoreV2,
)
from pastila_scout.voice_eligibility_v2 import (
    ZERO_IDENTITY,
    evaluate_voice_eligibility_v1,
    finalize_claim_identity,
)
from pastila_scout.voice_fact_atoms_v2 import finalize_bundle_identity
from pastila_scout.voice_fact_atoms_v2.models import AuthorityClass
from pastila_scout.voice_repetition_v2 import finalize_order_authority_v1
from pastila_scout.voice_repetition_v2.models import (
    EpisodeOrderAuthorityV1,
    PublicationStateV1,
)
from pastila_scout.voice_workflow_v2 import (
    semantic_draft_revision_identity,
    sha256_identity,
)
from tests.test_voice_production_materialization_v2 import _context


def synthetic_canonical_state_v2():
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
        update={"result_identity": _sealed(expression, "result_identity")}
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


def synthetic_canonical_store_v2(tmp_path):
    return CanonicalVoiceWorkspaceStoreV2(
        project_path=(tmp_path / "active-project.json").resolve(),
        project_identity="project-1",
    )


def started_adjudication_v2(tmp_path):
    binding, _, _, _, snapshot, _, _ = _context(
        "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1"
    )
    text = "Proiectul costă aproximativ 37.000 de euro. Cauza nu este cunoscută."
    authority = AuthorityTextV1(
        authority_class=AuthorityClass.EVENT,
        authority_identity=binding.event_authority_identity,
        source_identity="event-authority:1",
        text=text,
        text_sha256="sha256:" + hashlib.sha256(text.encode()).hexdigest(),
    )
    store = VoiceAdjudicationStoreV1(tmp_path / "voice-root")
    service = VoiceAdjudicationApplicationServiceV1(store)
    state = service.begin(
        binding=binding,
        story_position=1,
        authority_texts=(authority,),
        repetition_snapshot=snapshot,
    )
    return service, store, state, text

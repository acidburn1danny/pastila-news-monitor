from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pastila_scout.editor.generation.semantic_draft_v2 import (
    AcidCommentaryV2,
    AuthorityDensityV2,
    FactualNucleusBindingV2,
    FactualSummaryV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
    SemanticStoryV2,
)
from pastila_scout.editor_voice_application_v2 import (
    EditorVoiceApplicationOutcomeV1,
    EditorVoiceApplicationServiceV1,
    EditorVoiceStoryRequestV1,
    UnavailableVoiceExecutorV1,
    VoiceExecutorAvailabilityV1,
    VoiceExecutorCapabilityV1,
)
from pastila_scout.voice_workflow_v2 import (
    AcceptedCommentaryBindingV1,
    PersistedVoiceAttemptOutcomeV1,
    PublicCommentaryStateV1,
    VoiceAttemptRecordV1,
    VoiceStoryBindingV1,
    VoiceValidationResultV1,
    VoiceWorkflowSidecarStoreV1,
    VoiceWorkflowSidecarV1,
    semantic_draft_revision_identity,
    sha256_identity,
)

NOW = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)


def _sha(label: str) -> str:
    return f"sha256:{hashlib.sha256(label.encode()).hexdigest()}"


def _draft(
    commentary: AcidCommentaryV2 | None = None,
) -> PastilaEditorSemanticDraftV2:
    summary = FactualSummaryV2(
        text="Instituția a publicat rezultatul verificării.",
        authority_bundle_identity="event-authority:77:v1",
        authority_density=AuthorityDensityV2.THIN,
        nucleus_bindings=(
            FactualNucleusBindingV2(
                nucleus_id="fact-result",
                sentence_number=1,
                authority_fact_ids=("authority-fact-1",),
            ),
        ),
        model_identifier="pastila-editor-core-v1.2-experimental",
        provider="ollama",
        validation_receipt="core-validation:pass",
    )
    story = SemanticStoryV2(
        event_id=77,
        position=1,
        factual_summary=summary,
        acid_commentary=commentary,
        acid_commentary_status=(
            "present" if commentary else "absent_voice_layer_unavailable"
        ),
    )
    return PastilaEditorSemanticDraftV2.assemble(
        episode_id="episode-77",
        mode=(
            SemanticDraftModeV2.CORE_PLUS_VOICE
            if commentary
            else SemanticDraftModeV2.CORE_ONLY
        ),
        stories=(story,),
    )


def _request(draft: PastilaEditorSemanticDraftV2) -> EditorVoiceStoryRequestV1:
    return EditorVoiceStoryRequestV1(
        draft=draft,
        story_material_reference="editor-material-v2:event:77:revision:1",
        event_id=77,
        expected_semantic_draft_revision_identity=(
            semantic_draft_revision_identity(draft)
        ),
        expected_event_authority_identity="event-authority:77:v1",
        runtime_input_identity=_sha("runtime-input-77"),
    )


class _CountingUnavailableExecutor(UnavailableVoiceExecutorV1):
    def __init__(self) -> None:
        self.capability_calls = 0
        self.execution_calls = 0

    def inspect_capability(self):
        self.capability_calls += 1
        return super().inspect_capability()

    def execute(self, request):
        self.execution_calls += 1
        return super().execute(request)


class _AvailableInspectionOnlyExecutor:
    def __init__(self) -> None:
        self.execution_calls = 0

    def inspect_capability(self):
        return VoiceExecutorCapabilityV1(
            executor_identity="future-voice-executor:v1",
            availability=VoiceExecutorAvailabilityV1.AVAILABLE,
            voice_model_package_identity="future-voice-package:v1",
        )

    def execute(self, request):
        del request
        self.execution_calls += 1
        raise AssertionError("inspection must not execute Voice")


def test_unavailable_executor_has_zero_runtime_effects() -> None:
    result = UnavailableVoiceExecutorV1().execute(
        request=type("RequestSentinel", (), {})()
    )

    assert result.outcome is VoiceExecutorAvailabilityV1.UNAVAILABLE
    assert result.provider_calls == result.model_loads == 0
    assert result.generations == result.attempts_created == 0


def test_generation_request_persists_unavailable_without_attempt(
    tmp_path: Path,
) -> None:
    draft = _draft()
    request = _request(draft)
    executor = _CountingUnavailableExecutor()
    service = EditorVoiceApplicationServiceV1(executor=executor, clock=lambda: NOW)
    store = VoiceWorkflowSidecarStoreV1(tmp_path / "voice-workflow.json")
    draft_before = draft.model_dump_json()

    result = service.request_generation(request, store=store)
    persisted = store.load(draft=draft)

    assert result.outcome is EditorVoiceApplicationOutcomeV1.UNAVAILABLE
    assert result.commentary_state is PublicCommentaryStateV1.UNAVAILABLE
    assert result.executor_port_invoked
    assert not result.attempt_created
    assert persisted.attempts == ()
    assert persisted.commentary_state is PublicCommentaryStateV1.UNAVAILABLE
    assert result.sidecar_identity == sha256_identity(store.path.read_bytes())
    assert executor.capability_calls == executor.execution_calls == 1
    assert draft.model_dump_json() == draft_before


def test_unavailable_request_preserves_failed_attempt_history(tmp_path: Path) -> None:
    draft = _draft()
    request = _request(draft)
    binding = VoiceStoryBindingV1(
        story_material_reference=request.story_material_reference,
        semantic_draft_revision_identity=(
            request.expected_semantic_draft_revision_identity
        ),
        event_id=77,
        factual_summary_sha256=sha256_identity(draft.stories[0].factual_summary.text),
        event_authority_identity=request.expected_event_authority_identity,
        runtime_input_identity=request.runtime_input_identity,
    )
    attempt = VoiceAttemptRecordV1(
        attempt_identity=_sha("failed-attempt"),
        ordinal=1,
        outcome=PersistedVoiceAttemptOutcomeV1.FAILED,
        runtime_input_identity=request.runtime_input_identity,
        validation_result=VoiceValidationResultV1.NOT_REACHED,
        failure_identity="prior-runtime-failure",
        started_at=NOW - timedelta(minutes=2),
        completed_at=NOW - timedelta(minutes=1),
    )
    prior = VoiceWorkflowSidecarV1(
        binding=binding,
        commentary_state=PublicCommentaryStateV1.FAILED,
        attempts=(attempt,),
        created_at=NOW - timedelta(minutes=2),
        updated_at=NOW - timedelta(minutes=1),
    )
    store = VoiceWorkflowSidecarStoreV1(tmp_path / "voice-workflow.json")
    store.save(prior, draft=draft)

    result = EditorVoiceApplicationServiceV1(
        executor=UnavailableVoiceExecutorV1(), clock=lambda: NOW
    ).request_generation(request, store=store)
    persisted = store.load(draft=draft)

    assert result.outcome is EditorVoiceApplicationOutcomeV1.UNAVAILABLE
    assert persisted.attempts == (attempt,)
    assert persisted.commentary_state is PublicCommentaryStateV1.UNAVAILABLE


def test_inspection_derives_ungenerated_and_failed_when_executor_available(
    tmp_path: Path,
) -> None:
    draft = _draft()
    request = _request(draft)
    executor = _AvailableInspectionOnlyExecutor()
    service = EditorVoiceApplicationServiceV1(executor=executor, clock=lambda: NOW)
    store = VoiceWorkflowSidecarStoreV1(tmp_path / "voice-workflow.json")

    ungenerated = service.inspect(request, store=store)
    assert ungenerated.outcome is EditorVoiceApplicationOutcomeV1.UNGENERATED
    assert ungenerated.generation_possible

    binding = service.prepare_binding(request)
    failed_attempt = VoiceAttemptRecordV1(
        attempt_identity=_sha("attempt-1"),
        ordinal=1,
        outcome=PersistedVoiceAttemptOutcomeV1.FAILED,
        runtime_input_identity=request.runtime_input_identity,
        voice_model_package_identity="future-voice-package:v1",
        validation_result=VoiceValidationResultV1.FAILED,
        output_sha256=_sha("rejected-output"),
        failure_identity="factual-boundary-failed",
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
    )
    failed_sidecar = VoiceWorkflowSidecarV1(
        binding=binding,
        commentary_state=PublicCommentaryStateV1.FAILED,
        attempts=(failed_attempt,),
        created_at=NOW,
        updated_at=NOW + timedelta(seconds=1),
    )
    store.save(failed_sidecar, draft=draft)

    failed = service.inspect(request, store=store)
    assert failed.outcome is EditorVoiceApplicationOutcomeV1.FAILED
    assert failed.generation_possible
    assert executor.execution_calls == 0


def test_binding_mismatch_fails_before_executor_or_sidecar_mutation(
    tmp_path: Path,
) -> None:
    draft = _draft()
    request = _request(draft).model_copy(
        update={"expected_event_authority_identity": "wrong-authority"}
    )
    executor = _CountingUnavailableExecutor()
    service = EditorVoiceApplicationServiceV1(executor=executor, clock=lambda: NOW)
    store = VoiceWorkflowSidecarStoreV1(tmp_path / "voice-workflow.json")

    result = service.request_generation(request, store=store)

    assert result.outcome is EditorVoiceApplicationOutcomeV1.INVALID_BINDING
    assert result.safe_failure_code == "voice_story_binding_invalid"
    assert executor.capability_calls == executor.execution_calls == 0
    assert not store.path.exists()


def test_generated_state_wins_over_current_executor_unavailability(
    tmp_path: Path,
) -> None:
    commentary = AcidCommentaryV2(
        text="Verificarea e gata. Suspansul poate lua pauză.",
        voice_model_identity="voice-package:accepted",
        factual_boundary_receipt="voice-boundary:pass",
    )
    draft = _draft(commentary)
    request = _request(draft)
    binding = VoiceStoryBindingV1(
        story_material_reference=request.story_material_reference,
        semantic_draft_revision_identity=(
            request.expected_semantic_draft_revision_identity
        ),
        event_id=77,
        factual_summary_sha256=sha256_identity(draft.stories[0].factual_summary.text),
        event_authority_identity=request.expected_event_authority_identity,
        runtime_input_identity=request.runtime_input_identity,
    )
    attempt = VoiceAttemptRecordV1(
        attempt_identity=_sha("accepted-attempt"),
        ordinal=1,
        outcome=PersistedVoiceAttemptOutcomeV1.GENERATED,
        runtime_input_identity=request.runtime_input_identity,
        voice_model_package_identity="voice-package:accepted",
        validation_result=VoiceValidationResultV1.PASSED,
        output_sha256=sha256_identity(commentary.text),
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
    )
    accepted = AcceptedCommentaryBindingV1(
        attempt_identity=attempt.attempt_identity,
        attempt_ordinal=1,
        acid_commentary_identity=_sha("accepted-commentary"),
        output_sha256=sha256_identity(commentary.text),
        voice_model_package_identity="voice-package:accepted",
        factual_boundary_validation_receipt="voice-boundary:pass",
        accepted_at=NOW + timedelta(seconds=1),
    )
    sidecar = VoiceWorkflowSidecarV1(
        binding=binding,
        commentary_state=PublicCommentaryStateV1.GENERATED,
        attempts=(attempt,),
        accepted_commentary=accepted,
        created_at=NOW,
        updated_at=NOW + timedelta(seconds=1),
    )
    store = VoiceWorkflowSidecarStoreV1(tmp_path / "voice-workflow.json")
    store.save(sidecar, draft=draft)

    result = EditorVoiceApplicationServiceV1(
        executor=UnavailableVoiceExecutorV1(), clock=lambda: NOW
    ).inspect(request, store=store)

    assert result.outcome is EditorVoiceApplicationOutcomeV1.GENERATED
    assert result.commentary_state is PublicCommentaryStateV1.GENERATED
    assert not result.generation_possible
    assert result.sidecar_identity == sha256_identity(store.path.read_bytes())

"""Editor orchestration for Voice availability and immutable story binding."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from pastila_scout.editor_voice_application_v2.executor import VoiceExecutorPortV1
from pastila_scout.editor_voice_application_v2.models import (
    EditorVoiceApplicationOutcomeV1,
    EditorVoiceApplicationResultV1,
    EditorVoiceStoryRequestV1,
    VoiceExecutorAvailabilityV1,
    VoiceExecutorRequestV1,
)
from pastila_scout.voice_workflow_v2 import (
    PublicCommentaryStateV1,
    VoiceStoryBindingV1,
    VoiceWorkflowSidecarIntegrityError,
    VoiceWorkflowSidecarStoreV1,
    VoiceWorkflowSidecarV1,
    semantic_draft_revision_identity,
    sha256_identity,
    voice_sidecar_identity,
)


def _invalid(code: str) -> EditorVoiceApplicationResultV1:
    return EditorVoiceApplicationResultV1(
        outcome=EditorVoiceApplicationOutcomeV1.INVALID_BINDING,
        commentary_state=None,
        generation_possible=False,
        safe_failure_code=code,
    )


class EditorVoiceApplicationServiceV1:
    """Orchestrates Voice without owning semantics, models, or authored prose."""

    def __init__(
        self,
        *,
        executor: VoiceExecutorPortV1,
        clock: Callable[[], datetime],
    ) -> None:
        self._executor = executor
        self._clock = clock

    def prepare_binding(
        self, request: EditorVoiceStoryRequestV1
    ) -> VoiceStoryBindingV1:
        actual_revision = semantic_draft_revision_identity(request.draft)
        if actual_revision != request.expected_semantic_draft_revision_identity:
            raise VoiceWorkflowSidecarIntegrityError(
                "semantic draft revision authority mismatch"
            )
        stories = tuple(
            story
            for story in request.draft.stories
            if story.event_id == request.event_id
        )
        if len(stories) != 1:
            raise VoiceWorkflowSidecarIntegrityError("requested V2 story is missing")
        summary = stories[0].factual_summary
        if (
            summary.authority_bundle_identity
            != request.expected_event_authority_identity
        ):
            raise VoiceWorkflowSidecarIntegrityError(
                "event authority identity mismatch"
            )
        return VoiceStoryBindingV1(
            story_material_reference=request.story_material_reference,
            semantic_draft_revision_identity=actual_revision,
            event_id=request.event_id,
            factual_summary_sha256=sha256_identity(summary.text),
            event_authority_identity=summary.authority_bundle_identity,
            commentary_background_authority_identity=(
                request.commentary_background_authority_identity
            ),
            runtime_input_identity=request.runtime_input_identity,
        )

    def inspect(
        self,
        request: EditorVoiceStoryRequestV1,
        *,
        store: VoiceWorkflowSidecarStoreV1 | None,
    ) -> EditorVoiceApplicationResultV1:
        prepared = self._prepare_and_load(request, store=store)
        if isinstance(prepared, EditorVoiceApplicationResultV1):
            return prepared
        binding, sidecar = prepared
        capability = self._executor.inspect_capability()
        if sidecar is not None and (
            sidecar.commentary_state is PublicCommentaryStateV1.GENERATED
        ):
            return self._result(
                EditorVoiceApplicationOutcomeV1.GENERATED,
                sidecar.commentary_state,
                binding,
                executor_identity=capability.executor_identity,
                sidecar=sidecar,
            )
        if capability.availability is VoiceExecutorAvailabilityV1.UNAVAILABLE:
            return EditorVoiceApplicationResultV1(
                outcome=EditorVoiceApplicationOutcomeV1.UNAVAILABLE,
                commentary_state=PublicCommentaryStateV1.UNAVAILABLE,
                generation_possible=False,
                binding=binding,
                sidecar_identity=(
                    None if sidecar is None else voice_sidecar_identity(sidecar)
                ),
                executor_identity=capability.executor_identity,
                safe_failure_code=capability.safe_reason,
            )
        state = (
            PublicCommentaryStateV1.UNGENERATED
            if sidecar is None
            else sidecar.commentary_state
        )
        outcome = {
            PublicCommentaryStateV1.UNGENERATED: EditorVoiceApplicationOutcomeV1.UNGENERATED,
            PublicCommentaryStateV1.FAILED: EditorVoiceApplicationOutcomeV1.FAILED,
            PublicCommentaryStateV1.UNAVAILABLE: EditorVoiceApplicationOutcomeV1.UNGENERATED,
        }[state]
        exposed_state = (
            PublicCommentaryStateV1.UNGENERATED
            if state is PublicCommentaryStateV1.UNAVAILABLE
            else state
        )
        return self._result(
            outcome,
            exposed_state,
            binding,
            executor_identity=capability.executor_identity,
            sidecar=sidecar,
        )

    def request_generation(
        self,
        request: EditorVoiceStoryRequestV1,
        *,
        store: VoiceWorkflowSidecarStoreV1,
    ) -> EditorVoiceApplicationResultV1:
        prepared = self._prepare_and_load(request, store=store)
        if isinstance(prepared, EditorVoiceApplicationResultV1):
            return prepared
        binding, existing = prepared
        if existing is not None and (
            existing.commentary_state is PublicCommentaryStateV1.GENERATED
        ):
            return self._result(
                EditorVoiceApplicationOutcomeV1.GENERATED,
                existing.commentary_state,
                binding,
                executor_identity=self._executor.inspect_capability().executor_identity,
                sidecar=existing,
            )

        capability = self._executor.inspect_capability()
        if (
            capability.availability is VoiceExecutorAvailabilityV1.AVAILABLE
            and binding.runtime_input_identity is None
        ):
            return _invalid("voice_runtime_input_identity_missing")
        execution = self._executor.execute(
            VoiceExecutorRequestV1(
                binding=binding,
                next_attempt_ordinal=(0 if existing is None else len(existing.attempts))
                + 1,
            )
        )
        if (
            capability.availability is not VoiceExecutorAvailabilityV1.UNAVAILABLE
            or execution.outcome is not VoiceExecutorAvailabilityV1.UNAVAILABLE
            or execution.executor_identity != capability.executor_identity
        ):
            return _invalid("voice_executor_contract_mismatch")

        now = self._clock()
        if now.tzinfo is None:
            return _invalid("voice_application_clock_is_not_timezone_aware")
        sidecar = (
            VoiceWorkflowSidecarV1(
                binding=binding,
                commentary_state=PublicCommentaryStateV1.UNAVAILABLE,
                created_at=now,
                updated_at=now,
                provenance_references=(capability.executor_identity,),
            )
            if existing is None
            else VoiceWorkflowSidecarV1.model_validate(
                {
                    **existing.model_dump(mode="python"),
                    "commentary_state": PublicCommentaryStateV1.UNAVAILABLE,
                    "updated_at": now,
                }
            )
        )
        identity = store.save(sidecar, draft=request.draft)
        return EditorVoiceApplicationResultV1(
            outcome=EditorVoiceApplicationOutcomeV1.UNAVAILABLE,
            commentary_state=PublicCommentaryStateV1.UNAVAILABLE,
            generation_possible=False,
            binding=binding,
            sidecar_identity=identity,
            executor_identity=execution.executor_identity,
            executor_port_invoked=True,
            attempt_created=False,
            safe_failure_code=execution.safe_reason,
        )

    def _prepare_and_load(self, request, *, store):
        try:
            binding = self.prepare_binding(request)
            sidecar = (
                store.load(draft=request.draft)
                if store is not None and store.path.exists()
                else None
            )
            if sidecar is not None and sidecar.binding != binding:
                raise VoiceWorkflowSidecarIntegrityError(
                    "Voice sidecar binding mismatch"
                )
            story = next(
                item for item in request.draft.stories if item.event_id == request.event_id
            )
            if sidecar is None and story.acid_commentary is not None:
                raise VoiceWorkflowSidecarIntegrityError(
                    "persisted commentary lacks Voice sidecar binding"
                )
        except (ValueError, OSError):
            return _invalid("voice_story_binding_invalid")
        return binding, sidecar

    def inspect_persisted_story(
        self,
        *,
        draft,
        story_material_reference: str,
        event_id: int,
        sidecar_path: Path | None,
    ) -> EditorVoiceApplicationResultV1:
        store = (
            None
            if sidecar_path is None
            else VoiceWorkflowSidecarStoreV1(sidecar_path)
        )
        try:
            persisted = (
                store.load(draft=draft)
                if store is not None and store.path.exists()
                else None
            )
        except (ValueError, OSError):
            return _invalid("voice_story_binding_invalid")
        story = next((item for item in draft.stories if item.event_id == event_id), None)
        if story is None:
            return _invalid("voice_story_binding_invalid")
        request = EditorVoiceStoryRequestV1(
            draft=draft,
            story_material_reference=story_material_reference,
            event_id=event_id,
            expected_semantic_draft_revision_identity=(
                semantic_draft_revision_identity(draft)
            ),
            expected_event_authority_identity=(
                story.factual_summary.authority_bundle_identity
            ),
            commentary_background_authority_identity=(
                None
                if persisted is None
                else persisted.binding.commentary_background_authority_identity
            ),
            runtime_input_identity=(
                None if persisted is None else persisted.binding.runtime_input_identity
            ),
        )
        return self.inspect(request, store=store)

    @staticmethod
    def _result(
        outcome,
        state,
        binding,
        *,
        executor_identity,
        sidecar=None,
    ):
        return EditorVoiceApplicationResultV1(
            outcome=outcome,
            commentary_state=state,
            generation_possible=outcome
            in {
                EditorVoiceApplicationOutcomeV1.UNGENERATED,
                EditorVoiceApplicationOutcomeV1.FAILED,
            },
            binding=binding,
            sidecar_identity=(
                None if sidecar is None else voice_sidecar_identity(sidecar)
            ),
            executor_identity=executor_identity,
        )


__all__ = ["EditorVoiceApplicationServiceV1"]

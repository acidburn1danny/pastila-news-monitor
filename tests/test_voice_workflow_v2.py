from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from pastila_scout.editor.generation.semantic_draft_v2 import (
    AcidCommentaryV2,
    AuthorityDensityV2,
    FactualNucleusBindingV2,
    FactualSummaryV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
    SemanticStoryV2,
)
from pastila_scout.voice_workflow_v2 import (
    AcceptedCommentaryBindingV1,
    PersistedVoiceAttemptOutcomeV1,
    PublicCommentaryStateV1,
    TransientCommentaryStateV1,
    UnknownVoiceWorkflowSidecarVersionError,
    VoiceAttemptRecordV1,
    VoiceStoryBindingV1,
    VoiceValidationResultV1,
    VoiceWorkflowSidecarIntegrityError,
    VoiceWorkflowSidecarStoreV1,
    VoiceWorkflowSidecarV1,
    append_voice_attempt,
    canonical_voice_sidecar_bytes,
    sha256_identity,
    voice_sidecar_identity,
)

NOW = datetime(2026, 8, 22, 10, 30, tzinfo=UTC)


def _sha(label: str) -> str:
    return f"sha256:{hashlib.sha256(label.encode()).hexdigest()}"


def _summary(text: str = "Primăria a publicat raportul.") -> FactualSummaryV2:
    return FactualSummaryV2(
        text=text,
        authority_bundle_identity="event-authority:42:v1",
        authority_density=AuthorityDensityV2.THIN,
        nucleus_bindings=(
            FactualNucleusBindingV2(
                nucleus_id="nucleus-1",
                sentence_number=1,
                authority_fact_ids=("fact-1",),
            ),
        ),
        model_identifier="pastila-editor-core-v1.2-experimental",
        provider="ollama",
        validation_receipt="core-validation:pass",
    )


def _draft(
    *, commentary: AcidCommentaryV2 | None = None, summary_text: str | None = None
) -> PastilaEditorSemanticDraftV2:
    story = SemanticStoryV2(
        event_id=42,
        position=1,
        factual_summary=_summary(summary_text or "Primăria a publicat raportul."),
        acid_commentary=commentary,
        acid_commentary_status=(
            "present" if commentary else "absent_voice_layer_unavailable"
        ),
    )
    return PastilaEditorSemanticDraftV2.assemble(
        episode_id="episode-42",
        mode=(
            SemanticDraftModeV2.CORE_PLUS_VOICE
            if commentary
            else SemanticDraftModeV2.CORE_ONLY
        ),
        stories=(story,),
    )


def _draft_identity(draft: PastilaEditorSemanticDraftV2) -> str:
    payload = json.dumps(
        draft.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256_identity(payload)


def _binding(draft: PastilaEditorSemanticDraftV2) -> VoiceStoryBindingV1:
    story = draft.stories[0]
    return VoiceStoryBindingV1(
        story_material_reference="editor-material-v2:event:42:revision:1",
        semantic_draft_revision_identity=_draft_identity(draft),
        event_id=42,
        factual_summary_sha256=sha256_identity(story.factual_summary.text),
        event_authority_identity=story.factual_summary.authority_bundle_identity,
        commentary_background_authority_identity=None,
        runtime_input_identity=_sha("runtime-input"),
    )


def _failed_attempt(ordinal: int) -> VoiceAttemptRecordV1:
    return VoiceAttemptRecordV1(
        attempt_identity=_sha(f"attempt-{ordinal}"),
        ordinal=ordinal,
        outcome=PersistedVoiceAttemptOutcomeV1.FAILED,
        runtime_input_identity=_sha("runtime-input"),
        voice_model_package_identity=None,
        validation_result=VoiceValidationResultV1.NOT_REACHED,
        failure_identity="voice-executor:unavailable",
        started_at=NOW + timedelta(minutes=ordinal),
        completed_at=NOW + timedelta(minutes=ordinal, seconds=1),
        execution_provenance=("editor:event:42",),
    )


def _empty_sidecar(draft: PastilaEditorSemanticDraftV2) -> VoiceWorkflowSidecarV1:
    return VoiceWorkflowSidecarV1(
        binding=_binding(draft),
        commentary_state=PublicCommentaryStateV1.UNGENERATED,
        created_at=NOW,
        updated_at=NOW,
        provenance_references=("semantic-draft-v2",),
    )


def test_sidecar_round_trip_is_canonical_deterministic_and_draft_immutable(
    tmp_path: Path,
) -> None:
    draft = _draft()
    original = draft.model_dump_json()
    sidecar = _empty_sidecar(draft)
    store = VoiceWorkflowSidecarStoreV1(tmp_path / "voice-workflow.json")

    identity = store.save(sidecar, draft=draft)
    first = store.path.read_bytes()
    loaded = store.load(draft=draft)
    second_identity = store.save(loaded, draft=draft)

    assert loaded == sidecar
    assert first == canonical_voice_sidecar_bytes(sidecar) == store.path.read_bytes()
    assert identity == second_identity == voice_sidecar_identity(sidecar)
    assert draft.model_dump_json() == original


def test_retry_appends_story_scoped_terminal_attempts_without_overwrite() -> None:
    draft = _draft()
    initial = _empty_sidecar(draft)
    first = append_voice_attempt(
        initial, _failed_attempt(1), updated_at=NOW + timedelta(minutes=2)
    )
    second = append_voice_attempt(
        first, _failed_attempt(2), updated_at=NOW + timedelta(minutes=3)
    )

    assert initial.attempts == ()
    assert tuple(item.ordinal for item in second.attempts) == (1, 2)
    assert second.commentary_state is PublicCommentaryStateV1.FAILED
    with pytest.raises(ValueError, match="ordinal"):
        append_voice_attempt(
            second, _failed_attempt(4), updated_at=NOW + timedelta(minutes=4)
        )

    unavailable_with_history = VoiceWorkflowSidecarV1.model_validate(
        {
            **second.model_dump(mode="python"),
            "commentary_state": PublicCommentaryStateV1.UNAVAILABLE,
        }
    )
    assert len(unavailable_with_history.attempts) == 2
    public_values = VoiceWorkflowSidecarV1.model_json_schema()["$defs"][
        "PublicCommentaryStateV1"
    ]["enum"]
    assert TransientCommentaryStateV1.EXECUTING.value not in public_values


def test_generated_commentary_must_be_adjacent_and_match_exact_v2_bytes(
    tmp_path: Path,
) -> None:
    commentary = AcidCommentaryV2(
        text="Raport publicat. Panica poate lua liber.",
        voice_model_identity="voice-package:v2",
        factual_boundary_receipt="voice-boundary:pass",
    )
    draft = _draft(commentary=commentary)
    attempt = VoiceAttemptRecordV1(
        attempt_identity=_sha("attempt-generated"),
        ordinal=1,
        outcome=PersistedVoiceAttemptOutcomeV1.GENERATED,
        runtime_input_identity=_sha("runtime-input"),
        voice_model_package_identity="voice-package:v2",
        validation_result=VoiceValidationResultV1.PASSED,
        output_sha256=sha256_identity(commentary.text),
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=2),
    )
    accepted = AcceptedCommentaryBindingV1(
        attempt_identity=attempt.attempt_identity,
        attempt_ordinal=1,
        acid_commentary_identity=_sha("acid-commentary"),
        output_sha256=sha256_identity(commentary.text),
        voice_model_package_identity="voice-package:v2",
        factual_boundary_validation_receipt="voice-boundary:pass",
        accepted_at=NOW + timedelta(seconds=2),
    )
    sidecar = VoiceWorkflowSidecarV1(
        binding=_binding(draft),
        commentary_state=PublicCommentaryStateV1.GENERATED,
        attempts=(attempt,),
        accepted_commentary=accepted,
        created_at=NOW,
        updated_at=NOW + timedelta(seconds=2),
    )
    store = VoiceWorkflowSidecarStoreV1(tmp_path / "voice-workflow.json")

    store.save(sidecar, draft=draft)
    assert store.load(draft=draft) == sidecar
    with pytest.raises(VoiceWorkflowSidecarIntegrityError, match="revision mismatch"):
        store.load(draft=_draft())


def test_unknown_or_noncanonical_sidecar_fails_closed(tmp_path: Path) -> None:
    draft = _draft()
    path = tmp_path / "voice-workflow.json"
    path.write_text(
        json.dumps(
            {
                "schema_name": "pastila-voice-workflow-sidecar",
                "schema_version": "2",
            }
        ),
        encoding="utf-8",
    )
    store = VoiceWorkflowSidecarStoreV1(path)
    with pytest.raises(UnknownVoiceWorkflowSidecarVersionError):
        store.load(draft=draft)

    sidecar = _empty_sidecar(draft)
    path.write_text(
        json.dumps(sidecar.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with pytest.raises(VoiceWorkflowSidecarIntegrityError, match="not canonical"):
        store.load(draft=draft)


def test_factual_summary_or_authority_rebinding_fails_closed(tmp_path: Path) -> None:
    draft = _draft()
    store = VoiceWorkflowSidecarStoreV1(tmp_path / "voice-workflow.json")
    store.save(_empty_sidecar(draft), draft=draft)

    changed = _draft(summary_text="Primăria a retras raportul.")
    with pytest.raises(VoiceWorkflowSidecarIntegrityError, match="revision mismatch"):
        store.load(draft=changed)

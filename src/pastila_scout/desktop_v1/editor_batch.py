"""Sequential, recoverable orchestration for selected Editor worklist items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pastila_scout.episode_draft_v1 import (
    EpisodeDraftExcludedFailureV1,
    EpisodeDraftFailureStageV1,
)


@dataclass(frozen=True, slots=True)
class _EditorBatchResultV1:
    attempted_event_ids: tuple[int, ...]
    completed_event_ids: tuple[int, ...]
    failed_event_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        attempted = self.attempted_event_ids
        completed = set(self.completed_event_ids)
        failed = set(self.failed_event_ids)
        if (
            not attempted
            or any(type(value) is not int or value <= 0 for value in attempted)
            or len(attempted) != len(set(attempted))
            or completed.intersection(failed)
            or completed.union(failed) != set(attempted)
            or self.completed_event_ids
            != tuple(value for value in attempted if value in completed)
            or self.failed_event_ids
            != tuple(value for value in attempted if value in failed)
        ):
            raise ValueError("Invalid Editor batch result")


def _run_editor_batch_v1(
    *, store, event_ids: tuple[int, ...], execute
) -> _EditorBatchResultV1:
    if (
        type(event_ids) is not tuple
        or not event_ids
        or any(type(value) is not int or value <= 0 for value in event_ids)
        or len(event_ids) != len(set(event_ids))
        or not callable(execute)
    ):
        raise ValueError("Invalid Editor batch")
    project = store.load_runtime_state()
    selected = set(event_ids)
    ordered = tuple(
        item.event_id for item in project.editor_worklist if item.event_id in selected
    )
    statuses = {item.event_id: item.status.value for item in project.editor_worklist}
    if len(ordered) != len(event_ids) or any(
        statuses[event_id] != "pending" for event_id in ordered
    ):
        raise ValueError("Invalid Editor batch")
    completed: list[int] = []
    failed: list[int] = []
    for event_id in ordered:
        store.mark_editor_item_running(event_id=event_id)
        try:
            output_path, payload_sha256 = execute(event_id)
            if not isinstance(output_path, Path) or type(payload_sha256) is not str:
                raise ValueError("Invalid Editor result")
            store.record_editor_output_for_event(
                event_id=event_id,
                output_path=output_path,
                payload_sha256=payload_sha256,
            )
            store.mark_editor_item_completed(event_id=event_id)
            completed.append(event_id)
        except Exception:  # noqa: BLE001 - one item failure must not abort the batch
            store.mark_editor_item_failed(event_id=event_id)
            current = store.load_runtime_state()
            title = next(
                event.canonical_title
                for event in current.scout_input.ranked_events
                if event.event_id == event_id
            )
            store.record_terminal_editor_failure(
                evidence=EpisodeDraftExcludedFailureV1(
                    event_id=event_id,
                    title_snapshot=title,
                    attempt_count=1,
                    failure_stage=EpisodeDraftFailureStageV1.UNKNOWN,
                    failure_category="editor_execution_failed",
                    sanitized_reason="Generarea Editor a esuat.",
                    failure_evidence_reference=f"editor-batch-v1:event:{event_id}",
                )
            )
            failed.append(event_id)
    return _EditorBatchResultV1(ordered, tuple(completed), tuple(failed))


__all__: tuple[str, ...] = ()

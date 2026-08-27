"""Sequential, recoverable orchestration for selected Editor worklist items."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
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
    *,
    store,
    event_ids: tuple[int, ...],
    execute,
    provider_id: str | None = None,
    model_id: str | None = None,
    diagnostics_directory: Path | None = None,
) -> _EditorBatchResultV1:
    provider_id = provider_id or getattr(execute, "_diagnostic_provider_id", None)
    model_id = model_id or getattr(execute, "_diagnostic_model_id", None)
    diagnostics_directory = diagnostics_directory or getattr(
        execute, "_diagnostics_directory", None
    )
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
        except Exception as exc:  # noqa: BLE001 - one item failure must not abort the batch
            store.mark_editor_item_failed(event_id=event_id)
            current = store.load_runtime_state()
            title = next(
                event.canonical_title
                for event in current.scout_input.ranked_events
                if event.event_id == event_id
            )
            evidence_path = _persist_failure_diagnostic(
                event_id=event_id,
                exception=exc,
                provider_id=provider_id,
                model_id=model_id,
                diagnostics_directory=diagnostics_directory,
            )
            failure_code = re.sub(
                r"[^a-z0-9_.-]+", "-", type(exc).__name__.casefold()
            ).strip("-")[:80] or "exception"
            store.record_terminal_editor_failure(
                evidence=EpisodeDraftExcludedFailureV1(
                    event_id=event_id,
                    title_snapshot=title,
                    attempt_count=1,
                    failure_stage=EpisodeDraftFailureStageV1.PROVIDER_EXECUTION,
                    failure_category="editor_execution_failed",
                    failure_code=failure_code,
                    sanitized_reason="Generarea Editor a esuat.",
                    failure_evidence_reference=(
                        str(evidence_path)
                        if evidence_path is not None
                        else f"editor-batch-v1:event:{event_id}"
                    ),
                    provider_id=provider_id,
                    model_id=model_id,
                    validation_path=(str(evidence_path) if evidence_path else None),
                    last_successful_stage="batch_execute_started",
                )
            )
            failed.append(event_id)
    return _EditorBatchResultV1(ordered, tuple(completed), tuple(failed))


def _persist_failure_diagnostic(
    *,
    event_id: int,
    exception: Exception,
    provider_id: str | None,
    model_id: str | None,
    diagnostics_directory: Path | None,
) -> Path | None:
    if diagnostics_directory is None:
        return None
    diagnostics_directory.mkdir(parents=True, exist_ok=True)
    path = diagnostics_directory / f"editor-event-{event_id}-attempt-1-failure.json"
    payload = {
        "attempt_number": 1,
        "event_id": event_id,
        "exception_message": str(exception)[:2000],
        "exception_type": type(exception).__name__,
        "model_id": model_id,
        "provider_id": provider_id,
        "stage": "provider_execution",
        "stored_at": datetime.now(UTC).isoformat(),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path.resolve()


def _persist_application_result_diagnostic(
    *,
    event_id: int,
    application_result,
    provider_id: str,
    model_id: str,
    diagnostics_directory: Path | None,
) -> Path | None:
    """Retain the safe application failure result before the shell collapses it."""
    if diagnostics_directory is None:
        return None
    diagnostics_directory.mkdir(parents=True, exist_ok=True)
    failure = application_result.failure
    path = diagnostics_directory / (
        f"editor-event-{event_id}-application-result-failure.json"
    )
    payload = {
        "event_id": event_id,
        "failure": (
            None
            if failure is None
            else {"code": failure.code.value, "message": failure.safe_message}
        ),
        "handoff_permitted": application_result.handoff_permitted,
        "lifecycle": [state.value for state in application_result.lifecycle],
        "model_id": model_id,
        "output_path": (
            None
            if application_result.output_path is None
            else str(application_result.output_path)
        ),
        "output_path_present": application_result.output_path is not None,
        "payload_sha256": application_result.payload_sha256,
        "payload_sha256_present": application_result.payload_sha256 is not None,
        "provider_id": provider_id,
        "status": application_result.status.value,
        "stored_at": datetime.now(UTC).isoformat(),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path.resolve()


__all__: tuple[str, ...] = ()

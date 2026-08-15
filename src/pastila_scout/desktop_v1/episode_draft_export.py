"""Read-only export of the immutable Episode Draft selected by ActiveProject."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pastila_scout.editor_application_v1 import (
    EditorAtomicExporterV1,
    EditorOutputDestinationV1,
    EditorOverwritePolicyV1,
)
from pastila_scout.episode_draft_v1 import EpisodeDraftPersistenceError


@dataclass(frozen=True, slots=True)
class _EpisodeDraftExportResultV1:
    status: str
    succeeded: bool = False
    destination: Path | None = None


def _episode_draft_default_filename_v1(revision_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", revision_id).strip("-_")
    suffix = (safe or "revision")[-24:]
    return f"PastilaScout-EpisodeDraft-{suffix}.md"


def _export_current_episode_draft_v1(
    *, store, destination: Path, exporter=None, read_bytes=None
) -> _EpisodeDraftExportResultV1:
    """Resolve, render and atomically export the exact active revision."""

    try:
        before = store.load_runtime_state()
        if before is None or before.current_episode_draft_revision is None:
            return _result("Nu exista un draft de episod pentru export.")
        revision = store.load_episode_draft_revision()
        if revision is None:
            return _result("Revizia draftului nu a putut fi gasita.")
        payload = _render_episode_draft_v1(revision)
    except EpisodeDraftPersistenceError, OSError, TypeError, ValueError:
        return _result("Revizia draftului nu a putut fi verificata.")

    if destination.exists():
        return _result("Fisierul exista deja. Alegeti o alta destinatie.")
    try:
        writer = exporter if exporter is not None else EditorAtomicExporterV1()
        published = writer.publish(
            payload=payload,
            destination=EditorOutputDestinationV1(
                path=destination,
                overwrite_policy=EditorOverwritePolicyV1.FAIL_IF_EXISTS,
            ),
        )
    except Exception:  # noqa: BLE001 - desktop boundary exposes one safe status
        return _result("Draftul nu a putut fi scris la destinatia aleasa.")
    try:
        restored = (
            read_bytes(published) if read_bytes is not None else published.read_bytes()
        )
        after = store.load_runtime_state()
    except Exception:  # noqa: BLE001 - read-back/repository failures are finite
        return _result("Fisierul exportat nu a putut fi verificat.")
    if restored != payload or after != before:
        return _result("Fisierul exportat nu a putut fi verificat.")
    return _EpisodeDraftExportResultV1(
        status=f"Draft exportat: {published.name}",
        succeeded=True,
        destination=published,
    )


def _render_episode_draft_v1(revision) -> bytes:
    lines = [
        "# Pastila Scout - Draft episod",
        "",
        f"- Revizie: {revision.revision_id}",
        f"- Revizie parinte: {revision.parent_revision_id or '-'}",
        f"- Episod: {revision.episode_id}",
        f"- Stiri incluse: {len(revision.included_event_ids)}",
        f"- Esecuri excluse: {len(revision.excluded_failures)}",
        "",
        "## Stiri incluse",
        "",
    ]
    for index, story in enumerate(revision.episode_draft.stories, start=1):
        lines.extend(
            (
                f"### {index}. Stirea {story.story_id}",
                "",
                story.text,
                "",
            )
        )
    lines.extend(("## Text asamblat", "", revision.episode_draft.assembled_text, ""))
    if revision.excluded_failures:
        lines.extend(("## Esecuri excluse", ""))
        for failure in revision.excluded_failures:
            lines.extend(
                (
                    f"### Stirea {failure.event_id}: {failure.title_snapshot}",
                    "",
                    failure.sanitized_reason,
                    "",
                )
            )
    return "\n".join(lines).encode("utf-8")


def _result(status: str) -> _EpisodeDraftExportResultV1:
    return _EpisodeDraftExportResultV1(status=status)


__all__: tuple[str, ...] = ()

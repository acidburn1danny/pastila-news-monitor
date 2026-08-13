"""Small persisted bridge between a Scout event and the Editor desktop flow."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pastila_scout import __version__
from pastila_scout.category_integrity import CATEGORY_ORDER
from pastila_scout.contracts.common import ALLOWED_CATEGORIES
from pastila_scout.contracts.identity import (
    assign_scout_input_identity,
    verify_scout_input_identity,
)
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.episode_draft_v1 import (
    EpisodeDraftExcludedFailureV1,
    EpisodeDraftPersistenceError,
    EpisodeDraftRevisionRefV1,
    EpisodeDraftRevisionRepositoryV1,
)


@dataclass(frozen=True, slots=True)
class ScoutCandidateV1:
    event_id: int
    title: str
    summary: str
    category: str
    source_count: int
    article_count: int


@dataclass(frozen=True, slots=True)
class EditorMaterialV1:
    reference: str
    event_id: int
    title: str
    summary: str
    output_path: str | None = None
    payload_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class ChiefEditorItemV1:
    material_reference: str
    section: str = ""
    note: str = ""


class EditorWorkItemStatusV1(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class EditorWorkItemV1:
    event_id: int
    status: EditorWorkItemStatusV1 = EditorWorkItemStatusV1.PENDING

    def __post_init__(self) -> None:
        if type(self.event_id) is not int or self.event_id <= 0:
            raise ValueError("Element Editor invalid")
        if type(self.status) is not EditorWorkItemStatusV1:
            raise ValueError("Stare Editor invalida")


@dataclass(frozen=True, slots=True)
class ActiveProjectV1:
    project_id: str
    title: str
    handed_off_at: datetime
    scout_input: ScoutEditorInputV1
    editor_materials: tuple[EditorMaterialV1, ...] = ()
    chief_editor_items: tuple[ChiefEditorItemV1, ...] = ()
    chief_editor_title: str = ""
    chief_editor_updated_at: datetime | None = None
    editor_worklist: tuple[EditorWorkItemV1, ...] = ()
    current_episode_draft_revision: EpisodeDraftRevisionRefV1 | None = None
    editor_terminal_failures: tuple[EpisodeDraftExcludedFailureV1, ...] = ()

    @property
    def candidate(self):
        return self.scout_input.ranked_events[0]


class ActiveProjectStoreV1:
    """Persist exactly one active local project using atomic replacement."""

    def __init__(self, *, database_path: Path, project_path: Path) -> None:
        self.database_path = database_path
        self.project_path = project_path

    def list_candidates(self, *, limit: int = 50) -> tuple[ScoutCandidateV1, ...]:
        if not self.database_path.is_file():
            return ()
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            category_order = " ".join(
                f"WHEN ? THEN {position}"
                for position, _category_name in enumerate(CATEGORY_ORDER)
            )
            rows = connection.execute(
                f"""SELECT id, canonical_title, summary, category, source_count,
                           article_count
                    FROM (
                        SELECT id, canonical_title, summary, category, source_count,
                               article_count, last_seen_at
                        FROM events
                        WHERE TRIM(canonical_title) <> ''
                          AND TRIM(COALESCE(summary, '')) <> ''
                        ORDER BY last_seen_at DESC, id DESC
                        LIMIT ?
                    ) AS recent_candidates
                   ORDER BY CASE category {category_order} ELSE {len(CATEGORY_ORDER)} END,
                            source_count DESC, last_seen_at DESC, id ASC""",
                (limit, *CATEGORY_ORDER),
            ).fetchall()
        return tuple(
            ScoutCandidateV1(
                event_id=int(row["id"]),
                title=str(row["canonical_title"]),
                summary=str(row["summary"]),
                category=_category(row["category"]),
                source_count=int(row["source_count"]),
                article_count=int(row["article_count"]),
            )
            for row in rows
        )

    def list_candidates_by_ids(
        self, *, event_ids: tuple[int, ...]
    ) -> tuple[ScoutCandidateV1, ...]:
        if (
            type(event_ids) is not tuple
            or any(type(value) is not int or value <= 0 for value in event_ids)
            or len(event_ids) != len(set(event_ids))
        ):
            raise ValueError("Selectie Scout invalida")
        if not event_ids or not self.database_path.is_file():
            return ()
        placeholders = ",".join("?" for _ in event_ids)
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                f"""SELECT id, canonical_title, summary, category, source_count,
                           article_count
                    FROM events
                    WHERE id IN ({placeholders})
                      AND TRIM(canonical_title) <> ''
                      AND TRIM(COALESCE(summary, '')) <> ''""",
                event_ids,
            ).fetchall()
        by_id = {int(row["id"]): row for row in rows}
        return tuple(
            ScoutCandidateV1(
                event_id=int(row["id"]),
                title=str(row["canonical_title"]),
                summary=str(row["summary"]),
                category=_category(row["category"]),
                source_count=int(row["source_count"]),
                article_count=int(row["article_count"]),
            )
            for event_id in event_ids
            if (row := by_id.get(event_id)) is not None
        )

    def load_runtime_state(self) -> ActiveProjectV1 | None:
        """Read current in-process state without restart recovery transitions."""

        return self._load(recover_running=False)

    def handoff(self, *, event_id: int) -> ActiveProjectV1:
        source = _scout_input(self.database_path, event_id)
        existing = self._load(recover_running=False)
        project = ActiveProjectV1(
            project_id=(
                existing.project_id
                if existing
                else f"active-project-v1:{uuid.uuid4().hex}"
            ),
            title=(
                existing.title if existing else source.ranked_events[0].canonical_title
            ),
            handed_off_at=datetime.now(UTC),
            scout_input=source,
            editor_materials=(() if existing is None else existing.editor_materials),
            chief_editor_items=(
                () if existing is None else existing.chief_editor_items
            ),
            chief_editor_title=(
                "" if existing is None else existing.chief_editor_title
            ),
            chief_editor_updated_at=(
                None if existing is None else existing.chief_editor_updated_at
            ),
            editor_worklist=_synchronize_editor_worklist(
                source.ranked_events,
                () if existing is None else existing.editor_worklist,
            ),
            current_episode_draft_revision=(
                None if existing is None else existing.current_episode_draft_revision
            ),
            editor_terminal_failures=(
                () if existing is None else existing.editor_terminal_failures
            ),
        )
        self._write(project)
        return project

    def handoff_many(
        self, *, event_ids: tuple[int, ...]
    ) -> tuple[ActiveProjectV1, int]:
        if (
            type(event_ids) is not tuple
            or not event_ids
            or any(type(value) is not int for value in event_ids)
        ):
            raise ValueError("Selectie Scout invalida")
        existing = self._load(recover_running=False)
        existing_ids = (
            ()
            if existing is None
            else tuple(item.event_id for item in existing.scout_input.ranked_events)
        )
        new_ids = tuple(
            value
            for index, value in enumerate(event_ids)
            if value not in existing_ids and value not in event_ids[:index]
        )
        inputs = []
        for value in new_ids:
            try:
                inputs.append(_scout_input(self.database_path, value))
            except ValueError:
                continue
        inputs = tuple(inputs)
        if not inputs:
            if existing is None:
                raise ValueError("Nu exista selectie Scout")
            return existing, len(event_ids)
        source = _merge_scout_inputs(
            (() if existing is None else existing.scout_input.ranked_events)
            + tuple(value.ranked_events[0] for value in inputs),
            inputs[0],
        )
        project_id = (
            existing.project_id
            if existing is not None
            else f"active-project-v1:{uuid.uuid4().hex}"
        )
        project = ActiveProjectV1(
            project_id=project_id,
            title=(
                existing.title
                if existing is not None
                else source.ranked_events[0].canonical_title
            ),
            handed_off_at=datetime.now(UTC),
            scout_input=source,
            editor_materials=(() if existing is None else existing.editor_materials),
            chief_editor_items=(
                () if existing is None else existing.chief_editor_items
            ),
            chief_editor_title=(
                "" if existing is None else existing.chief_editor_title
            ),
            chief_editor_updated_at=(
                None if existing is None else existing.chief_editor_updated_at
            ),
            editor_worklist=_synchronize_editor_worklist(
                source.ranked_events,
                () if existing is None else existing.editor_worklist,
            ),
            current_episode_draft_revision=(
                None if existing is None else existing.current_episode_draft_revision
            ),
            editor_terminal_failures=(
                () if existing is None else existing.editor_terminal_failures
            ),
        )
        self._write(project)
        return project, len(event_ids) - len(inputs)

    def record_editor_output(
        self, *, output_path: Path, payload_sha256: str
    ) -> ActiveProjectV1:
        project = self._required()
        return self._record_editor_output(
            event_id=project.candidate.event_id,
            output_path=output_path,
            payload_sha256=payload_sha256,
            require_running=False,
        )

    def record_editor_output_for_event(
        self,
        *,
        event_id: int,
        output_path: Path,
        payload_sha256: str,
    ) -> ActiveProjectV1:
        return self._record_editor_output(
            event_id=event_id,
            output_path=output_path,
            payload_sha256=payload_sha256,
            require_running=True,
        )

    def _record_editor_output(
        self,
        *,
        event_id: int,
        output_path: Path,
        payload_sha256: str,
        require_running: bool,
    ) -> ActiveProjectV1:
        project = self._required()
        matches = tuple(
            event
            for event in project.scout_input.ranked_events
            if event.event_id == event_id
        )
        if len(matches) != 1:
            raise ValueError("Material Editor invalid")
        work_items = tuple(
            item for item in project.editor_worklist if item.event_id == event_id
        )
        if (
            type(require_running) is not bool
            or len(work_items) != 1
            or (
                require_running
                and work_items[0].status is not EditorWorkItemStatusV1.RUNNING
            )
        ):
            raise ValueError("Material Editor invalid")
        event = matches[0]
        reference = f"editor-material-v1:event:{event_id}"
        material = EditorMaterialV1(
            reference=reference,
            event_id=event_id,
            title=event.canonical_title,
            summary=event.canonical_summary,
            output_path=str(output_path),
            payload_sha256=payload_sha256,
        )
        materials = tuple(
            value for value in project.editor_materials if value.reference != reference
        ) + (material,)
        chief = project.chief_editor_items
        if reference not in {item.material_reference for item in chief}:
            chief += (ChiefEditorItemV1(reference),)
        updated = ActiveProjectV1(
            project.project_id,
            project.title,
            project.handed_off_at,
            project.scout_input,
            materials,
            chief,
            project.chief_editor_title or project.title,
            datetime.now(UTC),
            project.editor_worklist,
            project.current_episode_draft_revision,
            project.editor_terminal_failures,
        )
        self._write(updated)
        return updated

    def save_chief_editor(
        self, *, title: str, items: tuple[ChiefEditorItemV1, ...]
    ) -> ActiveProjectV1:
        project = self._required()
        title = title.strip()
        if not title or len(title) > 200 or type(items) is not tuple:
            raise ValueError("Structură Chief Editor invalidă")
        references = tuple(item.material_reference for item in items)
        available = {item.reference for item in project.editor_materials}
        if (
            any(type(item) is not ChiefEditorItemV1 for item in items)
            or len(references) != len(set(references))
            or not set(references).issubset(available)
            or any(len(item.section) > 80 or len(item.note) > 500 for item in items)
        ):
            raise ValueError("Structură Chief Editor invalidă")
        updated = ActiveProjectV1(
            project.project_id,
            project.title,
            project.handed_off_at,
            project.scout_input,
            project.editor_materials,
            items,
            title,
            datetime.now(UTC),
            project.editor_worklist,
            project.current_episode_draft_revision,
            project.editor_terminal_failures,
        )
        self._write(updated)
        return updated

    def export_chief_editor(self, *, destination: Path) -> str:
        project = self._required()
        materials = {item.reference: item for item in project.editor_materials}
        lines = [project.chief_editor_title or project.title, ""]
        for number, item in enumerate(project.chief_editor_items, start=1):
            material = materials.get(item.material_reference)
            if material is None:
                continue
            section = f" [{item.section.strip()}]" if item.section.strip() else ""
            lines.append(f"{number}.{section} {material.title}")
            if item.note.strip():
                lines.append(f"   Notă / tranziție: {item.note.strip()}")
            lines.append(f"   {material.summary}")
            lines.append("")
        text = "\n".join(lines).rstrip() + "\n"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8", newline="\n")
        return text

    def mark_editor_item_running(self, *, event_id: int) -> ActiveProjectV1:
        return self._transition_editor_item(
            event_id=event_id,
            allowed=(EditorWorkItemStatusV1.PENDING,),
            target=EditorWorkItemStatusV1.RUNNING,
        )

    def mark_editor_item_completed(self, *, event_id: int) -> ActiveProjectV1:
        return self._transition_editor_item(
            event_id=event_id,
            allowed=(EditorWorkItemStatusV1.RUNNING,),
            target=EditorWorkItemStatusV1.COMPLETED,
        )

    def mark_editor_item_failed(self, *, event_id: int) -> ActiveProjectV1:
        return self._transition_editor_item(
            event_id=event_id,
            allowed=(EditorWorkItemStatusV1.RUNNING,),
            target=EditorWorkItemStatusV1.FAILED,
        )

    def retry_editor_item(self, *, event_id: int) -> ActiveProjectV1:
        return self.retry_editor_items(event_ids=(event_id,))

    def retry_editor_items(self, *, event_ids: tuple[int, ...]) -> ActiveProjectV1:
        project = self._required()
        if (
            type(event_ids) is not tuple
            or not event_ids
            or any(type(value) is not int or value <= 0 for value in event_ids)
            or len(event_ids) != len(set(event_ids))
        ):
            raise ValueError("Tranzitie Editor invalida")
        selected = set(event_ids)
        matches = tuple(
            item for item in project.editor_worklist if item.event_id in selected
        )
        if len(matches) != len(event_ids) or any(
            item.status is not EditorWorkItemStatusV1.FAILED for item in matches
        ):
            raise ValueError("Tranzitie Editor invalida")
        worklist = tuple(
            EditorWorkItemV1(item.event_id, EditorWorkItemStatusV1.PENDING)
            if item.event_id in selected
            else item
            for item in project.editor_worklist
        )
        updated = ActiveProjectV1(
            project.project_id,
            project.title,
            project.handed_off_at,
            project.scout_input,
            project.editor_materials,
            project.chief_editor_items,
            project.chief_editor_title,
            project.chief_editor_updated_at,
            worklist,
            project.current_episode_draft_revision,
            project.editor_terminal_failures,
        )
        self._write(updated)
        return updated

    def _transition_editor_item(
        self,
        *,
        event_id: int,
        allowed: tuple[EditorWorkItemStatusV1, ...],
        target: EditorWorkItemStatusV1,
    ) -> ActiveProjectV1:
        project = self._required()
        matches = tuple(
            item for item in project.editor_worklist if item.event_id == event_id
        )
        if len(matches) != 1 or matches[0].status not in allowed:
            raise ValueError("Tranzitie Editor invalida")
        worklist = tuple(
            EditorWorkItemV1(item.event_id, target)
            if item.event_id == event_id
            else item
            for item in project.editor_worklist
        )
        updated = ActiveProjectV1(
            project.project_id,
            project.title,
            project.handed_off_at,
            project.scout_input,
            project.editor_materials,
            project.chief_editor_items,
            project.chief_editor_title,
            project.chief_editor_updated_at,
            worklist,
            project.current_episode_draft_revision,
            project.editor_terminal_failures,
        )
        self._write(updated)
        return updated

    def install_episode_draft_revision(
        self, *, reference: EpisodeDraftRevisionRefV1
    ) -> ActiveProjectV1:
        """Atomically install one already-published, strictly validated ready revision."""

        project = self._required()
        try:
            if type(reference) is not EpisodeDraftRevisionRefV1:
                raise TypeError
            revision = EpisodeDraftRevisionRepositoryV1().load(
                path=Path(reference.artifact_path),
                artifact_sha256=reference.artifact_sha256,
            )
            if (
                reference.project_id != project.project_id
                or revision.project_id != project.project_id
                or reference.draft_id != revision.draft_id
                or reference.revision_id != revision.revision_id
                or reference.parent_revision_id != revision.parent_revision_id
                or reference.episode_id != revision.episode_id
                or reference.requested_event_ids != revision.requested_event_ids
                or reference.included_event_ids != revision.included_event_ids
                or reference.excluded_failed_event_ids
                != revision.excluded_failed_event_ids
                or reference.created_at != revision.created_at
            ):
                raise ValueError
            if tuple(item.event_id for item in project.editor_worklist) != (
                revision.requested_event_ids
            ):
                raise ValueError
            statuses = {item.event_id: item.status for item in project.editor_worklist}
            if any(
                statuses[event_id] is not EditorWorkItemStatusV1.COMPLETED
                for event_id in revision.included_event_ids
            ) or any(
                statuses[event_id] is not EditorWorkItemStatusV1.FAILED
                for event_id in revision.excluded_failed_event_ids
            ):
                raise ValueError
            if len({item.event_id for item in project.editor_materials}) != len(
                project.editor_materials
            ) or len({item.reference for item in project.editor_materials}) != len(
                project.editor_materials
            ):
                raise ValueError
            materials = {item.event_id: item for item in project.editor_materials}
            for lineage in revision.included_materials:
                material = materials.get(lineage.event_id)
                if (
                    material is None
                    or material.reference != lineage.material_reference
                    or material.payload_sha256 != lineage.payload_sha256
                ):
                    raise ValueError
            terminal_failures = {
                item.event_id: item for item in project.editor_terminal_failures
            }
            if (
                len(terminal_failures) != len(project.editor_terminal_failures)
                or tuple(
                    terminal_failures.get(event_id)
                    for event_id in revision.excluded_failed_event_ids
                )
                != revision.excluded_failures
            ):
                raise ValueError
            current = project.current_episode_draft_revision
            if current is None:
                if reference.parent_revision_id is not None:
                    raise ValueError
            elif (
                reference.draft_id != current.draft_id
                or reference.parent_revision_id != current.revision_id
                or reference.revision_id == current.revision_id
            ):
                raise ValueError
        except (EpisodeDraftPersistenceError, TypeError, ValueError) as exc:
            raise ValueError("Revizie Episode Draft invalida") from exc
        if self._required() != project:
            raise ValueError("Revizie Episode Draft invalida")
        updated = ActiveProjectV1(
            project.project_id,
            project.title,
            project.handed_off_at,
            project.scout_input,
            project.editor_materials,
            project.chief_editor_items,
            project.chief_editor_title,
            project.chief_editor_updated_at,
            project.editor_worklist,
            reference,
            project.editor_terminal_failures,
        )
        self._write(updated)
        return updated

    def load_episode_draft_revision(self):
        """Load the current referenced revision without fallback or provider work."""

        project = self._required()
        reference = project.current_episode_draft_revision
        if reference is None:
            return None
        revision = EpisodeDraftRevisionRepositoryV1().load(
            path=Path(reference.artifact_path),
            artifact_sha256=reference.artifact_sha256,
        )
        if (
            revision.project_id != project.project_id
            or reference.project_id != revision.project_id
            or revision.revision_id != reference.revision_id
            or revision.draft_id != reference.draft_id
            or revision.parent_revision_id != reference.parent_revision_id
            or revision.episode_id != reference.episode_id
            or revision.created_at != reference.created_at
            or revision.requested_event_ids != reference.requested_event_ids
            or revision.included_event_ids != reference.included_event_ids
            or revision.excluded_failed_event_ids != reference.excluded_failed_event_ids
        ):
            raise EpisodeDraftPersistenceError("referenced revision identity mismatch")
        return revision

    def record_terminal_editor_failure(
        self, *, evidence: EpisodeDraftExcludedFailureV1
    ) -> ActiveProjectV1:
        """Persist explicit terminal evidence without changing generation behavior."""

        project = self._required()
        if type(evidence) is not EpisodeDraftExcludedFailureV1:
            raise ValueError("Evidenta esec Editor invalida")
        events = tuple(
            event
            for event in project.scout_input.ranked_events
            if event.event_id == evidence.event_id
        )
        matches = tuple(
            item
            for item in project.editor_worklist
            if item.event_id == evidence.event_id
        )
        if (
            len(events) != 1
            or evidence.title_snapshot != events[0].canonical_title
            or len(matches) != 1
            or matches[0].status is not EditorWorkItemStatusV1.FAILED
            or any(
                item.event_id == evidence.event_id for item in project.editor_materials
            )
            or any(
                item.event_id == evidence.event_id
                for item in project.editor_terminal_failures
            )
        ):
            raise ValueError("Evidenta esec Editor invalida")
        updated = ActiveProjectV1(
            project.project_id,
            project.title,
            project.handed_off_at,
            project.scout_input,
            project.editor_materials,
            project.chief_editor_items,
            project.chief_editor_title,
            project.chief_editor_updated_at,
            project.editor_worklist,
            project.current_episode_draft_revision,
            (*project.editor_terminal_failures, evidence),
        )
        self._write(updated)
        return updated

    def _required(self) -> ActiveProjectV1:
        project = self._load(recover_running=False)
        if project is None:
            raise ValueError("Nu există proiect activ")
        return project

    def _write(self, project: ActiveProjectV1) -> None:
        self.project_path.parent.mkdir(parents=True, exist_ok=True)
        worklist = _synchronize_editor_worklist(
            project.scout_input.ranked_events, project.editor_worklist
        )
        payload = {
            "version": "active-project-v1",
            "project_id": project.project_id,
            "title": project.title,
            "handed_off_at": project.handed_off_at.isoformat(),
            "scout_input": project.scout_input.model_dump(mode="json"),
            "editor_materials": [
                {
                    "reference": item.reference,
                    "event_id": item.event_id,
                    "title": item.title,
                    "summary": item.summary,
                    "output_path": item.output_path,
                    "payload_sha256": item.payload_sha256,
                }
                for item in project.editor_materials
            ],
            "editor_worklist": [
                {"event_id": item.event_id, "status": item.status.value}
                for item in worklist
            ],
            "current_episode_draft_revision": (
                None
                if project.current_episode_draft_revision is None
                else project.current_episode_draft_revision.model_dump(mode="json")
            ),
            "editor_terminal_failures": [
                item.model_dump(mode="json")
                for item in project.editor_terminal_failures
            ],
            "chief_editor": {
                "title": project.chief_editor_title,
                "updated_at": (
                    None
                    if project.chief_editor_updated_at is None
                    else project.chief_editor_updated_at.isoformat()
                ),
                "items": [
                    {
                        "material_reference": item.material_reference,
                        "section": item.section,
                        "note": item.note,
                    }
                    for item in project.chief_editor_items
                ],
            },
        }
        fd, temporary = tempfile.mkstemp(
            dir=self.project_path.parent, prefix="active-project-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.project_path)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def load(self) -> ActiveProjectV1 | None:
        return self._load(recover_running=True)

    def _load(self, *, recover_running: bool) -> ActiveProjectV1 | None:
        if not self.project_path.is_file():
            return None
        data = json.loads(self.project_path.read_text(encoding="utf-8"))
        if data.get("version") != "active-project-v1":
            raise ValueError("Unsupported active project")
        source = ScoutEditorInputV1.model_validate_json(
            json.dumps(data["scout_input"], ensure_ascii=False)
        )
        verify_scout_input_identity(source)
        materials = tuple(
            EditorMaterialV1(**item) for item in data.get("editor_materials", ())
        )
        chief_data = data.get("chief_editor", {})
        chief_items = tuple(
            ChiefEditorItemV1(**item) for item in chief_data.get("items", ())
        )
        updated_at = chief_data.get("updated_at")
        raw_worklist = data.get("editor_worklist")
        raw_draft_reference = data.get("current_episode_draft_revision")
        terminal_failures = tuple(
            EpisodeDraftExcludedFailureV1.model_validate_json(
                json.dumps(item, ensure_ascii=False), strict=True
            )
            for item in data.get("editor_terminal_failures", ())
        )
        draft_reference = (
            None
            if raw_draft_reference is None
            else EpisodeDraftRevisionRefV1.model_validate_json(
                json.dumps(raw_draft_reference, ensure_ascii=False), strict=True
            )
        )
        recovered_running = False
        if raw_worklist is None:
            worklist = _synchronize_editor_worklist(source.ranked_events, ())
        else:
            if type(raw_worklist) is not list:
                raise ValueError("Lista Editor invalida")
            recovered_running = recover_running and any(
                item["status"] == EditorWorkItemStatusV1.RUNNING.value
                for item in raw_worklist
            )
            worklist = tuple(
                EditorWorkItemV1(
                    event_id=item["event_id"],
                    status=(
                        EditorWorkItemStatusV1.PENDING
                        if recover_running
                        and item["status"] == EditorWorkItemStatusV1.RUNNING.value
                        else EditorWorkItemStatusV1(item["status"])
                    ),
                )
                for item in raw_worklist
            )
            expected_ids = tuple(event.event_id for event in source.ranked_events)
            if tuple(item.event_id for item in worklist) != expected_ids:
                raise ValueError("Lista Editor invalida")
        project = ActiveProjectV1(
            project_id=str(data["project_id"]),
            title=str(data["title"]),
            handed_off_at=datetime.fromisoformat(data["handed_off_at"]),
            scout_input=source,
            editor_materials=materials,
            chief_editor_items=chief_items,
            chief_editor_title=str(chief_data.get("title", "")),
            chief_editor_updated_at=(
                None if updated_at is None else datetime.fromisoformat(updated_at)
            ),
            editor_worklist=worklist,
            current_episode_draft_revision=draft_reference,
            editor_terminal_failures=terminal_failures,
        )
        if (
            not source.ranked_events
            or project.title != project.candidate.canonical_title
        ):
            raise ValueError("Invalid active project")
        if recovered_running:
            self._write(project)
        return project


def _merge_scout_inputs(events: tuple[object, ...], template: ScoutEditorInputV1):
    data = template.model_dump(mode="python")
    ranked = []
    for rank, event in enumerate(events, start=1):
        value = event.model_dump(mode="python")
        value["rank"] = rank
        value["score_rank"] = rank
        ranked.append(value)
    data["ranked_events"] = ranked
    data["event_counts"] = {
        "eligible": len(ranked),
        "processed": len(ranked),
        "reported": len(ranked),
    }
    data["ranking_parameters"]["limit"] = len(ranked)
    data["ranking_parameters"]["top"] = len(ranked)
    return assign_scout_input_identity(data)


def _synchronize_editor_worklist(
    ranked_events: tuple[object, ...], existing: tuple[EditorWorkItemV1, ...]
) -> tuple[EditorWorkItemV1, ...]:
    if type(existing) is not tuple or any(
        type(item) is not EditorWorkItemV1 for item in existing
    ):
        raise ValueError("Lista Editor invalida")
    by_event = {item.event_id: item for item in existing}
    if len(by_event) != len(existing):
        raise ValueError("Lista Editor invalida")
    event_ids = tuple(event.event_id for event in ranked_events)
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Lista Scout invalida")
    return tuple(
        by_event.get(event_id, EditorWorkItemV1(event_id)) for event_id in event_ids
    )


def move_chief_editor_item(
    items: tuple[ChiefEditorItemV1, ...], index: int, offset: int
) -> tuple[ChiefEditorItemV1, ...]:
    target = index + offset
    if (
        offset not in {-1, 1}
        or not 0 <= index < len(items)
        or not 0 <= target < len(items)
    ):
        return items
    values = list(items)
    values[index], values[target] = values[target], values[index]
    return tuple(values)


def _category(value: object) -> str:
    text = str(value or "Diverse")
    return text if text in ALLOWED_CATEGORIES else "Diverse"


def _scout_input(database_path: Path, event_id: int) -> ScoutEditorInputV1:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        event = connection.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if (
            event is None
            or not str(event["canonical_title"]).strip()
            or not str(event["summary"] or "").strip()
        ):
            raise ValueError("Candidate incomplet")
        articles = connection.execute(
            """SELECT a.source_id, COALESCE(s.name, a.source_id) source_name,
                      a.url, a.title, a.published_at
               FROM articles a LEFT JOIN sources s ON s.id = a.source_id
               WHERE a.event_id = ? ORDER BY a.id LIMIT 3""",
            (event_id,),
        ).fetchall()
        if not articles:
            raise ValueError("Candidate fără sursă")
        category = _category(event["category"])
        now = datetime.now(UTC)
        component = lambda name: {
            "raw_input": 0.0,
            "normalized_value": 0.0,
            "weighted_contribution": 0.0,
            "maximum_contribution": 0.0,
            "explanation": f"Selecție manuală; {name} nu a fost recalculat.",
        }
        data = {
            "generated_at": now,
            "report_id": "",
            "content_fingerprint": "",
            "scout_version": __version__,
            "ranking_schema_version": "desktop-manual-selection-v1",
            "source_run_id": f"snapshot:sha256:{'0' * 64}",
            "ranking_parameters": {
                "days": 1,
                "category_filter": category,
                "limit": 1,
                "top": 1,
                "minimum_score": 0.0,
                "ai_enabled": False,
            },
            "event_counts": {"eligible": 1, "processed": 1, "reported": 1},
            "ranked_events": [
                {
                    "rank": 1,
                    "score_rank": 1,
                    "event_id": event_id,
                    "canonical_title": str(event["canonical_title"]).strip(),
                    "canonical_summary": str(event["summary"]).strip(),
                    "publication_bounds": {
                        "first_published_at": event["first_published_at"],
                        "last_published_at": event["last_published_at"],
                    },
                    "categories": (category,),
                    "source_count": int(event["source_count"]),
                    "article_count": int(event["article_count"]),
                    "source_provenance": tuple(dict(row) for row in articles),
                    "provenance_truncated": int(event["article_count"]) > len(articles),
                    "deterministic_score": {
                        "score": 0.0,
                        "schema_version": "desktop-manual-selection-v1",
                        "components": {
                            name: component(name)
                            for name in (
                                "supporting_articles",
                                "source_diversity",
                                "source_credibility",
                                "recency",
                                "national_relevance",
                                "category_weight",
                                "title_strength",
                            )
                        },
                    },
                    "ai_editorial_score": None,
                    "final_score": 0.0,
                    "recommendation": "POSSIBLE_PICK",
                    "scout_recommendation_reason": "Selectat manual de utilizator pentru Editor.",
                    "editorial_risks": (),
                    "score_basis": "Selecție manuală, fără recalcularea scorului Scout.",
                    "extensions": {},
                }
            ],
            "extensions": {"pastila.active_project_handoff": True},
        }
    return assign_scout_input_identity(data)

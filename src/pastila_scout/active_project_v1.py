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
from pastila_scout.category_integrity import CATEGORY_ORDER, normalize_category
from pastila_scout.contracts.identity import (
    assign_scout_input_identity,
    verify_scout_input_identity,
)
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.editorial_evidence_v1 import EditorialEvidenceStoreV1
from pastila_scout.editorial_recommendation_v1 import (
    EditorialCandidateV1,
    EpisodeRecommendationV1,
    recommend_episode_v1,
)
from pastila_scout.editorial_recommendation_v1_1 import (
    ContinuityContextV1_1,
    EditorialCandidateV1_1,
    EpisodeRecommendationV1_1,
    recommend_episode_v1_1,
)
from pastila_scout.editorial_talkworthiness_v1_2 import (
    DiscussionBridgeContextV1_2,
    EditorialCandidateV1_2,
    EpisodeRecommendationV1_2,
    MaterialContinuityContextV1_2,
    pool_utility_v1_2,
    recommend_episode_v1_2,
)
from pastila_scout.episode_draft_v1 import (
    EpisodeDraftExcludedFailureV1,
    EpisodeDraftPersistenceError,
    EpisodeDraftRevisionRefV1,
    EpisodeDraftRevisionRepositoryV1,
)

NORMAL_SCOUT_RESULT_LIMIT = 60
_NORMAL_SCOUT_BASE_CATEGORY_CAPACITIES = (
    ("Politica", 10),
    ("CanCan", 5),
    ("Social", 15),
    ("Diverse", 15),
    ("Externe", 10),
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


class EpisodeDraftApprovalStatusV1(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"


class EpisodeDraftApprovalPersistenceError(ValueError):
    """Finite approval-state persistence failure exposed to the desktop boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class EpisodeDraftApprovalTransitionError(ValueError):
    """Finite invalid final-approval transition."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class EpisodeDraftApprovalV1:
    project_id: str
    revision_id: str
    artifact_sha256: str
    status: EpisodeDraftApprovalStatusV1 = EpisodeDraftApprovalStatusV1.PENDING_APPROVAL

    def __post_init__(self) -> None:
        if (
            type(self.project_id) is not str
            or not self.project_id.strip()
            or type(self.revision_id) is not str
            or not self.revision_id.strip()
            or type(self.artifact_sha256) is not str
            or not self.artifact_sha256.startswith("sha256:")
            or len(self.artifact_sha256) != 71
            or any(
                character not in "0123456789abcdef"
                for character in self.artifact_sha256[7:]
            )
            or type(self.status) is not EpisodeDraftApprovalStatusV1
        ):
            raise ValueError("Stare aprobare Episode Draft invalida")


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
    episode_draft_approval: EpisodeDraftApprovalV1 | None = None

    @property
    def candidate(self):
        return self.scout_input.ranked_events[0]


class ActiveProjectStoreV1:
    """Persist exactly one active local project using atomic replacement."""

    def __init__(self, *, database_path: Path, project_path: Path) -> None:
        self.database_path = database_path
        self.project_path = project_path

    def list_candidates(
        self, *, limit: int = NORMAL_SCOUT_RESULT_LIMIT, category: str | None = None
    ) -> tuple[ScoutCandidateV1, ...]:
        if type(limit) is not int or limit <= 0:
            raise ValueError("Limita Scout invalida")
        if not self.database_path.is_file():
            return ()
        selected_category = _candidate_category(category)
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            if selected_category is not None:
                rows = _ranked_candidate_rows(
                    connection, category=selected_category, limit=limit
                )
            else:
                effective_limit = min(limit, NORMAL_SCOUT_RESULT_LIMIT)
                protected = [
                    *_ranked_candidate_rows(connection, category="Politica", limit=10),
                    *_ranked_candidate_rows(connection, category="CanCan", limit=5),
                ]
                competitive = [
                    row
                    for candidate_category, capacity in (
                        _NORMAL_SCOUT_BASE_CATEGORY_CAPACITIES[2:]
                    )
                    for row in _ranked_candidate_rows(
                        connection, category=candidate_category, limit=capacity
                    )
                ]
                _sort_candidate_rows(competitive)
                rows = protected[:effective_limit]
                rows.extend(competitive[: max(0, min(50, effective_limit) - len(rows))])
                if effective_limit > 50:
                    selected_ids = {int(row["id"]) for row in rows}
                    extension = [
                        row
                        for candidate_category, capacity in (
                            _NORMAL_SCOUT_BASE_CATEGORY_CAPACITIES[2:]
                        )
                        for row in _ranked_candidate_rows(
                            connection,
                            category=candidate_category,
                            limit=capacity + 10,
                        )
                        if int(row["id"]) not in selected_ids
                    ]
                    _sort_candidate_rows(extension)
                    rows.extend(extension[: effective_limit - len(rows)])
                rows.sort(
                    key=lambda row: CATEGORY_ORDER.index(_category(row["category"]))
                )
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

    def list_useful_candidates_v1_2(
        self, *, limit: int = NORMAL_SCOUT_RESULT_LIMIT, category: str | None = None
    ) -> tuple[ScoutCandidateV1, ...]:
        """Return the explicit V1.2 human-browsable pool without filler padding.

        Normal ``Toate`` applies the utility filter before the established
        category intake capacities. Explicit category views remain pure views.
        """

        if type(limit) is not int or limit <= 0:
            raise ValueError("Limita Scout invalida")
        selected_category = _candidate_category(category)
        if selected_category is not None:
            return self.list_candidates(limit=limit, category=selected_category)
        if not self.database_path.is_file():
            return ()
        effective_limit = min(limit, NORMAL_SCOUT_RESULT_LIMIT)
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            useful_by_category: dict[str, list[sqlite3.Row]] = {}
            for candidate_category, capacity in _NORMAL_SCOUT_BASE_CATEGORY_CAPACITIES:
                scanned = _ranked_candidate_rows(
                    connection, category=candidate_category, limit=(capacity + 10) * 4
                )
                useful_by_category[candidate_category] = [
                    row
                    for row in scanned
                    if pool_utility_v1_2(_editorial_candidate_v1_2(row)).useful
                ]
        protected = [
            *useful_by_category["Politica"][:10],
            *useful_by_category["CanCan"][:5],
        ]
        competitive = [
            *useful_by_category["Social"][:15],
            *useful_by_category["Diverse"][:15],
            *useful_by_category["Externe"][:10],
        ]
        _sort_candidate_rows(competitive)
        rows = protected[:effective_limit]
        rows.extend(competitive[: max(0, min(50, effective_limit) - len(rows))])
        if effective_limit > 50:
            selected_ids = {int(row["id"]) for row in rows}
            extension = [
                row
                for candidate_category in ("Social", "Diverse", "Externe")
                for row in useful_by_category[candidate_category]
                if int(row["id"]) not in selected_ids
            ]
            _sort_candidate_rows(extension)
            rows.extend(extension[: effective_limit - len(rows)])
        rows.sort(key=lambda row: CATEGORY_ORDER.index(_category(row["category"])))
        return tuple(_scout_candidate(row) for row in rows)

    def recommend_episode(self) -> EpisodeRecommendationV1:
        """Derive a transient advisory slate from the canonical complete pool."""

        candidates = self.list_candidates()
        if not candidates:
            return recommend_episode_v1(())
        placeholders = ",".join("?" for _ in candidates)
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                f"SELECT id, last_seen_at FROM events WHERE id IN ({placeholders})",
                tuple(item.event_id for item in candidates),
            ).fetchall()
        seen_at = {int(row[0]): datetime.fromisoformat(str(row[1])) for row in rows}
        return recommend_episode_v1(
            tuple(
                EditorialCandidateV1(
                    event_id=item.event_id,
                    title=item.title,
                    summary=item.summary,
                    category=item.category,
                    source_count=item.source_count,
                    last_seen_at=seen_at[item.event_id],
                )
                for item in candidates
            )
        )

    def recommend_episode_v1_1(
        self,
        *,
        continuity_context: tuple[ContinuityContextV1_1, ...] = (),
    ) -> EpisodeRecommendationV1_1:
        """Derive an explicit transient V1.1 slate for A/B review."""

        candidates = self.list_candidates()
        if not candidates:
            return recommend_episode_v1_1((), continuity_context=continuity_context)
        placeholders = ",".join("?" for _ in candidates)
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                f"SELECT id, last_seen_at FROM events WHERE id IN ({placeholders})",
                tuple(item.event_id for item in candidates),
            ).fetchall()
        seen_at = {int(row[0]): datetime.fromisoformat(str(row[1])) for row in rows}
        return recommend_episode_v1_1(
            tuple(
                EditorialCandidateV1_1(
                    event_id=item.event_id,
                    title=item.title,
                    summary=item.summary,
                    category=item.category,
                    source_count=item.source_count,
                    last_seen_at=seen_at[item.event_id],
                )
                for item in candidates
            ),
            continuity_context=continuity_context,
        )

    def recommend_episode_v1_2(
        self,
        *,
        discussion_bridges: tuple[DiscussionBridgeContextV1_2, ...] = (),
        continuity_context: tuple[MaterialContinuityContextV1_2, ...] = (),
    ) -> EpisodeRecommendationV1_2:
        """Derive an explicit transient V1.2 slate for deterministic A/B review."""

        candidates = self.list_useful_candidates_v1_2()
        if not candidates:
            return recommend_episode_v1_2(
                (),
                discussion_bridges=discussion_bridges,
                continuity_context=continuity_context,
            )
        placeholders = ",".join("?" for _ in candidates)
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                f"SELECT id, last_seen_at FROM events WHERE id IN ({placeholders})",
                tuple(item.event_id for item in candidates),
            ).fetchall()
        seen_at = {int(row[0]): datetime.fromisoformat(str(row[1])) for row in rows}
        return recommend_episode_v1_2(
            tuple(
                EditorialCandidateV1_2(
                    event_id=item.event_id,
                    title=item.title,
                    summary=item.summary,
                    category=item.category,
                    source_count=item.source_count,
                    last_seen_at=seen_at[item.event_id],
                )
                for item in candidates
            ),
            discussion_bridges=discussion_bridges,
            continuity_context=continuity_context,
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
            episode_draft_approval=(
                None if existing is None else existing.episode_draft_approval
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
            episode_draft_approval=(
                None if existing is None else existing.episode_draft_approval
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
            project.episode_draft_approval,
        )
        self._write(updated)
        # Observation-only and failure-isolated: evidence can never block a
        # successful Editor material or alter its generation path.
        try:
            EditorialEvidenceStoreV1(
                self.project_path.parent / "editorial-evidence-v1"
            ).capture_editor_output(
                path=output_path,
                expected_payload_sha256=payload_sha256,
                project_id=project.project_id,
                event_id=event_id,
            )
        except OSError, ValueError:
            pass
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
            project.episode_draft_approval,
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
            project.episode_draft_approval,
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
            project.episode_draft_approval,
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
            worklist_ids = tuple(item.event_id for item in project.editor_worklist)
            requested = revision.requested_event_ids
            if requested != tuple(
                event_id for event_id in worklist_ids if event_id in set(requested)
            ):
                raise ValueError
            statuses = {item.event_id: item.status for item in project.editor_worklist}
            if (
                any(event_id not in statuses for event_id in requested)
                or any(
                    statuses[event_id] is not EditorWorkItemStatusV1.COMPLETED
                    for event_id in revision.included_event_ids
                )
                or any(
                    statuses[event_id] is not EditorWorkItemStatusV1.FAILED
                    for event_id in revision.excluded_failed_event_ids
                )
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
            project.episode_draft_approval,
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

    def mark_episode_draft_pending_approval(
        self, *, expected_project: ActiveProjectV1
    ) -> ActiveProjectV1:
        """Atomically bind pending approval to the exact installed revision."""

        project = self._required()
        if type(expected_project) is not ActiveProjectV1 or project != expected_project:
            raise ValueError("Starea proiectului s-a schimbat")
        reference = project.current_episode_draft_revision
        revision = self.load_episode_draft_revision()
        if reference is None or revision is None or self._required() != project:
            raise ValueError("Revizie Episode Draft invalida")
        approval = EpisodeDraftApprovalV1(
            project_id=project.project_id,
            revision_id=revision.revision_id,
            artifact_sha256=reference.artifact_sha256,
        )
        existing_approval = project.episode_draft_approval
        if (
            existing_approval is not None
            and existing_approval.project_id == approval.project_id
            and existing_approval.revision_id == approval.revision_id
            and existing_approval.artifact_sha256 == approval.artifact_sha256
        ):
            return project
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
            project.editor_terminal_failures,
            approval,
        )
        return self._persist_episode_draft_approval(previous=project, updated=updated)

    def approve_episode_draft(
        self, *, expected_project: ActiveProjectV1
    ) -> ActiveProjectV1:
        """Atomically approve the exact current pending immutable revision."""

        project = self._required()
        if type(expected_project) is not ActiveProjectV1 or project != expected_project:
            raise EpisodeDraftApprovalTransitionError("project_changed")
        reference = project.current_episode_draft_revision
        revision = self.load_episode_draft_revision()
        approval = project.episode_draft_approval
        if reference is None or revision is None or self._required() != project:
            raise EpisodeDraftApprovalTransitionError("invalid_revision")
        if approval is None:
            raise EpisodeDraftApprovalTransitionError("approval_missing")
        if (
            approval.project_id != project.project_id
            or approval.revision_id != revision.revision_id
            or approval.artifact_sha256 != reference.artifact_sha256
        ):
            raise EpisodeDraftApprovalTransitionError("approval_mismatch")
        if approval.status is EpisodeDraftApprovalStatusV1.APPROVED:
            return project
        if approval.status is not EpisodeDraftApprovalStatusV1.PENDING_APPROVAL:
            raise EpisodeDraftApprovalTransitionError("not_pending")
        approved = EpisodeDraftApprovalV1(
            project_id=approval.project_id,
            revision_id=approval.revision_id,
            artifact_sha256=approval.artifact_sha256,
            status=EpisodeDraftApprovalStatusV1.APPROVED,
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
            project.editor_worklist,
            project.current_episode_draft_revision,
            project.editor_terminal_failures,
            approved,
        )
        return self._persist_episode_draft_approval(previous=project, updated=updated)

    def _persist_episode_draft_approval(
        self, *, previous: ActiveProjectV1, updated: ActiveProjectV1
    ) -> ActiveProjectV1:
        try:
            self._write(updated)
        except OSError as exc:
            raise EpisodeDraftApprovalPersistenceError("write_failed") from exc
        try:
            if self._required() != updated:
                raise ValueError
        except (OSError, TypeError, ValueError) as exc:
            try:
                self._write(previous)
                restored = self._required() == previous
            except OSError, TypeError, ValueError:
                restored = False
            code = "verification_failed" if restored else "rollback_failed"
            raise EpisodeDraftApprovalPersistenceError(code) from exc
        return updated

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
            project.episode_draft_approval,
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
            "episode_draft_approval": (
                None
                if project.episode_draft_approval is None
                else {
                    "project_id": project.episode_draft_approval.project_id,
                    "revision_id": project.episode_draft_approval.revision_id,
                    "artifact_sha256": project.episode_draft_approval.artifact_sha256,
                    "status": project.episode_draft_approval.status.value,
                }
            ),
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
        raw_approval = data.get("episode_draft_approval")
        approval = (
            None
            if raw_approval is None
            else EpisodeDraftApprovalV1(
                project_id=raw_approval["project_id"],
                revision_id=raw_approval["revision_id"],
                artifact_sha256=raw_approval["artifact_sha256"],
                status=EpisodeDraftApprovalStatusV1(raw_approval["status"]),
            )
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
            episode_draft_approval=approval,
        )
        if (
            not source.ranked_events
            or project.title != project.candidate.canonical_title
            or (
                project.episode_draft_approval is not None
                and project.episode_draft_approval.project_id != project.project_id
            )
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
    return normalize_category(value) or "Diverse"


def _scout_candidate(row: sqlite3.Row) -> ScoutCandidateV1:
    return ScoutCandidateV1(
        event_id=int(row["id"]),
        title=str(row["canonical_title"]),
        summary=str(row["summary"]),
        category=_category(row["category"]),
        source_count=int(row["source_count"]),
        article_count=int(row["article_count"]),
    )


def _editorial_candidate_v1_2(row: sqlite3.Row) -> EditorialCandidateV1_2:
    return EditorialCandidateV1_2(
        event_id=int(row["id"]),
        title=str(row["canonical_title"]),
        summary=str(row["summary"]),
        category=_category(row["category"]),
        source_count=int(row["source_count"]),
        last_seen_at=datetime.fromisoformat(str(row["last_seen_at"])),
    )


def _candidate_category(value: str | None) -> str | None:
    if value is None or value in {"all", "Toate"}:
        return None
    category = normalize_category(value)
    if category is None:
        raise ValueError("Categorie Scout invalida")
    return category


def _ranked_candidate_rows(
    connection: sqlite3.Connection, *, category: str, limit: int
) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """SELECT id, canonical_title, summary, category, source_count,
                      article_count, last_seen_at
               FROM events
               WHERE TRIM(canonical_title) <> ''
                 AND TRIM(COALESCE(summary, '')) <> ''
                 AND CASE category
                         WHEN 'Economie' THEN 'Diverse'
                         WHEN 'Conspiratii' THEN 'CanCan'
                         ELSE category
                     END = ?
               ORDER BY source_count DESC, last_seen_at DESC, id ASC
               LIMIT ?""",
            (category, limit),
        ).fetchall()
    )


def _sort_candidate_rows(rows: list[sqlite3.Row]) -> None:
    rows.sort(key=lambda row: int(row["id"]))
    rows.sort(key=lambda row: str(row["last_seen_at"]), reverse=True)
    rows.sort(key=lambda row: int(row["source_count"]), reverse=True)


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

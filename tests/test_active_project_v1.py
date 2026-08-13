from __future__ import annotations

import sqlite3
from pathlib import Path

from pastila_scout.active_project_v1 import (
    ActiveProjectStoreV1,
    ActiveProjectV1,
    ChiefEditorItemV1,
    EditorMaterialV1,
    move_chief_editor_item,
)
from pastila_scout.contracts.identity import verify_scout_input_identity
from pastila_scout.database import initialize_database
from pastila_scout.desktop_v1.entrypoint import _complete_handoff, _save_chief_editor
from pastila_scout.desktop_v1.models import _DesktopPageV1


def _database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        initialize_database(connection)
        connection.execute(
            """INSERT INTO sources
               (id, name, type, url, enabled, created_at, updated_at)
               VALUES ('source', 'Sursa', 'rss', 'https://example.test/feed', 1,
                       '2026-08-13T10:00:00+00:00', '2026-08-13T10:00:00+00:00')"""
        )
        connection.execute(
            """INSERT INTO events
               (id, canonical_title, normalized_title, summary, category,
                first_seen_at, last_seen_at, article_count, source_count,
                created_at, updated_at, first_published_at, last_published_at)
               VALUES (7, 'Titlu ales', 'titlu ales', 'Rezumatul materialului.',
                       'Social', '2026-08-13T10:00:00+00:00',
                       '2026-08-13T11:00:00+00:00', 1, 1,
                       '2026-08-13T10:00:00+00:00',
                       '2026-08-13T11:00:00+00:00',
                       '2026-08-13T09:00:00+00:00',
                       '2026-08-13T09:00:00+00:00')"""
        )
        connection.execute(
            """INSERT INTO articles
               (source_id, url, normalized_url, title, normalized_title, summary,
                published_at, discovered_at, event_id)
               VALUES ('source', 'https://example.test/story',
                       'https://example.test/story', 'Titlul sursei',
                       'titlul sursei', 'Rezumat', '2026-08-13T09:00:00+00:00',
                       '2026-08-13T10:00:00+00:00', 7)"""
        )


def test_handoff_preserves_candidate_and_is_deterministic_across_reload(tmp_path):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=project_path
    )

    assert [(item.event_id, item.title) for item in store.list_candidates()] == [
        (7, "Titlu ales")
    ]
    first = store.handoff(event_id=7)
    second = store.handoff(event_id=7)
    restored = ActiveProjectStoreV1(
        database_path=database, project_path=project_path
    ).load()

    assert restored is not None
    assert first.project_id == second.project_id == restored.project_id
    assert restored.title == "Titlu ales"
    assert restored.candidate.event_id == 7
    assert restored.candidate.canonical_summary == "Rezumatul materialului."
    assert restored.candidate.categories == ("Social",)
    assert restored.candidate.source_provenance[0].url == "https://example.test/story"
    verify_scout_input_identity(restored.scout_input)


def test_handoff_rejects_missing_candidate_without_replacing_project(tmp_path):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=project_path
    )
    original = store.handoff(event_id=7)

    try:
        store.handoff(event_id=999)
    except ValueError:
        pass
    else:
        raise AssertionError("missing event was accepted")

    assert store.load() == original


def test_desktop_handoff_persists_material_and_opens_editor(tmp_path):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=project_path
    )
    published = []
    pages = []

    class View:
        def publish_active_project(self, *, title, message):
            published.append((title, message))

    class Controller:
        def select_page(self, *, page):
            pages.append(page)

    cells = {}
    assert _complete_handoff(
        store=store,
        event_id=7,
        cells=cells,
        view=View(),
        controller=Controller(),
    )
    assert cells["project"].candidate.canonical_title == "Titlu ales"
    assert published[0][0] == "Titlu ales"
    assert pages == [_DesktopPageV1.EDITOR]
    assert ActiveProjectStoreV1(
        database_path=database, project_path=project_path
    ).load().candidate.event_id == 7


def test_chief_editor_order_notes_persist_and_export(tmp_path):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    store = ActiveProjectStoreV1(database_path=database, project_path=project_path)
    base = store.handoff(event_id=7)
    materials = (
        EditorMaterialV1("material:a", 7, "Prima È™tire", "Primul rezumat"),
        EditorMaterialV1("material:b", 8, "A doua È™tire", "Al doilea rezumat"),
    )
    store._write(
        ActiveProjectV1(
            base.project_id,
            base.title,
            base.handed_off_at,
            base.scout_input,
            materials,
        )
    )
    ordered = move_chief_editor_item(
        (
            ChiefEditorItemV1("material:a", "Intro", "Deschidere"),
            ChiefEditorItemV1("material:b", "Social", "TranziÈ›ie"),
        ),
        1,
        -1,
    )
    saved = store.save_chief_editor(title="Episodul zilei", items=ordered)
    restored = ActiveProjectStoreV1(
        database_path=database, project_path=project_path
    ).load()
    assert restored is not None
    assert restored.chief_editor_items == saved.chief_editor_items == ordered
    assert restored.chief_editor_title == "Episodul zilei"
    output = tmp_path / "episod.md"
    text = store.export_chief_editor(destination=output)
    assert text.index("A doua È™tire") < text.index("Prima È™tire")
    assert "[Social]" in text and "TranziÈ›ie" in text
    assert output.read_text(encoding="utf-8") == text


def test_chief_editor_removal_preserves_material_and_duplicates_are_rejected(tmp_path):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    store = ActiveProjectStoreV1(database_path=database, project_path=project_path)
    store.handoff(event_id=7)
    project = store.record_editor_output(
        output_path=tmp_path / "editor.json", payload_sha256="sha256:" + "a" * 64
    )
    reference = project.editor_materials[0].reference
    store.save_chief_editor(title="Episod", items=())
    assert store.load().editor_materials[0].reference == reference
    duplicate = ChiefEditorItemV1(reference)
    try:
        store.save_chief_editor(title="Episod", items=(duplicate, duplicate))
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate Editor-Chief material was accepted")
    assert move_chief_editor_item((duplicate,), 0, -1) == (duplicate,)


def test_desktop_chief_editor_payload_saves_reordered_structure_for_reload(tmp_path):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    store = ActiveProjectStoreV1(database_path=database, project_path=project_path)
    base = store.handoff(event_id=7)
    materials = (
        EditorMaterialV1("material:a", 7, "Prima", "Rezumat A"),
        EditorMaterialV1("material:b", 8, "A doua", "Rezumat B"),
    )
    store._write(
        ActiveProjectV1(
            base.project_id,
            base.title,
            base.handed_off_at,
            base.scout_input,
            materials,
        )
    )
    _save_chief_editor(
        store,
        {
            "title": "Plan final",
            "items": (
                ("material:b", "Final", "ÃŽnchidere"),
                ("material:a", "Intro", "Deschidere"),
            ),
        },
    )
    restored = store.load()
    assert restored.chief_editor_title == "Plan final"
    assert tuple(item.material_reference for item in restored.chief_editor_items) == (
        "material:b",
        "material:a",
    )


def test_new_scout_handoff_keeps_active_project_and_developed_materials(tmp_path):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    store = ActiveProjectStoreV1(database_path=database, project_path=project_path)
    first = store.handoff(event_id=7)
    developed = store.record_editor_output(
        output_path=tmp_path / "first.json", payload_sha256="sha256:" + "b" * 64
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            """INSERT INTO events
               (id, canonical_title, normalized_title, summary, category,
                first_seen_at, last_seen_at, article_count, source_count,
                created_at, updated_at)
               VALUES (8, 'Alt material', 'alt material', 'Alt rezumat', 'Externe',
                       '2026-08-13T10:00:00+00:00', '2026-08-13T12:00:00+00:00',
                       1, 1, '2026-08-13T10:00:00+00:00',
                       '2026-08-13T12:00:00+00:00')"""
        )
        connection.execute(
            """INSERT INTO articles
               (source_id, url, normalized_url, title, normalized_title,
                discovered_at, event_id)
               VALUES ('source', 'https://example.test/other',
                       'https://example.test/other', 'AltÄƒ sursÄƒ', 'alta sursa',
                       '2026-08-13T12:00:00+00:00', 8)"""
        )
    second = store.handoff(event_id=8)
    assert second.project_id == first.project_id
    assert second.candidate.event_id == 8
    assert second.editor_materials == developed.editor_materials
    assert second.chief_editor_items == developed.chief_editor_items

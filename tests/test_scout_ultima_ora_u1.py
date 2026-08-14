import sqlite3
from pathlib import Path

import pytest
from test_desktop_application_v1 import scout_result

from pastila_scout.active_project_v1 import ActiveProjectStoreV1
from pastila_scout.database import initialize_database
from pastila_scout.desktop_application_v1 import (
    DesktopApplicationConfigurationError,
    ScoutDesktopCategoryV1,
)
from pastila_scout.desktop_v1 import entrypoint
from pastila_scout.desktop_v1.errors import _DesktopShellConfigurationError
from pastila_scout.desktop_v1.models import _DesktopScoutActionInputV1


@pytest.mark.parametrize("query", ("", "   ", "\t\r\n"))
def test_empty_query_selects_normal_mode(query):
    request = entrypoint._scout_request(
        _DesktopScoutActionInputV1("7", "Politica", query)
    )

    assert request.period_days == 7
    assert request.category is ScoutDesktopCategoryV1.POLITICA
    assert request.targeted_query is None


def test_nonempty_query_is_trimmed_once_at_request_boundary():
    request = entrypoint._scout_request(
        _DesktopScoutActionInputV1("3", "all", "  Donald Trump Iran  ")
    )

    assert request.period_days == 3
    assert request.category is ScoutDesktopCategoryV1.ALL
    assert request.targeted_query == "Donald Trump Iran"


def test_two_days_is_not_accepted_as_a_visible_normal_period():
    with pytest.raises(_DesktopShellConfigurationError):
        entrypoint._scout_request(_DesktopScoutActionInputV1("2", "all", ""))


class _View:
    def __init__(self):
        self.candidates = None

    def publish_candidates(self, *, candidates):
        self.candidates = candidates

    def publish_scout_result(self, **kwargs):
        self.result = kwargs


class _IsolationStore:
    def __init__(self):
        self.global_calls = 0
        self.scoped_calls = []

    def list_candidates(self, *, category=None):
        del category
        self.global_calls += 1
        raise AssertionError("targeted completion used global restoration")

    def list_candidates_by_ids(self, *, event_ids):
        self.scoped_calls.append(event_ids)
        return ()


def test_targeted_empty_projection_never_uses_global_restoration():
    view = _View()
    store = _IsolationStore()

    entrypoint._publish_scoped_candidates(view, store, ())

    assert store.global_calls == 0
    assert store.scoped_calls == [()]
    assert view.candidates == ()


def test_targeted_completion_with_restored_candidates_uses_only_empty_scope():
    view = _View()
    store = _IsolationStore()
    result = scout_result(targeted_candidate_ids=())

    entrypoint._publish_scout_completion(view, store, result)

    assert store.global_calls == 0
    assert store.scoped_calls == [()]
    assert view.candidates == ()


def test_malformed_completion_fails_closed_before_any_candidate_projection():
    view = _View()
    store = _IsolationStore()
    result = scout_result(targeted_candidate_ids=())
    object.__setattr__(result, "targeted_candidate_ids", None)

    with pytest.raises(DesktopApplicationConfigurationError):
        entrypoint._publish_scout_completion(view, store, result)

    assert store.global_calls == 0
    assert store.scoped_calls == []
    assert view.candidates is None


def test_normal_projection_keeps_global_restoration_path():
    view = _View()

    class Store:
        def list_candidates(self, *, category=None):
            assert category is None
            return ()

    entrypoint._publish_candidates(view, Store())

    assert view.candidates == ()


def test_restored_projection_uses_the_persisted_category():
    view = _View()

    class Store:
        def __init__(self):
            self.categories = []

        def list_candidates(self, *, category=None):
            self.categories.append(category)
            return ()

    store = Store()

    entrypoint._publish_candidates(view, store, "Externe")

    assert store.categories == ["Externe"]
    assert view.candidates == ()


def test_normal_completion_projects_only_the_executed_category():
    view = _View()

    class Store:
        def __init__(self):
            self.categories = []

        def list_candidates(self, *, category=None):
            self.categories.append(category)
            return ()

    store = Store()
    result = scout_result(
        targeted_candidate_ids=None,
        executed_category=ScoutDesktopCategoryV1.SOCIAL,
    )

    entrypoint._publish_scout_completion(view, store, result)

    assert store.categories == ["Social"]
    assert view.candidates == ()


def test_scoped_candidate_projection_preserves_requested_event_order(tmp_path):
    database = tmp_path / "missing.db"
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "active.json"
    )

    assert store.list_candidates_by_ids(event_ids=()) == ()
    assert not database.exists()
    with pytest.raises(ValueError):
        store.list_candidates_by_ids(event_ids=(1, 1))
    for invalid in ((0,), (-1,), (True,)):
        with pytest.raises(ValueError):
            store.list_candidates_by_ids(event_ids=invalid)


def test_scoped_candidate_projection_keeps_normal_event_identity(tmp_path):
    database = tmp_path / "scout.db"
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        initialize_database(connection)
        for event_id, title in ((41, "First event"), (42, "Second event")):
            connection.execute(
                """INSERT INTO events
                   (id, canonical_title, normalized_title, summary, category,
                    first_seen_at, last_seen_at, article_count, source_count,
                    created_at, updated_at)
                   VALUES (?, ?, ?, 'Summary', 'Externe', 'x', 'x', 1, 1, 'x', 'x')""",
                (event_id, title, title.casefold()),
            )
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "active.json"
    )
    view = _View()

    entrypoint._publish_scoped_candidates(view, store, (42, 41))

    assert tuple(row[0] for row in view.candidates) == (42, 41)
    assert tuple(row[1] for row in view.candidates) == ("Second event", "First event")

    entrypoint._publish_scoped_candidates(view, store, (999, 42))
    assert tuple(row[0] for row in view.candidates) == (42,)


def test_targeted_query_is_transient_and_not_part_of_windows_settings():
    settings_source = Path("src/pastila_scout/windows_state_v1/settings.py").read_text(
        encoding="utf-8"
    )

    assert "targeted_query" not in settings_source

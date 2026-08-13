from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

from pastila_scout.active_project_v1 import ActiveProjectStoreV1
from pastila_scout.database import initialize_database
from pastila_scout.desktop_v1 import source_settings
from pastila_scout.desktop_v1.views import (
    _BUTTON_STYLE,
    _PRIMARY_LABEL_STYLE,
)


def _events(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        initialize_database(connection)
        connection.execute(
            "INSERT INTO sources (id,name,type,url,enabled,created_at,updated_at) VALUES ('s','S','rss','https://x.test/feed',1,'x','x')"
        )
        for event_id in (1, 2, 3):
            connection.execute(
                "INSERT INTO events (id,canonical_title,normalized_title,summary,category,first_seen_at,last_seen_at,article_count,source_count,created_at,updated_at) VALUES (?,?,?,?,?,'x','x',1,1,'x','x')",
                (
                    event_id,
                    f"Titlu {event_id}",
                    f"titlu {event_id}",
                    "Rezumat",
                    "Diverse",
                ),
            )
            connection.execute(
                "INSERT INTO articles (source_id,url,normalized_url,title,normalized_title,discovered_at,event_id) VALUES ('s',?,?,?,?, 'x',?)",
                (
                    f"https://x.test/{event_id}",
                    f"https://x.test/{event_id}",
                    f"Titlu {event_id}",
                    f"titlu {event_id}",
                    event_id,
                ),
            )


def test_bulk_handoff_is_stable_persistent_and_suppresses_duplicates(tmp_path):
    database = tmp_path / "news.db"
    _events(database)
    store = ActiveProjectStoreV1(
        database_path=database, project_path=tmp_path / "project.json"
    )
    project, skipped = store.handoff_many(event_ids=(2, 1, 2))
    assert skipped == 1
    assert tuple(item.event_id for item in project.scout_input.ranked_events) == (2, 1)
    restored, skipped = store.handoff_many(event_ids=(1, 999, 3))
    assert skipped == 2
    assert tuple(item.event_id for item in restored.scout_input.ranked_events) == (
        2,
        1,
        3,
    )
    assert (
        ActiveProjectStoreV1(
            database_path=database, project_path=tmp_path / "project.json"
        ).load()
        == restored
    )


def test_source_add_validates_persists_and_survives_reload(tmp_path, monkeypatch):
    base = tmp_path / "sources.yaml"
    override = tmp_path / "profile" / "sources.override.yaml"
    base.write_text("sources: []\n", encoding="utf-8")

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def fetch(self, url):
            return b"feed"

    monkeypatch.setattr(source_settings, "HTTPClient", Client)
    monkeypatch.setattr(
        source_settings, "parse_feed", lambda source_id, body: [object()]
    )
    assert (
        source_settings._add_scout_source_v1(
            url=" https://news.test/rss ", current_path=base, override_path=override
        )
        == "saved"
    )
    saved = yaml.safe_load(override.read_text(encoding="utf-8"))["sources"]
    assert saved[0]["url"] == "https://news.test/rss" and saved[0]["enabled"] is True
    assert (
        source_settings._add_scout_source_v1(
            url="https://news.test/rss", current_path=override, override_path=override
        )
        == "duplicate"
    )
    assert (
        source_settings._add_scout_source_v1(
            url="ftp://news.test/rss", current_path=override, override_path=override
        )
        == "invalid"
    )
    monkeypatch.setattr(source_settings, "parse_feed", lambda source_id, body: [])
    assert (
        source_settings._add_scout_source_v1(
            url="https://bad.test/", current_path=override, override_path=override
        )
        == "unsupported"
    )


def test_source_override_rebase_keeps_user_additions_without_old_canonical_entries(
    tmp_path,
):
    canonical = tmp_path / "canonical.yaml"
    override = tmp_path / "profile" / "sources.override.yaml"
    canonical.write_text(
        """sources:
  - id: guardian_world
    name: Guardian World
    type: rss
    url: https://www.theguardian.com/world/rss
    enabled: true
    categories: [Externe]
""",
        encoding="utf-8",
    )
    override.parent.mkdir()
    override.write_text(
        """sources:
  - id: ziare
    name: Ziare
    type: rss
    url: https://ziare.com/rss/breaking_news.xml
    enabled: true
    categories: [Diverse]
  - id: user_feed
    name: User Feed
    type: rss
    url: https://user.test/feed
    enabled: true
    categories: [Diverse]
""",
        encoding="utf-8",
    )

    selected = source_settings._rebase_scout_sources_override_v1(
        canonical_path=canonical,
        override_path=override,
    )

    assert selected == override
    saved = yaml.safe_load(override.read_text(encoding="utf-8"))["sources"]
    assert [item["id"] for item in saved] == ["guardian_world", "user_feed"]
    assert len({item["url"] for item in saved}) == 2


def test_source_override_rebase_does_not_duplicate_new_canonical_source(tmp_path):
    canonical = tmp_path / "canonical.yaml"
    override = tmp_path / "sources.override.yaml"
    source = """  - id: context
    name: Context
    type: rss
    url: https://context.ro/feed
    enabled: true
    categories: [Diverse]
"""
    canonical.write_text(f"sources:\n{source}", encoding="utf-8")
    override.write_text(f"sources:\n{source}", encoding="utf-8")

    source_settings._rebase_scout_sources_override_v1(
        canonical_path=canonical,
        override_path=override,
    )

    saved = yaml.safe_load(override.read_text(encoding="utf-8"))["sources"]
    assert [item["id"] for item in saved] == ["context"]


def test_small_shared_styles_are_named_for_buttons_and_primary_labels():
    assert _BUTTON_STYLE == "TButton"
    assert _PRIMARY_LABEL_STYLE == "PastilaPrimary.TLabel"

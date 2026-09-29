from __future__ import annotations

import gzip
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_scout_production_v1 import (
    CapturedArticle,
    CaptureError,
    FeedParseError,
    FetchResponse,
    SourceDefinition,
    build_source_packet,
    capture_sources,
    group_articles,
    load_sources,
    parse_feed,
    persist_capture_and_grouping,
    same_event,
)
from pastila_scout.vnext_state_sqlite_v1 import SQLiteStateStore

FIXTURES = Path("docs/artifacts/vnext-scout-production-closure-v1-fixtures.json")
SOURCES = Path("docs/artifacts/editor-vnext-minimal-scout-sources-v1.json")


def fixture() -> dict:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def source(raw: dict) -> SourceDefinition:
    return SourceDefinition(raw["source_id"], raw["name"], raw["url"], tuple(raw["categories"]), raw["maximum_articles"])


def response(payload: str, *, gzip_encoded: bool = False) -> FetchResponse:
    value = payload.encode("utf-8")
    return FetchResponse(gzip.compress(value) if gzip_encoded else value, "https://fixture.invalid/feed", "text/xml", "gzip" if gzip_encoded else None)


def article(source_id: str, title: str, identity: str) -> CapturedArticle:
    return CapturedArticle(identity, source_id, source_id, f"https://{source_id}.invalid/feed", f"https://{source_id}.invalid/{identity}", title, title, "2026-09-28T08:00:00Z", "2026-09-28T12:00:00Z", ("News",), identity)


def store(tmp_path: Path) -> SQLiteStateStore:
    value = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="scout-writer", busy_timeout_ms=100)
    value.bootstrap()
    value.create_workflow("workflow-1")
    return value


def test_published_source_set_is_identity_bound_and_complete():
    raw = json.loads(SOURCES.read_text(encoding="utf-8"))
    sources = load_sources(raw)
    assert len(sources) == 54
    assert len({item.source_id for item in sources}) == 54
    mutated = dict(raw); mutated["sources_identity"] = "0" * 64
    with pytest.raises(Exception, match="identity mismatch"):
        load_sources(mutated)


def test_rss_atom_and_bounded_gzip_capture():
    value = fixture()
    definitions = {item.source_id: item for item in map(source, value["sources"])}
    rss = parse_feed(definitions["fixture_public"], response(value["feeds"]["fixture_public"], gzip_encoded=True), value["captured_at"])
    atom = parse_feed(definitions["fixture_ministry"], response(value["feeds"]["fixture_ministry"]), value["captured_at"])
    assert len(rss) == len(atom) == 1
    assert "utm_source" not in rss[0].article_url
    assert rss[0].source_text.startswith("Consiliul local")
    assert rss[0].feed_identity != atom[0].feed_identity


def test_xml_entities_payload_limits_and_non_https_fail_closed():
    definition = source(fixture()["sources"][0])
    with pytest.raises(FeedParseError, match="DTD"):
        parse_feed(definition, response("<!DOCTYPE x [<!ENTITY y 'z'>]><rss/>"), fixture()["captured_at"])
    with pytest.raises(CaptureError, match="byte limit"):
        parse_feed(definition, FetchResponse(b"x" * 2_000_001, definition.url, "text/xml"), fixture()["captured_at"])


def test_source_failures_are_isolated_and_do_not_discard_successes():
    value = fixture(); definitions = tuple(map(source, value["sources"][:2]))

    def transport(item: SourceDefinition, _timeout: float) -> FetchResponse:
        if item.source_id == "fixture_ministry":
            raise OSError("temporary source outage")
        return response(value["feeds"][item.source_id])

    articles, failures = capture_sources(definitions, transport=transport, captured_at=value["captured_at"])
    assert len(articles) == 1 and len(failures) == 1
    assert failures[0].source_identity == "fixture_ministry"
    with pytest.raises(CaptureError, match="maximum_workers"):
        capture_sources(definitions, transport=transport, captured_at=value["captured_at"], maximum_workers=17)


@pytest.mark.parametrize("case", fixture()["grouping_cases"])
def test_grouping_cases(case: dict):
    left = article("left", case["left"], "left")
    right = article("right", case["right"], "right")
    assert same_event(left, right) is case["expected"]


def test_complete_link_prevents_chain_merge():
    first = article("a", "Guvernul aprobă programul pentru școli București", "a")
    bridge = article("b", "Guvernul aprobă programul pentru școli naționale", "b")
    third = article("c", "Ministerul lansează programul pentru școli naționale", "c")
    groups = group_articles((first, bridge, third))
    assert max(len(item.captures) for item in groups) == 2


def test_capture_group_selection_and_sourcepacket_use_published_state_boundary(tmp_path: Path):
    value = fixture(); definitions = tuple(map(source, value["sources"]))
    feeds = value["feeds"]
    articles, failures = capture_sources(definitions, transport=lambda item, _: response(feeds[item.source_id], gzip_encoded=item.source_id == "fixture_ministry"), captured_at=value["captured_at"])
    state = store(tmp_path)
    groups = persist_capture_and_grouping(
        state,
        workflow_identity="workflow-1",
        sources_identity="sources:test",
        articles=articles,
        failures=failures,
        observed_at=value["captured_at"],
    )
    selected = next(item for item in groups if len(item.captures) == 2)
    packet = build_source_packet(
        state,
        workflow_identity="workflow-1",
        event_identity=selected.event_identity,
        selection_actor="Daniel",
        selection_authorization_identity="a" * 64,
        observed_at=value["captured_at"],
    )
    assert packet["source_count"] == 2
    assert packet["selection_authority"] == "EXPLICIT_USER_EVENT_ID"
    assert packet["selection_receipt"]["actor"] == "Daniel"
    assert packet["selection_receipt"]["authorization_identity"] == "a" * 64
    assert object_identity({key: item for key, item in packet.items() if key != "packet_identity"}) == packet["packet_identity"]
    assert state.load_workflow("workflow-1")["state"] == "SOURCE_PACKET_READY"
    assert state.reconstruct_workflow("workflow-1")["state"] == "SOURCE_PACKET_READY"
    assert len(list((tmp_path / "blobs/capture-batches").glob("*.json"))) == 1
    with state.read() as connection:
        assert connection.execute("SELECT COUNT(*) FROM captures").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM source_packets").fetchone()[0] == 1


def test_all_source_failure_is_terminal_without_partial_eligible_state(tmp_path: Path):
    state = store(tmp_path)
    groups = persist_capture_and_grouping(
        state,
        workflow_identity="workflow-1",
        sources_identity="sources:test",
        articles=(),
        failures=(),
        observed_at=fixture()["captured_at"],
    )
    assert groups == ()
    assert state.load_workflow("workflow-1")["state"] == "CAPTURE_FAILED"
    manifests = list((tmp_path / "blobs/capture-batches").glob("*.json"))
    assert len(manifests) == 1
    with state.read() as connection:
        assert connection.execute("SELECT COUNT(*) FROM captures").fetchone()[0] == 0


def test_grouping_and_packet_identities_are_deterministic(tmp_path: Path):
    value = fixture(); definitions = tuple(map(source, value["sources"][:2]))
    articles, _ = capture_sources(definitions, transport=lambda item, _: response(value["feeds"][item.source_id]), captured_at=value["captured_at"])
    forward = group_articles(articles)
    reverse = group_articles(tuple(reversed(articles)))
    assert [item.event_identity for item in forward] == [item.event_identity for item in reverse]


def test_duplicate_capture_replay_is_idempotent(tmp_path: Path):
    value = fixture(); definition = source(value["sources"][0])
    articles = parse_feed(definition, response(value["feeds"][definition.source_id]), value["captured_at"])
    state = store(tmp_path)
    first = persist_capture_and_grouping(state, workflow_identity="workflow-1", sources_identity="sources:test", articles=articles, failures=(), observed_at=value["captured_at"])
    second = persist_capture_and_grouping(state, workflow_identity="workflow-1", sources_identity="sources:test", articles=articles, failures=(), observed_at=value["captured_at"])
    assert first == second
    with state.read() as connection:
        assert connection.execute("SELECT COUNT(*) FROM captures").fetchone()[0] == 1


def test_capture_identity_changes_when_source_text_changes():
    value = fixture(); definition = source(value["sources"][0])
    original = parse_feed(definition, response(value["feeds"][definition.source_id]), value["captured_at"])[0]
    changed = replace(original, source_text=original.source_text + " Detaliu nou.")
    assert original.capture_identity != object_identity({key: item for key, item in asdict(changed).items() if key != "capture_identity"})

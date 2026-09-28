from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path

import pytest

from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_scout_production_v1 import (
    FetchResponse,
    SourceDefinition,
    build_source_packet,
    capture_sources,
    persist_capture_and_grouping,
)
from pastila_scout.vnext_sourcepacket_binding_v1 import (
    SourcePacketBindingError,
    bind_source_packet,
    validate_bound_source_packet,
)
from pastila_scout.vnext_state_sqlite_v1 import SQLiteStateStore

FIXTURE = Path("docs/artifacts/vnext-sourcepacket-production-binding-v1-fixture.json")
SCOUT_FIXTURE = Path("docs/artifacts/vnext-scout-production-closure-v1-fixtures.json")
CONTRACT = Path("docs/artifacts/editor-vnext-minimal-scout-sourcepacket-contract-v1.json")
CLOSURE = Path("docs/artifacts/vnext-sourcepacket-production-binding-closure-v1.json")


def fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_binds_byte_exact_and_deterministically():
    value = fixture()
    first = bind_source_packet(value["source_packet"])
    second = bind_source_packet(copy.deepcopy(value["source_packet"]))
    assert first == second == value["expected_bound_packet"]
    assert first["packet_identity"] == "facb4d1dc230c10d6c744befbd37e7d0ab559f24c13c5f11a118e956a7c994e2"
    assert [item["text"].encode() for item in first["spans"]] == [item["text"].encode() for item in value["source_packet"]["spans"]]


def test_binding_targets_frozen_contract_without_modifying_it():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    packet = bind_source_packet(fixture()["source_packet"])
    assert object_identity({key: item for key, item in contract.items() if key != "contract_identity"}) == contract["contract_identity"]
    assert packet["schema"] == contract["source_packet"]["schema"]
    assert packet["schema_version"] == contract["source_packet"]["schema_version"]
    assert packet["selection_authority"] == contract["handoff"]["selection_authority"]
    assert packet["completeness"] == contract["handoff"]["source_packet_completeness"]


def test_provenance_is_preserved_by_explicit_field_mapping():
    source = fixture()["source_packet"]
    bound = bind_source_packet(source)
    for before, after in zip(source["spans"], bound["spans"], strict=True):
        assert after["source_id"] == before["source_identity"]
        assert after["capture_sha256"] == before["capture_identity"]
        assert after["sha256"] == before["text_sha256"]
        for key in ("source_name", "source_feed_url", "article_url", "title", "published_at", "captured_at", "byte_start", "byte_end", "text", "content_scope"):
            assert after[key] == before[key]


@pytest.mark.parametrize("mutation", ["identity", "text", "bytes", "duplicate", "scope", "selection", "completeness"])
def test_source_tampering_fails_closed(mutation: str):
    packet = copy.deepcopy(fixture()["source_packet"])
    if mutation == "identity": packet["packet_identity"] = "0" * 64
    elif mutation == "text": packet["spans"][0]["text"] += " inventat"
    elif mutation == "bytes": packet["spans"][0]["byte_end"] += 1
    elif mutation == "duplicate": packet["spans"][1]["source_identity"] = packet["spans"][0]["source_identity"]
    elif mutation == "scope": packet["spans"][0]["content_scope"] = "FULL_ARTICLE_UNPROVEN"
    elif mutation == "selection": packet["selection_authority"] = "AUTOMATIC"
    elif mutation == "completeness": packet["completeness"] = "PARTIAL"
    with pytest.raises(SourcePacketBindingError):
        bind_source_packet(packet)


def test_bound_packet_tampering_fails_closed():
    packet = bind_source_packet(fixture()["source_packet"])
    packet["spans"][0]["text"] += " alterat"
    with pytest.raises(SourcePacketBindingError):
        validate_bound_source_packet(packet)


def test_real_scout_production_fixture_reaches_frozen_packet(tmp_path: Path):
    value = json.loads(SCOUT_FIXTURE.read_text(encoding="utf-8"))
    definitions = tuple(SourceDefinition(item["source_id"], item["name"], item["url"], tuple(item["categories"]), item["maximum_articles"]) for item in value["sources"])

    def transport(item: SourceDefinition, _: float) -> FetchResponse:
        payload = value["feeds"][item.source_id].encode()
        encoded = gzip.compress(payload) if item.source_id == "fixture_ministry" else payload
        return FetchResponse(encoded, item.url, "application/xml", "gzip" if item.source_id == "fixture_ministry" else None)

    articles, failures = capture_sources(definitions, transport=transport, captured_at=value["captured_at"])
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="sourcepacket-binding-test", busy_timeout_ms=100)
    store.bootstrap(); store.create_workflow("workflow-binding")
    groups = persist_capture_and_grouping(store, workflow_identity="workflow-binding", sources_identity="sources:fixture", articles=articles, failures=failures, observed_at=value["captured_at"])
    selected = next(group for group in groups if len(group.captures) == 2)
    source = build_source_packet(store, workflow_identity="workflow-binding", event_identity=selected.event_identity, observed_at=value["captured_at"])
    bound = bind_source_packet(source)
    validate_bound_source_packet(bound)
    assert bound["source_count"] == 2
    assert {item["source_id"] for item in bound["spans"]} == {item.source_identity for item in selected.captures}
    assert store.load_workflow("workflow-binding")["state"] == "SOURCE_PACKET_READY"


def test_closure_forbids_migration_integration_and_legacy():
    closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
    assert closure["status"] == "ISOLATED_NOT_ACTIVE"
    assert closure["historical_database_migrated"] is False
    assert closure["product_data_migration"] is False
    assert closure["active_integration"] is False
    assert closure["product_root_dependency"] is False
    assert closure["legacy_dependency_count"] == 0
    assert closure["stop_all_candidates"] is True
    assert closure["voice"] == "DISABLED_UNTIL_PROMOTION"


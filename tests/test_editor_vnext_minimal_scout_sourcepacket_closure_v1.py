import importlib.util
import json
import sys
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("scout", "src/pastila_scout/vnext_scout_v1.py")
S = importlib.util.module_from_spec(SPEC); assert SPEC.loader; sys.modules[SPEC.name] = S; SPEC.loader.exec_module(S)


def fixture():
    return json.loads(Path("docs/artifacts/editor-vnext-minimal-scout-acceptance-fixture-v1.json").read_text(encoding="utf-8"))


def test_rss_atom_capture_grouping_and_unrelated_separation():
    value = fixture()
    with S.open_database(Path(":memory:")) as connection:
        for item in value["feeds"]:
            S.capture(connection, item["source"], item["xml"].encode(), value["captured_at"])
        events = S.event_rows(connection)
    assert sorted(item["source_count"] for item in events) == [1, 2]


def test_explicit_handoff_is_self_contained_and_bound():
    value = fixture()
    with S.open_database(Path(":memory:")) as connection:
        for item in value["feeds"]:
            S.capture(connection, item["source"], item["xml"].encode(), value["captured_at"])
        event = next(item for item in S.event_rows(connection) if item["source_count"] == 2)
        packet = S.build_source_packet(connection, event["event_id"])
    assert packet["completeness"] == "ALL_CAPTURED_UNIQUE_SOURCES"
    assert packet["source_count"] == 2
    assert S.identity(packet, "packet_identity") == packet["packet_identity"]
    assert all(span["article_url"] and span["capture_sha256"] for span in packet["spans"])
    assert all(span["sha256"] == S.hashlib.sha256(span["text"].encode()).hexdigest() for span in packet["spans"])


def test_grouping_fails_closed_on_conflicting_numbers():
    assert S.same_event("Primăria aprobă 19 milioane pentru pod", "Primăria aprobă 127 milioane pentru pod") is False


def test_config_is_rss_only_and_identity_bound():
    value = json.loads(Path("docs/artifacts/editor-vnext-minimal-scout-sources-v1.json").read_text(encoding="utf-8"))
    assert len(value["sources"]) == 54
    assert {item["adapter"] for item in value["sources"]} == {"rss"}
    assert S.identity(value, "sources_identity") == value["sources_identity"]


def test_contract_excludes_legacy_authority_layers():
    value = json.loads(Path("docs/artifacts/editor-vnext-minimal-scout-sourcepacket-contract-v1.json").read_text(encoding="utf-8"))
    forbidden = set(value["source_packet"]["forbidden_dependencies"])
    assert {"EVENT_AUTHORITY_BUNDLE", "EVIDENCE_PACKET", "BOUNDED_SELECTOR", "FACTUAL_LEDGER"} <= forbidden
    assert S.identity(value, "contract_identity") == value["contract_identity"]


def test_runtime_uses_relative_product_dependencies_for_clean_restore():
    source = Path("src/pastila_scout/vnext_scout_v1.py").read_text(encoding="utf-8")
    assert 'product_root = runtime_root.parents[1]' in source
    assert 'runtime_root != (product_root / lock["runtime_path"]).resolve()' in source

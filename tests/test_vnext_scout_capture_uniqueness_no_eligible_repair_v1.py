from __future__ import annotations

import json
import runpy
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from pastila_scout.vnext_product_orchestrator_v1 import (
    ProductOrchestrator,
    ProductOrchestratorError,
    bootstrap_store,
)
from pastila_scout.vnext_scout_production_v1 import (
    CaptureFailure,
    FetchResponse,
    SourceConfigError,
    SourceDefinition,
    _reconcile_source_dispositions,
    capture_sources,
    parse_feed,
    persist_capture_and_grouping,
    source_set_from_definitions,
)

_HELPERS = runpy.run_path(
    str(Path(__file__).with_name("test_vnext_product_orchestrator_integrated_core_e2e_v1.py"))
)
_persisted_factual_bundle = _HELPERS["_persisted_factual_bundle"]
SOURCES = _HELPERS["SOURCES"]
transport = _HELPERS["transport"]


def _articles():
    articles, failures = capture_sources(
        SOURCES.definitions,
        transport=transport,
        captured_at="2026-09-29T01:00:00Z",
        maximum_workers=2,
    )
    assert not failures
    return articles


def _batch(store):
    paths = list((store.root / "blobs/capture-batches").glob("*.json"))
    assert len(paths) == 1
    return json.loads(paths[0].read_text(encoding="utf-8"))


def test_valid_empty_feed_is_not_capture_failure():
    source = SourceDefinition("empty", "Empty", "https://empty.example/feed", ("news",), 5)
    response = FetchResponse(
        b"<rss><channel></channel></rss>",
        source.url,
        "application/rss+xml",
    )
    assert parse_feed(source, response, "2026-09-29T01:00:00Z") == ()

    articles, failures = capture_sources(
        (source,),
        transport=lambda definition, timeout: response,
        captured_at="2026-09-29T01:00:00Z",
    )
    assert articles == ()
    assert failures == ()


@pytest.mark.parametrize(
    "payload",
    (b"<rss>", b"<!DOCTYPE rss><rss/>", b"not xml"),
)
def test_invalid_feed_remains_explicit_capture_failure(payload: bytes):
    source = SourceDefinition("broken", "Broken", "https://broken.example/feed", ("news",), 5)
    articles, failures = capture_sources(
        (source,),
        transport=lambda definition, timeout: FetchResponse(
            payload, definition.url, "application/rss+xml"
        ),
        captured_at="2026-09-29T01:00:00Z",
    )
    assert articles == ()
    assert len(failures) == 1
    assert failures[0].source_identity == "broken"
    assert failures[0].failure_class == "FeedParseError"


def test_duplicate_capture_identity_fails_before_any_persistence(tmp_path: Path):
    store = bootstrap_store(tmp_path, writer_identity="audit")
    store.create_workflow("duplicate")
    articles = _articles()
    with pytest.raises(SourceConfigError, match="duplicate capture_identity"):
        persist_capture_and_grouping(
            store,
            workflow_identity="duplicate",
            source_set=SOURCES,
            articles=(articles[0], articles[0], *articles[1:]),
            failures=(),
            observed_at="2026-09-29T01:00:00Z",
        )
    assert store.load_workflow("duplicate")["state"] == "DISCOVERED"
    assert not (store.root / "blobs/source-sets").exists()
    assert not (store.root / "blobs/capture-batches").exists()
    assert not (store.root / "blobs/captures").exists()


def test_maximum_articles_is_enforced_before_any_persistence(tmp_path: Path):
    limited = source_set_from_definitions((replace(SOURCES[0], maximum_articles=1),))
    first = _articles()[0]
    second = replace(
        first,
        capture_identity="f" * 64,
        article_url="https://one.example/second",
    )
    store = bootstrap_store(tmp_path, writer_identity="audit")
    store.create_workflow("over-limit")
    with pytest.raises(SourceConfigError, match="maximum_articles"):
        persist_capture_and_grouping(
            store,
            workflow_identity="over-limit",
            source_set=limited,
            articles=(first, second),
            failures=(),
            observed_at="2026-09-29T01:00:00Z",
        )
    assert store.load_workflow("over-limit")["state"] == "DISCOVERED"
    assert not (store.root / "blobs").exists()


@pytest.mark.parametrize("mode", ("duplicate", "extra", "invalid_shape", "captured_and_failed"))
def test_failure_records_are_unique_complete_and_consistent(mode: str):
    definitions = SOURCES.definitions
    captures = [definitions[0].source_id] if mode == "captured_and_failed" else []
    base = {
        "source_identity": definitions[0].source_id,
        "failure_class": "TimeoutError",
        "detail": "fixture",
    }
    if mode == "duplicate":
        failures = [base, dict(base)]
    elif mode == "extra":
        failures = [{**base, "source_identity": "outside"}]
    elif mode == "invalid_shape":
        failures = [{"source_identity": definitions[0].source_id, "failure_class": "TimeoutError"}]
    else:
        failures = [base]
    with pytest.raises(SourceConfigError):
        _reconcile_source_dispositions(definitions, captures, failures)


def test_mixed_batch_records_all_three_dispositions_and_rehydrates(tmp_path: Path):
    definitions = (
        SourceDefinition("captured", "Captured", "https://captured.example/feed", ("news",), 5),
        SourceDefinition("empty", "Empty", "https://empty.example/feed", ("news",), 5),
        SourceDefinition("failed", "Failed", "https://failed.example/feed", ("news",), 5),
    )
    source_set = source_set_from_definitions(definitions)

    def mixed_transport(source: SourceDefinition, timeout: float) -> FetchResponse:
        del timeout
        if source.source_id == "failed":
            raise OSError("offline")
        if source.source_id == "empty":
            payload = b"<rss><channel></channel></rss>"
        else:
            payload = (
                b"<rss><channel><item><title>Guvernul anunta masura publica</title>"
                b"<link>https://captured.example/article</link>"
                b"<description>Guvernul anunta masura publica.</description>"
                b"</item></channel></rss>"
            )
        return FetchResponse(payload, source.url, "application/rss+xml")

    store = bootstrap_store(tmp_path, writer_identity="audit")
    orchestrator = ProductOrchestrator(store)
    orchestrator.create_workflow("mixed")
    groups, failures = orchestrator.capture_and_group(
        workflow_identity="mixed",
        source_set=source_set,
        transport=mixed_transport,
        captured_at="2026-09-29T01:00:00Z",
    )
    assert len(groups) == 1
    assert len(failures) == 1
    assert _batch(store)["source_dispositions"] == [
        {"article_count": 1, "outcome": "CAPTURED", "source_identity": "captured"},
        {"article_count": 0, "outcome": "NO_ELIGIBLE_ENTRIES", "source_identity": "empty"},
        {
            "article_count": 0,
            "failure_class": "OSError",
            "outcome": "CAPTURE_FAILED",
            "source_identity": "failed",
        },
    ]
    from pastila_scout.vnext_scout_production_v1 import validate_workflow_event_membership
    assert validate_workflow_event_membership(
        store,
        workflow_identity="mixed",
        event_identity=groups[0].event_identity,
    )


def test_issuance_and_recovery_share_reconciliation_semantics(tmp_path: Path):
    store = bootstrap_store(tmp_path, writer_identity="audit")
    store.create_workflow("same-semantics")
    articles = _articles()
    groups = persist_capture_and_grouping(
        store,
        workflow_identity="same-semantics",
        source_set=SOURCES,
        articles=articles,
        failures=(),
        observed_at="2026-09-29T01:00:00Z",
    )
    from pastila_scout.vnext_scout_production_v1 import validate_workflow_event_membership
    assert validate_workflow_event_membership(
        store,
        workflow_identity="same-semantics",
        event_identity=groups[0].event_identity,
    )


@pytest.mark.parametrize("terminal", (False, True))
def test_downstream_and_terminal_recovery_fail_closed_on_capture_evidence_loss(
    tmp_path: Path, terminal: bool
):
    if terminal:
        store, orchestrator, _, workflow = _persisted_factual_bundle(
            tmp_path, structural=False, outcome="ABSTAIN"
        )
        loader = lambda: orchestrator.load_factual_result_bundle(workflow)
    else:
        store, orchestrator, _ = _HELPERS["prepare"](tmp_path)
        loader = lambda: orchestrator.load_editor_review_bundle("product-flow")
    list((store.root / "blobs/capture-batches").glob("*.json"))[0].unlink()
    with pytest.raises(ProductOrchestratorError):
        loader()

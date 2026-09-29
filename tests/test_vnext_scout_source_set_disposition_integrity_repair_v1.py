from __future__ import annotations

import copy
import inspect
import json
import runpy
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.vnext_product_orchestrator_v1 import ProductOrchestratorError
from pastila_scout.vnext_scout_production_v1 import (
    CaptureFailure,
    CapturedArticle,
    SourceConfigError,
    ValidatedSourceSet,
    load_sources,
    persist_capture_and_grouping,
)

_HELPERS = runpy.run_path(
    str(Path(__file__).with_name("test_vnext_product_orchestrator_integrated_core_e2e_v1.py"))
)
SOURCES = _HELPERS["SOURCES"]
prepare = _HELPERS["prepare"]
_persisted_factual_bundle = _HELPERS["_persisted_factual_bundle"]


def _only(root: Path, subdir: str) -> Path:
    paths = list((root / subdir).glob("*.json"))
    assert len(paths) == 1
    return paths[0]


def test_source_set_is_typed_canonical_and_identity_bound():
    assert isinstance(SOURCES, ValidatedSourceSet)
    assert SOURCES.source_set_identity == SOURCES.canonical_document["sources_identity"]
    assert load_sources(SOURCES.canonical_document) == SOURCES


@pytest.mark.parametrize("mode", ("false_identity", "subset", "extra", "modified", "duplicate"))
def test_source_set_definition_faults_fail_closed(mode: str):
    value = copy.deepcopy(SOURCES.canonical_document)
    if mode == "false_identity":
        value["sources_identity"] = "f" * 64
    elif mode == "subset":
        value["sources"] = value["sources"][:-1]
    elif mode == "extra":
        value["sources"].append({**value["sources"][0], "id": "extra"})
    elif mode == "modified":
        value["sources"][0]["url"] = "https://modified.example/feed"
    else:
        value["sources"].append(copy.deepcopy(value["sources"][0]))
    with pytest.raises(SourceConfigError):
        load_sources(value)


def test_capture_api_accepts_one_source_set_authority():
    parameters = inspect.signature(_HELPERS["ProductOrchestrator"].capture_and_group).parameters
    assert "source_set" in parameters
    assert "sources_identity" not in parameters
    assert "sources" not in parameters


def test_capture_batch_records_exhaustive_per_source_dispositions(tmp_path: Path):
    store, _, _ = prepare(tmp_path)
    batch = json.loads(_only(store.root, "blobs/capture-batches").read_text(encoding="utf-8"))
    dispositions = batch["source_dispositions"]
    assert [item["source_identity"] for item in dispositions] == [item.source_id for item in SOURCES]
    assert all(item["outcome"] == "CAPTURED" and item["article_count"] == 1 for item in dispositions)
    assert batch["source_set_reference"] == f"blobs/source-sets/{SOURCES.source_set_identity}.json"


def test_no_eligible_and_failure_dispositions_are_explicit(tmp_path: Path):
    store = _HELPERS["bootstrap_store"](tmp_path, writer_identity="writer")
    store.create_workflow("dispositions")
    failure = CaptureFailure(SOURCES[1].source_id, "TimeoutError", "fixture")
    persist_capture_and_grouping(
        store,
        workflow_identity="dispositions",
        source_set=SOURCES,
        articles=(),
        failures=(failure,),
        observed_at="2026-09-29T01:00:00Z",
    )
    batch = json.loads(_only(store.root, "blobs/capture-batches").read_text(encoding="utf-8"))
    assert batch["source_dispositions"] == [
        {"article_count": 0, "source_identity": SOURCES[0].source_id, "outcome": "NO_ELIGIBLE_ENTRIES"},
        {"article_count": 0, "failure_class": "TimeoutError", "source_identity": SOURCES[1].source_id, "outcome": "CAPTURE_FAILED"},
    ]


def test_capture_provenance_must_match_exact_source_definition(tmp_path: Path):
    store, _, _ = prepare(tmp_path)
    capture = json.loads(sorted((store.root / "blobs/captures").glob("*.json"))[0].read_text(encoding="utf-8"))
    article = CapturedArticle(**{key: tuple(value) if key == "categories" else value for key, value in capture.items() if key not in {"schema", "schema_version"}})
    clean = _HELPERS["bootstrap_store"](tmp_path / "clean", writer_identity="writer")
    clean.create_workflow("wrong-provenance")
    with pytest.raises(Exception, match="provenance"):
        persist_capture_and_grouping(
            clean,
            workflow_identity="wrong-provenance",
            source_set=SOURCES,
            articles=(replace(article, source_name="modified"),),
            failures=(),
            observed_at="2026-09-29T01:00:00Z",
        )


@pytest.mark.parametrize("mode", ("absent", "altered"))
def test_source_set_artifact_faults_fail_closed(tmp_path: Path, mode: str):
    store, orchestrator, _ = prepare(tmp_path)
    path = _only(store.root, "blobs/source-sets")
    if mode == "absent":
        path.unlink()
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
        value["sources"][0]["name"] = "altered"
        path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_editor_review_bundle("product-flow")


@pytest.mark.parametrize("field", ("source_dispositions", "source_set_reference", "sources_identity"))
def test_batch_source_authority_tampering_fails_closed(tmp_path: Path, field: str):
    store, orchestrator, _ = prepare(tmp_path)
    path = _only(store.root, "blobs/capture-batches")
    value = json.loads(path.read_text(encoding="utf-8"))
    if field == "source_dispositions":
        value[field] = value[field][:-1]
    elif field == "source_set_reference":
        value[field] = "blobs/source-sets/" + "f" * 64 + ".json"
    else:
        value[field] = "f" * 64
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_editor_review_bundle("product-flow")


@pytest.mark.parametrize("terminal", (False, True))
def test_downstream_and_terminal_recovery_require_source_set_authority(tmp_path: Path, terminal: bool):
    if terminal:
        store, orchestrator, _, workflow = _persisted_factual_bundle(
            tmp_path, structural=False, outcome="ABSTAIN"
        )
        loader = lambda: orchestrator.load_factual_result_bundle(workflow)
    else:
        store, orchestrator, _ = prepare(tmp_path)
        loader = lambda: orchestrator.load_editor_review_bundle("product-flow")
    _only(store.root, "blobs/source-sets").unlink()
    with pytest.raises(ProductOrchestratorError):
        loader()

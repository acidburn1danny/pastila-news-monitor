from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_scout_production_v1 import (
    SourceConfigError,
    SourceDefinition,
    _reconcile_source_dispositions,
)
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION
from pastila_scout.vnext_workflow_v1 import STATES, TRANSITIONS

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
RUNTIME_HASHES = {
    "src/pastila_scout/vnext_product_orchestrator_v1.py": "f158c01a3d48455c58f0a32780df607a4dcf4a35c936bcf3645d2dd1e3c689e7",
    "src/pastila_scout/vnext_scout_production_v1.py": "b08633014c2d59ab39b668d3371bbc37003c676e606584d2d0333c784226632d",
    "src/pastila_scout/vnext_workflow_v1.py": "b3214f3b9f43ae14751bd0ecc2c04d055435ca56996ed735c438efd6d930506a",
}
EXPECTED_COMMON = {
    "cardinality": "EXACTLY_ONE_PER_ENABLED_SOURCE",
    "domain": "EXACT_ENABLED_SOURCE_SET",
    "extra_source_dispositions_forbidden": True,
    "failure_disposition_binding": "BIJECTIVE_BY_SOURCE_IDENTITY",
    "missing_source_dispositions_forbidden": True,
    "outcome_derivation": {
        "CAPTURED": {"capture_count": "1_TO_SOURCE_MAXIMUM", "failure_record_count": 0},
        "CAPTURE_FAILED": {"capture_count": 0, "failure_record_count": 1},
        "NO_ELIGIBLE_ENTRIES": {"capture_count": 0, "failure_record_count": 0},
    },
    "source_identity_unique": True,
}
EXPECTED_TERMINALS = {
    "CAPTURE_FAILED": {
        "capture_count": 0,
        "disposition_counts": {
            "CAPTURED": 0,
            "CAPTURE_FAILED": "AT_LEAST_ONE",
            "NO_ELIGIBLE_ENTRIES": "ZERO_OR_MORE",
            "TOTAL": "ENABLED_SOURCE_COUNT",
        },
        "failure_record_count": "EQUALS_CAPTURE_FAILED_DISPOSITION_COUNT",
        "operational_outcome": "FAIL",
    },
    "NO_ELIGIBLE_CONTENT": {
        "capture_count": 0,
        "disposition_counts": {
            "CAPTURED": 0,
            "CAPTURE_FAILED": 0,
            "NO_ELIGIBLE_ENTRIES": "ENABLED_SOURCE_COUNT",
            "TOTAL": "ENABLED_SOURCE_COUNT",
        },
        "failure_record_count": 0,
        "operational_outcome": "PASS",
    },
}


def load(name: str) -> dict[str, object]:
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def definitions() -> tuple[SourceDefinition, ...]:
    return (
        SourceDefinition("a", "A", "https://a.example/feed", ("news",), 2),
        SourceDefinition("b", "B", "https://b.example/feed", ("news",), 2),
        SourceDefinition("c", "C", "https://c.example/feed", ("news",), 2),
    )


def failure(source: str) -> dict[str, object]:
    return {"source_identity": source, "failure_class": "OSError", "detail": "offline"}


def test_authority_v6_is_content_addressed_and_semantically_exact():
    authority = load("vnext-active-product-workflow-state-contract-v6.json")
    assert authority["authority_identity"] == object_identity(
        {key: value for key, value in authority.items() if key != "authority_identity"}
    )
    assert authority["supersedes"] == "vnext-active-product-workflow-state-contract-v5"
    assert authority["source_disposition_contract"] == EXPECTED_COMMON
    assert authority["terminal_semantics"] == EXPECTED_TERMINALS
    assert set(map(tuple, authority["transitions"])) == set(TRANSITIONS)
    assert set(authority["states"]) == set(STATES)


def test_manifest_and_runtime_are_bound_without_runtime_change():
    authority = load("vnext-active-product-workflow-state-contract-v6.json")
    manifest = load("vnext-active-authority-audit-manifest-v1.json")
    assert manifest["manifest_identity"] == object_identity(
        {key: value for key, value in manifest.items() if key != "manifest_identity"}
    )
    assert manifest["active_authorities"]["workflow"]["identity"] == authority["authority_identity"]
    for relative, expected in RUNTIME_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    assert SCHEMA_VERSION == 7


def test_runtime_reconciliation_is_exhaustive_unique_and_source_ordered():
    actual = _reconcile_source_dispositions(
        definitions(), ("a",), (failure("b"),)
    )
    assert actual == [
        {"source_identity": "a", "outcome": "CAPTURED", "article_count": 1},
        {
            "source_identity": "b",
            "outcome": "CAPTURE_FAILED",
            "article_count": 0,
            "failure_class": "OSError",
        },
        {"source_identity": "c", "outcome": "NO_ELIGIBLE_ENTRIES", "article_count": 0},
    ]
    assert len(actual) == len(definitions())
    assert len({item["source_identity"] for item in actual}) == len(definitions())


def test_runtime_rejects_duplicate_failure_binding():
    with pytest.raises(SourceConfigError):
        _reconcile_source_dispositions(definitions(), (), (failure("b"), failure("b")))


def test_runtime_rejects_failure_outside_enabled_source_set():
    with pytest.raises(SourceConfigError):
        _reconcile_source_dispositions(definitions(), (), (failure("outside"),))


def test_runtime_rejects_capture_and_failure_for_same_source():
    with pytest.raises(SourceConfigError):
        _reconcile_source_dispositions(definitions(), ("b",), (failure("b"),))


def test_runtime_rejects_capture_count_above_source_maximum():
    with pytest.raises(SourceConfigError):
        _reconcile_source_dispositions(definitions(), ("a", "a", "a"), ())

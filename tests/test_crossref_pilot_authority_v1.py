"""Offline conformance tests for Milestone 10 Phase 1."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.crossref_pilot_authority_v1 import (
    FOUNDATION_COMMIT,
    build_crossref_pilot_authority_design_v1,
    canonical_authority_design_bytes_v1,
    crossref_pilot_authority_design_identity_v1,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "pastila_scout" / "crossref_pilot_authority_v1.py"
ARTIFACT = (
    ROOT
    / "docs"
    / "artifacts"
    / "milestone10-phase1-crossref-pilot-authority-design-v1.json"
)


def test_exact_owner_approved_phase_1_boundary() -> None:
    design = build_crossref_pilot_authority_design_v1()
    assert design.foundation_commit == FOUNDATION_COMMIT
    assert design.registry == "CROSSREF_ONLY"
    assert design.transport == "READ_ONLY_HTTPS"
    assert design.request_count == 1
    assert design.maximum_records == 10
    assert design.raw_and_normalized_storage == "SEPARATE_IDENTITY_DOMAINS"
    assert design.unresolved_owner_values == (
        "EXACT_ENDPOINT",
        "EXACT_DETERMINISTIC_QUERY",
    )
    assert set(design.prohibited) == {
        "DOWNSTREAM_PUBLISHING",
        "METADATA_ACQUISITION",
        "NETWORK_REQUESTS",
        "OPENALEX",
        "PHASE_2_EXECUTION",
        "RFC3161",
        "SCHEDULED_ACTIVATION",
        "SIGSTORE",
    }


def test_design_is_canonical_identity_bound_and_rejects_substitution() -> None:
    design = build_crossref_pilot_authority_design_v1()
    payload = canonical_authority_design_bytes_v1(design)
    assert payload.endswith(b"\n")
    assert payload == canonical_authority_design_bytes_v1(
        build_crossref_pilot_authority_design_v1()
    )
    assert len(crossref_pilot_authority_design_identity_v1(design)) == 64
    with pytest.raises(ValueError, match="not canonical"):
        canonical_authority_design_bytes_v1(
            replace(design, maximum_records=11)
        )


def test_committed_authority_artifact_is_the_canonical_design() -> None:
    design = build_crossref_pilot_authority_design_v1()
    assert ARTIFACT.read_bytes() == canonical_authority_design_bytes_v1(design)
    assert (
        crossref_pilot_authority_design_identity_v1(design)
        == "3ee1f209bf4b83c07d47b95c7bc4f76485bfcbfe7b7f73cffb5664fd533555c4"
    )


def test_phase_1_module_is_passive_and_has_no_capture_surface() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports = {
        node.names[0].name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import) and node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imports.isdisjoint(
        {"httpx", "requests", "socket", "urllib", "urllib.request"}
    )
    names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert not any(
        term in name
        for name in names
        for term in ("capture", "download", "fetch", "request", "transport")
    )

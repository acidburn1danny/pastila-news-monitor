"""Identity and evidence closure for Milestone 10 Phase 3."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path

from pastila_scout.crossref_capture_integration_v1 import (
    PHASE2_NORMALIZED_IDENTITY,
    PHASE2_PROOF_COMMIT,
    PHASE2_RAW_CAPTURE_IDENTITY,
    PHASE3_ACCEPTED_STATE_IDENTITY,
    PHASE3_EMPTY_STATE_IDENTITY,
    CrossrefIntegrationStateV1,
    integrate_crossref_normalized_bytes_v1,
)

ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = (
    ROOT
    / "docs/artifacts/milestone10-phase3-crossref-integration-qualification-v1.json"
)
NORMALIZED = (
    ROOT / ".pastila-runtime/milestone10-crossref-pilot-v2/normalized-records.json"
)
MODULE = ROOT / "src/pastila_scout/crossref_capture_integration_v1.py"
IMPLEMENTATION_TEST = ROOT / "tests/test_crossref_capture_integration_v1.py"
PHASE2_PUBLIC_COMMIT = "777a5f673f32f3fc06b1da7bae2ffcbba2baa399"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(*arguments: str) -> bytes:
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", *arguments], cwd=ROOT
    )


def test_phase3_qualification_has_exact_authority_and_file_bindings() -> None:
    value = json.loads(QUALIFICATION.read_bytes())
    assert set(value) == {
        "accepted_batch_identity",
        "accepted_state_identity",
        "base_public_commit",
        "base_public_ref",
        "base_public_tree",
        "empty_state_identity",
        "implementation_sha256",
        "implementation_test_sha256",
        "invariants",
        "normalized_identity",
        "phase2_proof_commit",
        "qualification_test_sha256",
        "raw_capture_identity",
        "record_count",
        "record_identities",
        "schema",
        "source_artifact_sha256",
        "verdict",
    }
    assert value["schema"] == "pastila-crossref-integration-qualification-v1"
    assert value["verdict"] == "PASS_OFFLINE_CROSSREF_INTEGRATION"
    assert value["base_public_commit"] == PHASE2_PUBLIC_COMMIT
    assert value["base_public_ref"] == (
        "refs/heads/milestone10/phase2-final-prenetwork"
    )
    assert (
        value["base_public_tree"]
        == _git("rev-parse", f"{PHASE2_PUBLIC_COMMIT}^{{tree}}").decode().strip()
    )
    assert value["phase2_proof_commit"] == PHASE2_PROOF_COMMIT
    assert value["raw_capture_identity"] == PHASE2_RAW_CAPTURE_IDENTITY
    assert value["normalized_identity"] == PHASE2_NORMALIZED_IDENTITY
    assert value["empty_state_identity"] == PHASE3_EMPTY_STATE_IDENTITY
    assert CrossrefIntegrationStateV1().identity == PHASE3_EMPTY_STATE_IDENTITY
    assert value["source_artifact_sha256"] == _sha256(NORMALIZED.read_bytes())
    assert value["implementation_sha256"] == _sha256(MODULE.read_bytes())
    assert value["implementation_test_sha256"] == _sha256(
        IMPLEMENTATION_TEST.read_bytes()
    )
    assert value["qualification_test_sha256"] == _sha256(Path(__file__).read_bytes())
    committed = _git(
        "show",
        f"{PHASE2_PROOF_COMMIT}:.pastila-runtime/"
        "milestone10-crossref-pilot-v2/normalized-records.json",
    )
    assert committed == NORMALIZED.read_bytes()


def test_phase3_qualification_reconstructs_exact_result_offline(monkeypatch) -> None:
    def network_forbidden(*args, **kwargs):
        raise AssertionError("qualification attempted network access")

    monkeypatch.setattr("socket.socket", network_forbidden)
    value = json.loads(QUALIFICATION.read_bytes())
    accepted = integrate_crossref_normalized_bytes_v1(
        CrossrefIntegrationStateV1(), NORMALIZED.read_bytes()
    )
    assert accepted.disposition == "ACCEPTED"
    assert accepted.batch is not None
    replay = integrate_crossref_normalized_bytes_v1(
        accepted.state, NORMALIZED.read_bytes()
    )

    assert accepted.batch.identity == value["accepted_batch_identity"]
    assert accepted.state.identity == value["accepted_state_identity"]
    assert accepted.state.identity == PHASE3_ACCEPTED_STATE_IDENTITY
    assert replay.disposition == "IDEMPOTENT_REPLAY"
    assert replay.state.identity == value["accepted_state_identity"]
    assert value["record_count"] == len(accepted.state.records) == 10
    assert value["record_identities"] == [
        record.identity for record in accepted.state.records
    ]
    assert value["invariants"] == {
        "atomic_quarantine_no_state_change": "PASS",
        "caller_selected_authority_rejected": "PASS",
        "deterministic_doi_order": "PASS",
        "exact_phase2_provenance": "PASS",
        "immutable_nested_metadata": "PASS",
        "no_network_or_persistence": "PASS",
        "qualified_state_input_only": "PASS",
        "raw_normalized_integrated_separation": "PASS",
        "replay_idempotent": "PASS",
    }
    assert (
        len(
            {
                PHASE2_RAW_CAPTURE_IDENTITY,
                PHASE2_NORMALIZED_IDENTITY,
                accepted.batch.identity,
                accepted.state.identity,
            }
        )
        == 4
    )


def test_phase3_module_has_no_network_or_persistence_import_boundary() -> None:
    tree = ast.parse(MODULE.read_bytes())
    imported_roots = {
        alias.name.partition(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").partition(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imported_roots.isdisjoint(
        {"http", "httpx", "socket", "sqlite3", "ssl", "urllib"}
    )

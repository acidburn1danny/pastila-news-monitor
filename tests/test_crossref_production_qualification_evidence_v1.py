"""Evidence closure for Milestone 10 Phase 4."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from pastila_scout.crossref_production_qualification_v1 import (
    OfflineCrossrefResponseV1,
    execute_offline_crossref_production_qualification_v1,
    recover_offline_crossref_production_qualification_v1,
)

ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = (
    ROOT / "docs/artifacts/milestone10-phase4-crossref-production-qualification-v1.json"
)
PROOF = ROOT / ".pastila-runtime/milestone10-crossref-pilot-v2"
BASE_COMMIT = "809be94457dcc0cc3dc6ab9f8671338882b4afb7"
BASE_TREE = "4a2886f9d183bd1cdf0248e9f64e750d35478ce1"


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def offline_response() -> OfflineCrossrefResponseV1:
    manifest = json.loads((PROOF / "raw-capture/manifest.json").read_bytes())
    headers = json.loads((PROOF / "raw-capture/response-headers.json").read_bytes())
    return OfflineCrossrefResponseV1(
        manifest["status"],
        tuple(tuple(pair) for pair in headers),
        (PROOF / "raw-capture/response-body.bin").read_bytes(),
    )


def test_qualification_binds_exact_authorities_and_bytes() -> None:
    value = json.loads(QUALIFICATION.read_bytes())
    assert set(value) == {
        "accepted_batch_identity",
        "accepted_state_identity",
        "base_phase3_commit",
        "base_phase3_tree",
        "document_sha256",
        "implementation_sha256",
        "implementation_test_sha256",
        "invariants",
        "normalized_identity",
        "outcome_identity",
        "qualification_test_sha256",
        "raw_capture_identity",
        "request_identity",
        "schema",
        "verdict",
    }
    assert value["schema"] == ("pastila-crossref-production-capture-qualification-v1")
    assert value["verdict"] == "PASS_OFFLINE_PRODUCTION_ORCHESTRATION"
    assert value["base_phase3_commit"] == BASE_COMMIT
    assert value["base_phase3_tree"] == BASE_TREE
    assert (
        subprocess.check_output(
            ["git", "rev-parse", f"{BASE_COMMIT}^{{tree}}"], cwd=ROOT, text=True
        ).strip()
        == BASE_TREE
    )
    assert value["implementation_sha256"] == sha256(
        (
            ROOT / "src/pastila_scout/crossref_production_qualification_v1.py"
        ).read_bytes()
    )
    assert value["implementation_test_sha256"] == sha256(
        (ROOT / "tests/test_crossref_production_qualification_v1.py").read_bytes()
    )
    assert value["qualification_test_sha256"] == sha256(Path(__file__).read_bytes())
    assert value["document_sha256"] == sha256(
        (
            ROOT / "docs/milestone10-phase4-crossref-production-qualification.md"
        ).read_bytes()
    )
    assert set(value["invariants"].values()) == {"PASS"}


def test_qualification_reconstructs_exact_result_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    value = json.loads(QUALIFICATION.read_bytes())

    def network_forbidden(*args, **kwargs):
        raise AssertionError("qualification attempted network access")

    monkeypatch.setattr("socket.socket", network_forbidden)
    root = tmp_path / "qualification"
    result = execute_offline_crossref_production_qualification_v1(
        root, offline_response()
    )
    assert result.identity == value["outcome_identity"]
    assert result.request_identity == value["request_identity"]
    assert result.raw_capture_identity == value["raw_capture_identity"]
    assert result.normalized_identity == value["normalized_identity"]
    assert result.batch_identity == value["accepted_batch_identity"]
    assert result.state_after_identity == value["accepted_state_identity"]
    assert recover_offline_crossref_production_qualification_v1(root) == result


def test_phase4_does_not_change_default_or_authorized_skip_boundaries() -> None:
    changed = set(
        subprocess.check_output(
            ["git", "diff", "--name-only", BASE_COMMIT, "--"],
            cwd=ROOT,
            text=True,
        ).splitlines()
    )
    changed.update(
        subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=ROOT,
            text=True,
        ).splitlines()
    )
    phase4 = {
        path
        for path in changed
        if "phase4" in path or "production_qualification" in path
    }
    assert phase4 == {
        "docs/artifacts/milestone10-phase4-crossref-production-qualification-v1.json",
        "docs/milestone10-phase4-crossref-production-qualification.md",
        "src/pastila_scout/crossref_production_qualification_v1.py",
        "tests/test_crossref_production_qualification_evidence_v1.py",
        "tests/test_crossref_production_qualification_v1.py",
    }
    assert "pyproject.toml" not in changed
    assert "tests/conftest.py" not in changed
    assert not any("crossref_pilot" in path for path in changed)
    assert not any("crossref_capture_integration" in path for path in changed)

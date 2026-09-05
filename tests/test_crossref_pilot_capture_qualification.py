from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from pastila_scout.crossref_pilot_offline_v1 import (
    RawResponseCaptureV1,
    normalize_capture_v1,
)

ROOT = Path(__file__).resolve().parents[1]
PROOF_ROOT = ROOT / ".pastila-runtime/milestone10-crossref-pilot-v2"
QUALIFICATION = (
    ROOT
    / "docs/artifacts/milestone10-phase2-crossref-pilot-capture-qualification-v1.json"
)
PROOF_COMMIT = "82f1cf1c681e014e73208fa32e5e4ed78d3f963a"

ARTIFACTS = {
    "attempt_consumed": PROOF_ROOT / "attempt-consumed.json",
    "normalized_records": PROOF_ROOT / "normalized-records.json",
    "raw_manifest": PROOF_ROOT / "raw-capture/manifest.json",
    "raw_request": PROOF_ROOT / "raw-capture/request.json",
    "response_body": PROOF_ROOT / "raw-capture/response-body.bin",
    "response_headers": PROOF_ROOT / "raw-capture/response-headers.json",
    "terminal_result": PROOF_ROOT / "terminal-result.json",
    "wire_request": PROOF_ROOT / "raw-capture/wire-request.http",
}


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_capture_qualification_binds_exact_committed_proof_bytes() -> None:
    value = json.loads(QUALIFICATION.read_bytes())
    assert value["schema"] == "pastila-crossref-pilot-capture-qualification-v1"
    assert value["verdict"] == "PASS_BOUNDED_CROSSREF_PILOT_CAPTURE"
    assert value["proof_commit"] == PROOF_COMMIT
    assert value["proof_tree"] == "73c2ec9e044036eafa0fcd5551f7e846b83cb36e"
    assert value["execution_authority_commit"] == (
        "3dd2ae1e8596f1a4146b87409e07c7dd626b6dbf"
    )
    assert value["artifact_sha256"] == {
        name: sha256(path.read_bytes()) for name, path in ARTIFACTS.items()
    }
    for path in ARTIFACTS.values():
        relative = path.relative_to(ROOT).as_posix()
        committed = subprocess.check_output(
            [
                "git",
                "-c",
                f"safe.directory={ROOT.as_posix()}",
                "show",
                f"{PROOF_COMMIT}:{relative}",
            ],
            cwd=ROOT,
        )
        assert committed == path.read_bytes()


def test_capture_qualification_reconstructs_semantic_identity_closure() -> None:
    value = json.loads(QUALIFICATION.read_bytes())
    manifest = json.loads(ARTIFACTS["raw_manifest"].read_bytes())
    headers = tuple(
        tuple(pair) for pair in json.loads(ARTIFACTS["response_headers"].read_bytes())
    )
    capture = RawResponseCaptureV1(
        manifest["request_identity"],
        manifest["status"],
        headers,
        ARTIFACTS["response_body"].read_bytes(),
    )
    normalized = normalize_capture_v1(capture)
    terminal = json.loads(ARTIFACTS["terminal_result"].read_bytes())
    assert capture.identity == value["raw_capture_identity"]
    assert normalized.canonical_bytes == ARTIFACTS["normalized_records"].read_bytes()
    assert normalized.identity == value["normalized_identity"]
    assert len(normalized.records) == value["record_count"] == 10
    assert len({record.DOI for record in normalized.records}) == 10
    assert terminal["raw_capture_identity"] == capture.identity
    assert terminal["normalized_identity"] == normalized.identity
    assert value["transport"] == {
        "attempts": 1,
        "pages": 1,
        "redirects": 0,
        "retries": 0,
    }


def test_capture_proof_has_no_v1_or_other_untracked_dependency() -> None:
    value = json.loads(QUALIFICATION.read_bytes())
    assert set(value["artifact_sha256"]) == set(ARTIFACTS)
    assert all("pilot-v2" in path.as_posix() for path in ARTIFACTS.values())
    assert value["invariants"]["no_untracked_dependency"] == "PASS"

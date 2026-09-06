"""Evidence closure for the bounded Crossref production execution."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pastila_scout.crossref_pilot_offline_v1 as phase2
from pastila_scout.crossref_production_capture_v1 import (
    CrossrefProductionCaptureReceiptV1,
)

ROOT = Path(__file__).resolve().parents[1]
PROOF_ROOT = ROOT / ".pastila-runtime/milestone10-crossref-production-capture-v1"
QUALIFICATION = ROOT / (
    "docs/artifacts/"
    "milestone10-phase5-crossref-production-capture-execution-qualification-v1.json"
)
CAPTURE_COMMIT = "a5a13dd2d2f4dde5ed5ec8a2df20c05fea6727c5"
CAPTURE_TREE = "5a028101ebc3afe8dd34b76e8f345e55af989dc0"
EXECUTION_AUTHORITY_COMMIT = "247a7658fab9916db5e4473ebc0bd151a6dac1cc"
EXECUTION_AUTHORITY_TREE = "570e06bca8b18dbb7f45a9b2983c6f24e070b469"
ARTIFACTS = {
    "attempt-consumed.json": (
        "eba2034006bf0317492c5b453e21b897878ef4292146a5f5eed17d86c8486bc5"
    ),
    "completion.json": (
        "f9cc2acac3c5df2f8c7d0b5124bdb12237eaf77f9a683fe0096ba8f4d78732c6"
    ),
    "raw-capture/manifest.json": (
        "e5e3c6608e6b76f0bfaadb1a85b463c16cd8d8166a073f0b0377e058d250025e"
    ),
    "raw-capture/request.json": (
        "b34ecc203014226eba2188700876630060b0c5da719b1f88ac2b29579051744b"
    ),
    "raw-capture/response-body.bin": (
        "5fee9b617bb9ae59eea01eb5953a3328e7bccb07b1b286d61eb351331b83e36c"
    ),
    "raw-capture/response-headers.json": (
        "aa435b09b1f6088f8110fb7db425fb0652d5ecd06d3c85ca8982bed3788afbff"
    ),
    "raw-capture/wire-request.http": (
        "3a12fd685d9efd30afcd5fda04f8e1f5034ebc1144a224265ba0b18dfe70a4c1"
    ),
}


def _git(*arguments: str) -> bytes:
    return subprocess.check_output(["git", *arguments], cwd=ROOT)


def test_execution_qualification_binds_committed_capture_bytes() -> None:
    value = json.loads(QUALIFICATION.read_bytes())
    assert value["schema"] == (
        "pastila-crossref-production-capture-execution-qualification-v1"
    )
    assert value["verdict"] == "PASS_BOUNDED_CROSSREF_PRODUCTION_CAPTURE"
    assert value["capture_commit"] == CAPTURE_COMMIT
    assert value["capture_tree"] == CAPTURE_TREE
    assert value["execution_authority_commit"] == EXECUTION_AUTHORITY_COMMIT
    assert value["execution_authority_tree"] == EXECUTION_AUTHORITY_TREE
    assert _git("show", "-s", "--format=%T", CAPTURE_COMMIT).strip().decode() == (
        CAPTURE_TREE
    )
    assert _git("show", "-s", "--format=%P", CAPTURE_COMMIT).strip().decode() == (
        EXECUTION_AUTHORITY_COMMIT
    )
    assert value["artifact_sha256"] == ARTIFACTS
    for relative, identity in ARTIFACTS.items():
        proof_path = PROOF_ROOT.relative_to(ROOT).as_posix()
        committed = _git("show", f"{CAPTURE_COMMIT}:{proof_path}/{relative}")
        assert hashlib.sha256(committed).hexdigest() == identity
        assert (PROOF_ROOT / relative).read_bytes() == committed


def test_execution_qualification_reproduces_semantic_closure() -> None:
    value = json.loads(QUALIFICATION.read_bytes())
    headers = tuple(
        tuple(pair)
        for pair in json.loads(
            (PROOF_ROOT / "raw-capture/response-headers.json").read_bytes()
        )
    )
    manifest = json.loads((PROOF_ROOT / "raw-capture/manifest.json").read_bytes())
    body = (PROOF_ROOT / "raw-capture/response-body.bin").read_bytes()
    capture = phase2.RawResponseCaptureV1(
        request_identity=phase2.frozen_request_identity_v1(),
        status=manifest["status"],
        headers=headers,
        body=body,
    )
    phase2.validate_response_profile_v1(capture)
    normalized = phase2.normalize_capture_v1(capture)
    receipt = CrossrefProductionCaptureReceiptV1(
        request_identity=capture.request_identity,
        raw_capture_identity=capture.identity,
        record_count=len(normalized.records),
        transport_mode="PRODUCTION_DIRECT_HTTPS",
    )
    assert capture.identity == value["raw_capture_identity"]
    assert receipt.identity == value["completion_receipt_identity"]
    assert receipt.canonical_bytes == (PROOF_ROOT / "completion.json").read_bytes()
    assert value["record_count"] == len(normalized.records) == 10
    assert value["transport_mode"] == "PRODUCTION_DIRECT_HTTPS"
    assert value["activity"] == {
        "crossref_requests": 1,
        "openalex_requests": 0,
        "retries": 0,
    }
    assert set(value["invariants"].values()) == {"PASS"}


def test_execution_qualification_binds_its_test_and_preflight_qualification() -> None:
    value = json.loads(QUALIFICATION.read_bytes())
    assert (
        value["qualification_test_sha256"]
        == hashlib.sha256(
            subprocess.check_output(
                [
                    "git",
                    "show",
                    "04205ccb73542f3360b3811e31c2caef7adec1dc:"
                    + Path(__file__).relative_to(ROOT).as_posix(),
                ],
                cwd=ROOT,
            )
        ).hexdigest()
    )
    preflight = ROOT / (
        "docs/artifacts/"
        "milestone10-phase5-bounded-crossref-production-capture-qualification-v1.json"
    )
    assert (
        value["preflight_qualification_sha256"]
        == hashlib.sha256(preflight.read_bytes()).hexdigest()
    )

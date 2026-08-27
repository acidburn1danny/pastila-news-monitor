from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-span-shape-derived-coverage-candidate-v1.json"


def test_candidate_evidence_identity_and_source() -> None:
    value = json.loads(ARTIFACT.read_text("utf-8"))
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == value["canonical_identity"]
    source = ROOT / value["implementation"]["path"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == value["implementation"]["sha256"]


def test_candidate_remains_zero_inference_and_unbound() -> None:
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert value["captured_case01_verification"]["status"] == "FAIL"
    assert value["phase1_coverage_evidence"]["disposition"] == "BLOCKED"
    assert not any(value["authority"].values())
    assert value["verification"]["inference_calls"] == 0

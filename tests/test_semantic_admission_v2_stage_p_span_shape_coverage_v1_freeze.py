from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-span-shape-derived-coverage-candidate-v1-freeze.json"


def test_phase1_freeze_identity_and_boundaries() -> None:
    value = json.loads(RECEIPT.read_text("utf-8"))
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == value["canonical_identity"]
    assert value["status"] == "FROZEN"
    assert value["frozen_candidate_identity"] == "961b2eede98e31ee7b4e7ed4d786e66bae9c4c558d3cd11d964e1c16199d9aa9"
    assert not any(value["authority"].values())
    assert value["preservation"]["candidate_artifact_modified"] is False
    assert value["preservation"]["implementation_modified"] is False
    assert value["preservation"]["captured_run_evidence_modified"] is False
    assert value["preservation"]["zero_inference_evaluation_only"] is True

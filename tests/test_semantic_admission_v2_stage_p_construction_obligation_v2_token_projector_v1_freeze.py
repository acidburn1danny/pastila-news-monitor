from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-token-projector-v1-freeze.json"


def test_freeze_identity_and_bound_files_reproduce() -> None:
    receipt = json.loads(FREEZE.read_bytes())
    material = "\n".join(receipt["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == receipt["canonical_identity"]
    for relative, expected in receipt["bound_files"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_freeze_grants_no_execution_authority() -> None:
    receipt = json.loads(FREEZE.read_bytes())
    assert receipt["status"] == "OWNER_AUTHORIZED_FROZEN_ZERO_INFERENCE_CANDIDATE"
    assert receipt["historical_evidence"] == {"modified": False, "reinterpreted": False}
    assert receipt["authority"]["source_normalization"] is True
    assert all(value is False for key, value in receipt["authority"].items()
               if key != "source_normalization")

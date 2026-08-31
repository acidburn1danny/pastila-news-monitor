"""Regression coverage for immutable Development Pilot 05 ingestion."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pilot05_ingestion_verifies_without_writes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/verify_humor_batch2_development_pilot05_ingestion_v1.py"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    report = json.loads(result.stdout)
    assert report["verdict"] == "ATOMIC_IMMUTABLE_INGESTION_PASS"
    assert report["signature_verification"] == "PASS_8_OF_8"
    assert report["seven_proposition_bindings"] == "PASS"
    assert report["downstream_authorities"] is False

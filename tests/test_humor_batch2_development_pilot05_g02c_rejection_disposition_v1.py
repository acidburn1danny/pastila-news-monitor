"""Verify Pilot 05 non-positive G02C-rejection disposition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PATH = Path(__file__).resolve().parents[1] / "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-g02c-rejection-disposition-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot05_g02c_rejection_is_nonpositive_and_non_authorizing() -> None:
    disposition = json.loads(PATH.read_text(encoding="utf-8"))
    core = dict(disposition)
    identity = core.pop("disposition_identity")
    assert seal("B2_DEVELOPMENT_PILOT05_G02C_REJECTION_DISPOSITION_V1", core) == identity
    assert disposition["disposition"] == "DEVELOPMENT_NONPOSITIVE_G02C_REJECTION_EVIDENCE"
    assert disposition["g02c_verdict"] == "FAIL_INCOMPLETE_RECOVERABLE_REVERSE_DEPENDENCY"
    assert disposition["earliest_failed_link"] == "STEP2_TO_SELECTED_FACTUAL_RELATION"
    assert disposition["capability_state"] == "CONSUMED_1_OF_1_NO_FURTHER_CONSTRUCTION"
    assert disposition["candidate_bytes_modified"] is False
    assert disposition["positive_coverage_eligible"] is False and disposition["g03_eligible"] is False
    assert all(value is False for value in disposition["authority_matrix"].values())

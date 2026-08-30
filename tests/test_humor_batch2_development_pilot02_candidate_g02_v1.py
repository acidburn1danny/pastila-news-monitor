"""Verify the immutable Pilot 02 candidate's frozen G02 receipt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot02_g02_receipt_is_sealed_factual_and_non_authorizing() -> None:
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot02-candidate01-g02-v1.json").read_text(encoding="utf-8"))
    candidate = (ART / "humor-mechanics-batch2-development-pilot02-candidate01-v1.txt").read_bytes()
    core = dict(receipt)
    identity = core.pop("g02_receipt_identity")
    assert seal("B2_DEVELOPMENT_PILOT02_CANDIDATE_G02_V1", core) == identity
    assert receipt["g02_verdict"] == "PASS"
    assert hashlib.sha256(candidate).hexdigest() == receipt["candidate_raw_sha256"]
    assert len(receipt["factual_assertion_trace"]) == 1
    trace = receipt["factual_assertion_trace"][0]
    assert trace["authority_proposition_ids"] == ["P7"]
    assert trace["trace_result"] == "EXACT_SOURCE_BOUND_ASSERTION_WITH_TIME_SCOPE_AND_UNKNOWN_BOUNDARY"
    assert receipt["creative_nonfactual_separation_result"].startswith("PASS_")
    assert receipt["unsupported_inference_result"].startswith("PASS_")
    assert receipt["protected_target_result"].startswith("PASS_")
    assert receipt["sealed_mapping_accessed"] is False
    assert receipt["mechanism_adjudication_performed"] is False
    assert receipt["g02c_obligation_conformance_performed"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())

"""Verify Pilot 03 candidate G02 receipt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot03_g02_is_sealed_factual_and_non_authorizing() -> None:
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot03-candidate01-g02-v1.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("g02_receipt_identity")
    assert seal("B2_DEVELOPMENT_PILOT03_CANDIDATE_G02_V1", core) == identity
    assert receipt["g02_verdict"] == "PASS"
    assert receipt["candidate_identity"] == "b4555cc43bf16a466734aed46e93baa83bd9bc37d52d3826976be3370ccef72d"
    assert receipt["factual_assertion_trace"][0]["authority_proposition_ids"] == ["P7"]
    assert receipt["creative_nonfactual_separation_result"].startswith("PASS_")
    assert receipt["unsupported_inference_result"].startswith("PASS_")
    assert receipt["sealed_mapping_accessed"] is False
    assert receipt["mechanism_adjudication_performed"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())

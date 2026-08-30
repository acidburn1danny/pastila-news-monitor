from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_blind_naturalness_review_rejects_stable_surface_defects() -> None:
    value = load("humor-mechanics-batch2-development-pilot02-candidate01-g04a-naturalness-review-v1.json")
    identity = value.pop("g04a_review_identity")

    assert identity == seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G04A_NATURALNESS_REVIEW_V1", value)
    assert value["review_mode"] == "BLIND_ROMANIAN_SURFACE_ONLY"
    assert value["sealed_mapping_accessed"] is False
    assert value["mechanism_adjudication_performed"] is False
    assert value["findings"]["basic_grammaticality"]["verdict"] == "PASS"
    assert value["findings"]["idiomatic_word_order_and_register"]["verdict"] == "FAIL"
    assert value["findings"]["natural_creative_marking"]["verdict"] == "FAIL"
    assert value["g04a_verdict"] == "ROMANIAN_NATURALNESS_REJECTED"
    assert value["candidate_bytes_modified"] is False
    assert value["candidate_repair_attempted"] is False
    assert not any(value["performed"].values())
    assert not any(value["authority_matrix"].values())


def test_naturalness_receipt_is_sealed_and_voice_remains_separate() -> None:
    value = load("humor-mechanics-batch2-development-pilot02-candidate01-g04a-naturalness-receipt-v1.json")
    identity = value.pop("g04a_receipt_identity")

    assert identity == seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G04A_NATURALNESS_RECEIPT_V1", value)
    assert value["g04a_verdict"] == "ROMANIAN_NATURALNESS_REJECTED"
    assert value["voice_review_performed"] is False
    assert value["candidate_bytes_modified"] is False
    assert value["authority_matrix"]["voice_review"] is False
    assert not any(value["authority_matrix"].values())

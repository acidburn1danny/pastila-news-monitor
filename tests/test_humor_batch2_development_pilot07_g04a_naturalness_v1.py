from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def load(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_pilot07_blind_naturalness_passes_with_nonmaterial_reservations() -> None:
    value = load("humor-mechanics-batch2-development-pilot07-candidate01-g04a-naturalness-review-v1.json")
    identity = value.pop("g04a_review_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_G04A_NATURALNESS_REVIEW_V1", value)
    assert value["review_mode"] == "BLIND_ROMANIAN_SURFACE_ONLY"
    assert value["sealed_mapping_accessed"] is False
    assert value["mechanism_adjudication_performed"] is False
    assert value["findings"]["basic_grammaticality"]["verdict"] == "PASS"
    assert value["findings"]["instruction_or_governance_register_transfer"]["verdict"] == "PASS"
    assert value["findings"]["overall_naturalness"]["verdict"] == "PASS"
    assert value["g04a_verdict"] == "ROMANIAN_NATURALNESS_PASS"
    assert value["reservations"] == [
        "MINOR_PROCEDURAL_NOMINAL_REPETITION_NONMATERIAL",
        "MINOR_EDITORIAL_CREATIVE_MARKER_NONMATERIAL",
    ]
    assert value["candidate_bytes_modified"] is False
    assert value["candidate_repair_attempted"] is False
    assert not any(value["authority_matrix"].values())


def test_pilot07_naturalness_receipt_is_sealed_and_voice_stays_separate() -> None:
    value = load("humor-mechanics-batch2-development-pilot07-candidate01-g04a-naturalness-receipt-v1.json")
    identity = value.pop("g04a_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_G04A_NATURALNESS_RECEIPT_V1", value)
    assert value["g04a_verdict"] == "ROMANIAN_NATURALNESS_PASS"
    assert value["voice_review_performed"] is False
    assert value["next_gate_eligible"] == "VOICE_REVIEW_SEPARATELY_AUTHORIZED_ONLY"
    assert value["candidate_bytes_modified"] is False
    assert not any(value["authority_matrix"].values())

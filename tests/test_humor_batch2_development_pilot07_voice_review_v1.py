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


def test_pilot07_voice_rejects_material_cross_pilot_template_reuse() -> None:
    value = load("humor-mechanics-batch2-development-pilot07-candidate01-voice-review-v1.json")
    identity = value.pop("voice_review_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_BLIND_VOICE_REVIEW_V1", value)
    assert value["review_mode"] == "BLIND_MECHANISM_INDEPENDENT_VOICE_COMPATIBILITY"
    assert value["sealed_mapping_accessed"] is False
    assert value["mechanism_adjudication_performed"] is False
    assert value["owner_preference_accessed"] is False
    assert value["historical_surfaces_exposed_to_evaluator"] is False
    assert value["findings"]["tonal_coherence"]["verdict"] == "PASS"
    assert value["findings"]["payoff_economy"]["verdict"] == "PASS"
    assert value["findings"]["no_canned_opening_or_transition"]["verdict"] == "FAIL"
    assert value["findings"]["no_historical_wording_copy"]["verdict"] == "FAIL_PARTIAL_EXACT_TEMPLATE_REUSE"
    assert value["voice_verdict"] == "VOICE_REJECTED"
    assert value["stable_rejection_reasons"] == ["CANNED_CROSS_PILOT_CREATIVE_TRANSITION_REUSE"]
    assert value["candidate_bytes_modified"] is False
    assert value["candidate_repair_attempted"] is False
    assert not any(value["authority_matrix"].values())


def test_pilot07_voice_receipt_is_sealed_and_owner_review_is_not_eligible() -> None:
    value = load("humor-mechanics-batch2-development-pilot07-candidate01-voice-receipt-v1.json")
    identity = value.pop("voice_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_BLIND_VOICE_RECEIPT_V1", value)
    assert value["voice_verdict"] == "VOICE_REJECTED"
    assert value["owner_review_performed"] is False
    assert value["next_gate_eligible"] == "NONPOSITIVE_VOICE_REJECTION_FREEZE_SEPARATELY_AUTHORIZED_ONLY"
    assert value["candidate_bytes_modified"] is False
    assert not any(value["authority_matrix"].values())

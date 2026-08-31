from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_blind_voice_review_passes_without_using_mechanism_or_owner_preferences() -> None:
    value = load("humor-mechanics-batch2-development-pilot04-candidate01-voice-review-v1.json")
    identity = value.pop("voice_review_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT04_CANDIDATE01_BLIND_VOICE_REVIEW_V1", value)
    assert value["review_mode"] == "BLIND_MECHANISM_INDEPENDENT_VOICE_COMPATIBILITY"
    assert value["sealed_mapping_accessed"] is False
    assert value["mechanism_adjudication_performed"] is False
    assert value["owner_preference_accessed"] is False
    assert value["findings"]["no_canned_opening"]["verdict"] == "PASS"
    assert value["findings"]["no_canned_landing"]["verdict"] == "PASS"
    assert value["findings"]["register_reservation_materiality"]["verdict"] == "NONMATERIAL"
    assert value["findings"]["overall_voice_compatibility"]["verdict"] == "PASS"
    assert value["voice_verdict"] == "VOICE_PASS"
    assert value["candidate_bytes_modified"] is False
    assert not any(value["performed"].values())
    assert not any(value["authority_matrix"].values())


def test_voice_receipt_is_sealed_and_owner_review_remains_separate() -> None:
    value = load("humor-mechanics-batch2-development-pilot04-candidate01-voice-receipt-v1.json")
    identity = value.pop("voice_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT04_CANDIDATE01_BLIND_VOICE_RECEIPT_V1", value)
    assert value["voice_verdict"] == "VOICE_PASS"
    assert value["owner_review_performed"] is False
    assert value["next_gate_eligible"] == "OWNER_REVIEW_SEPARATELY_AUTHORIZED_WITH_POOL_PENDING_EXPLICIT"
    assert value["candidate_bytes_modified"] is False
    assert not any(value["authority_matrix"].values())

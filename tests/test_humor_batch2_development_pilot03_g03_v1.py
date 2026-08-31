"""Verify Pilot 03 blind G03 freeze and reconciliation."""

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


def test_pilot03_g03_is_blind_valid_and_target_dominant() -> None:
    prefix = "humor-mechanics-batch2-development-pilot03-candidate01-g03-"
    choice = json.loads((ART / f"{prefix}choice-set-v1.json").read_text(encoding="utf-8"))
    opened = json.loads((ART / f"{prefix}pass-a-v1.json").read_text(encoding="utf-8"))
    contrast = json.loads((ART / f"{prefix}pass-b-v1.json").read_text(encoding="utf-8"))
    isolation = json.loads((ART / f"{prefix}blind-isolation-v1.json").read_text(encoding="utf-8"))
    reconciliation = json.loads((ART / f"{prefix}reconciliation-v1.json").read_text(encoding="utf-8"))
    receipt = json.loads((ART / f"{prefix}receipt-v1.json").read_text(encoding="utf-8"))
    for value, field, namespace in (
        (choice, "choice_set_identity", "B2_DEVELOPMENT_PILOT03_G03_CHOICE_SET_V1"),
        (opened, "pass_identity", "B2_DEVELOPMENT_PILOT03_G03_OPEN_PASS_V1"),
        (contrast, "pass_identity", "B2_DEVELOPMENT_PILOT03_G03_CONTRAST_PASS_V1"),
        (isolation, "isolation_identity", "B2_DEVELOPMENT_PILOT03_G03_BLIND_ISOLATION_V1"),
        (reconciliation, "reconciliation_identity", "B2_DEVELOPMENT_PILOT03_G03_RECONCILIATION_V1"),
        (receipt, "g03_receipt_identity", "B2_DEVELOPMENT_PILOT03_G03_RECEIPT_V1"),
    ):
        core = dict(value); identity = core.pop(field)
        assert seal(namespace, core) == identity
    assert opened["choice_set_visible"] is False and opened["mapping_visible"] is False
    assert contrast["mapping_visible"] is False
    assert isolation["sealed_mapping_access"] is False and isolation["mapping_revealed"] is False
    assert contrast["result"]["primary_choice"] == "Absurd Logical Extension"
    assert contrast["result"]["primary_role"] == "DOMINANT"
    assert reconciliation["classification"] == "TARGET_RECOVERED_DOMINANT"
    assert reconciliation["mapping_revealed_after_blind_freeze"] is True
    assert receipt["g03_validity_status"] == "VALID_BLIND_REVIEW"
    assert receipt["target_dominant_recovery_established"] is True
    assert receipt["candidate_modified"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())

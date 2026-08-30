"""Verify Pilot 02 blind G03 passes before mapping reconciliation."""

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


def test_blind_passes_are_independent_sealed_and_unreconciled() -> None:
    choice = json.loads((ART / "humor-mechanics-batch2-development-pilot02-candidate01-g03-choice-set-v1.json").read_text(encoding="utf-8"))
    open_pass = json.loads((ART / "humor-mechanics-batch2-development-pilot02-candidate01-g03-pass-a-v1.json").read_text(encoding="utf-8"))
    contrast = json.loads((ART / "humor-mechanics-batch2-development-pilot02-candidate01-g03-pass-b-v1.json").read_text(encoding="utf-8"))
    isolation = json.loads((ART / "humor-mechanics-batch2-development-pilot02-candidate01-g03-blind-isolation-v1.json").read_text(encoding="utf-8"))
    for value, field, namespace in (
        (choice, "choice_set_identity", "B2_DEVELOPMENT_PILOT02_G03_CHOICE_SET_V1"),
        (open_pass, "pass_identity", "B2_DEVELOPMENT_PILOT02_G03_OPEN_PASS_V1"),
        (contrast, "pass_identity", "B2_DEVELOPMENT_PILOT02_G03_CONTRAST_PASS_V1"),
        (isolation, "isolation_identity", "B2_DEVELOPMENT_PILOT02_G03_BLIND_ISOLATION_V1"),
    ):
        core = dict(value)
        identity = core.pop(field)
        assert seal(namespace, core) == identity
    assert open_pass["choice_set_visible"] is False and open_pass["mapping_visible"] is False
    assert contrast["mapping_visible"] is False
    assert isolation["independent_evaluators"] is True
    assert isolation["sealed_mapping_access"] is isolation["mapping_revealed"] is False
    assert isolation["status"] == "BLIND_PASSES_FROZEN_AWAITING_RECONCILIATION"


def test_blind_freeze_source_cannot_resolve_mapping() -> None:
    source = (ROOT / "scripts/freeze_humor_batch2_development_pilot02_g03_blind_passes_v1.py").read_text(encoding="utf-8")
    assert "sealed-assignment-mapping" not in source
    assert "target_mapping" not in source

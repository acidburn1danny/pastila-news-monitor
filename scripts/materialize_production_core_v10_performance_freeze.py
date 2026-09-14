"""Materialize the bounded V10 performance bake-off disposition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v10-performance-bakeoff-freeze.json"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def build() -> dict[str, object]:
    selected_ms = [564467, 545165, 529095]
    baseline_ms = 1711574
    average_ms = sum(selected_ms) / len(selected_ms)
    core = {
        "schema": "pastila-production-core-v10-performance-bakeoff-freeze",
        "schema_version": 1,
        "status": "PASS_HARD_GATE_SELECTED_TARGET_NOT_MET",
        "selected_variant": "BF16_FLASH_REPEAT_KV_SELECTIVE_LOGITS",
        "selected_capabilities": ["BF16_AUTOCAST", "FLASH_ATTENTION", "REPEAT_KV", "SELECTIVE_ASSISTANT_LOGITS"],
        "baseline": {
            "elapsed_ms": baseline_ms,
            "checkpoint_identity": "b6d4a237ccdb38e51f038bbf22554404c23d55a2f1814863399291cb15500dda",
            "checkpoint_sha256": "8bb5bf3e7439ddef4690cca70a069bd195d799a8e3c4b21c58c0f835dd2ea9ea",
        },
        "selected_repetitions": [
            {"elapsed_ms": 564467, "loss": "0.19140107929706573", "receipt_identity": "ab0cfc40e442fab029ea2d0383557235ded53de13b3b3b0e5864c5d32f7df7d3", "receipt_sha256": "c7811ee626626c60bcb0db1fddc251ed62cedce6c02907009a9185c79b16b872"},
            {"elapsed_ms": 545165, "loss": "0.19140107929706573", "receipt_identity": "25f12e84a5946e9069f59d5f649635be586404fd893250d0ddbf018cb68a9f9d", "receipt_sha256": "000106eb40536c2a8c5abf2c5d88fbb670f21b54053f33565cf85bb4210410ed"},
            {"elapsed_ms": 529095, "loss": "0.19140107929706573", "receipt_identity": "f05e94de524ed8ef0270f9d064f763d3cfb8c80c88ee5cf7ee487309b915d163", "receipt_sha256": "a3df777eeef6869d7a989dd342e1049d2c79aa38b5fc8c28eb925b13524fb732"},
        ],
        "mean_elapsed_ms_numerator": sum(selected_ms),
        "mean_elapsed_ms_denominator": len(selected_ms),
        "speedup_numerator": baseline_ms * len(selected_ms),
        "speedup_denominator": sum(selected_ms),
        "hard_gate_speedup": 3,
        "target_speedup": 4,
        "stretch_speedup": 5,
        "hard_gate_pass": baseline_ms >= 3 * average_ms,
        "target_gate_pass": baseline_ms >= 4 * average_ms,
        "selected_peak_allocated_bytes": 16484919296,
        "selected_peak_reserved_bytes": 17198743552,
        "full_logits_reference_loss": "0.19140109419822693",
        "absolute_loss_delta": "0.00000001490116120",
        "flex_attention_disposition": {
            "status": "REJECTED_SEMANTIC_NON_EQUIVALENCE",
            "experiment_bounded_to_one_repaired_microstep": True,
            "elapsed_ms": 19620,
            "loss": "0.21999861299991608",
            "control_loss": "0.22096703946590424",
            "absolute_loss_delta": "0.00096842646598816",
            "receipt_identity": "8866e3fc77fe871c050238075a871d06b7e9de334a54d4b6b25fdb2a5b64167a",
            "receipt_sha256": "5100b26c323534cd194eadbd969752db635a7797774dbba07f641efd5e5a1b1a",
            "further_bakeoff_authorized": False,
        },
        "full_training_started": False,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return {**core, "freeze_identity": hashlib.sha256(canonical(core)).hexdigest()}


def main() -> int:
    value = build()
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    if OUTPUT.exists() and OUTPUT.read_bytes() != raw:
        raise SystemExit("published V10 performance freeze differs")
    OUTPUT.write_bytes(raw)
    print(value["freeze_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

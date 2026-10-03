from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"


def load(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_pack02_admission_and_fail_closed_rejections() -> None:
    decisions = [json.loads(x) for x in (ARTIFACTS / "vnext-voice-owner-gold-pack02-v1-admission.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [x["pack_record"] for x in decisions if x["admission"] == "ADMITTED"] == [1, 2, 3, 4, 5, 7, 10, 11]
    assert [x["pack_record"] for x in decisions if x["admission"] == "REJECTED_FAIL_CLOSED"] == [6, 8, 9]


def test_pack02_readiness_and_pack3_margin() -> None:
    dataset = load("vnext-voice-owner-gold-pack02-v1-dataset-successor.json")
    gates = dataset["second_experiment_readiness"]["gates"]
    assert (gates["train_positive"]["actual"], gates["train_positive"]["pass"]) == (33, False)
    assert (gates["validation_positive"]["actual"], gates["validation_positive"]["pass"]) == (12, True)
    assert (gates["commentary_tokens"]["actual"], gates["commentary_tokens"]["pass"]) == (8017, True)
    assert (gates["factual_restraint_support"]["actual"], gates["factual_restraint_support"]["pass"]) == (8, True)
    backlog = load("vnext-voice-owner-gold-pack02-v1-backlog.json")
    assert backlog["minimum_pack3"]["total_owner_written_records"] == 4
    assert backlog["minimum_pack3"]["validation_positive_records"] == 1


def test_pack02_factual_safety_partition_and_protected_state() -> None:
    dataset = load("vnext-voice-owner-gold-pack02-v1-dataset-successor.json")
    assert dataset["factual_safety"]["unsupported_fact_records"] == 0
    assert dataset["factual_safety"]["tuscany_tents_thread_separation"] == "PASS"
    assert dataset["partition"]["holdout_exposure"] == dataset["partition"]["qwen3_bakeoff_exposure"] == 0
    assert dataset["voice_state"] == "DISABLED_UNTIL_PROMOTION"
    assert dataset["gui_state"] == "ACTIVE"
    assert not dataset["active_product_modified"] and not dataset["canonical_rollback_modified"]

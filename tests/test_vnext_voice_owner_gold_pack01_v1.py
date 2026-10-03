from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def rows(name: str) -> list[dict]:
    return [json.loads(line) for line in (ART / name).read_text(encoding="utf-8").splitlines() if line]


def test_source_pack_is_exact() -> None:
    source = ART / "vnext-voice-owner-gold-pack01-v1/sources/PASTILA_VOICE_OWNER_GOLD_PACK_01.txt"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == "0be3c092e9189c516996b60f2ca1d858de52e2162fbdddcaeb299a30d26c45d5"


def test_ten_records_are_admitted_without_rewrite() -> None:
    admitted = rows("vnext-voice-owner-gold-pack01-v1-admission.jsonl")
    assert len(admitted) == 10
    assert [r["pack_record"] for r in admitted] == list(range(1, 11))
    assert all(not r["gold_commentary"]["rewritten"] for r in admitted)
    assert all(not r["gold_commentary"]["normalized"] for r in admitted)


def test_partition_is_family_disjoint_and_holdout_sealed() -> None:
    dataset = load("vnext-voice-owner-gold-pack01-v1-dataset-successor.json")
    train = rows("vnext-voice-owner-gold-pack01-v1-train-successor.jsonl")
    validation = rows("vnext-voice-owner-gold-pack01-v1-validation-successor.jsonl")
    assert {r["family_identity"] for r in train}.isdisjoint({r["family_identity"] for r in validation})
    assert dataset["partition"]["holdout_exposure"] == 0
    assert dataset["partition"]["qwen3_bakeoff_exposure"] == 0


def test_annotation_and_safety_closure() -> None:
    admitted = rows("vnext-voice-owner-gold-pack01-v1-admission.jsonl")
    for record in admitted:
        commentary = record["gold_commentary"]["text"]
        assert record["factual_commentary_taxonomy"]["unsupported_fact_admitted"] is False
        assert record["target_policy"]["protected_target_is_satire_target"] is False
        for annotations in record["mechanisms"].values():
            for annotation in annotations:
                assert annotation["evidence_span"] in commentary


def test_boundary_does_not_train_or_mutate_active_product() -> None:
    dataset = load("vnext-voice-owner-gold-pack01-v1-dataset-successor.json")
    assert dataset["training_performed"] is False
    assert dataset["weights_modified"] is False
    assert dataset["active_product_modified"] is False
    assert dataset["canonical_rollback_modified"] is False
    assert dataset["gui_state"] == "ACTIVE"
    assert dataset["voice_state"] == "DISABLED_UNTIL_PROMOTION"


def test_second_experiment_readiness_uses_demonstrated_support() -> None:
    dataset = load("vnext-voice-owner-gold-pack01-v1-dataset-successor.json")
    backlog = load("vnext-voice-owner-gold-pack01-v1-backlog-delta.json")
    assert dataset["quality_coverage"]["restraint"] == 4
    assert dataset["second_experiment_readiness"]["factual_restraint_records_pass"] is False
    assert backlog["remaining_second_experiment_gap"]["factual_restraint_records"] == 4

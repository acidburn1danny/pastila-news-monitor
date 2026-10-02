import json
from pathlib import Path
from scripts.build_vnext_voice_commentary_quality_gold_dataset_boundary_v1 import build

ROOT=Path(__file__).resolve().parents[1]

def result(): return build(ROOT)

def test_no_ineligible_evidence_is_admitted():
    d=result(); assert d["gold_records"]==d["train_records"]==d["validation_records"]==0
    assert d["rights_closure"]["training_eligible_records"]==0

def test_qwen3_bakeoff_remains_holdout_only():
    d=result(); assert d["holdout"]["records"]==24
    assert d["holdout"]["training_exposure"] is False

def test_episode_34_fails_closed_without_package():
    row=next(x for x in result()["admissions"] if x["corpus"]=="OWNER_WRITTEN_EPISODE_34")
    assert row["records"]==0 and row["disposition"]=="REJECT_PENDING_ADMISSION_PACKAGE"

def test_all_mechanism_gaps_remain_explicit():
    d=result(); assert d["mechanism_coverage"]["curriculum_mechanisms"]==50
    assert len(d["mechanism_coverage"]["positive_gaps"])==50 and d["mechanism_coverage"]["quota_fill"] is False

def test_empty_training_file_is_intentional():
    build(ROOT); assert (ROOT/"docs/artifacts/vnext-voice-commentary-quality-gold-dataset-train-v1.jsonl").read_bytes()==b""

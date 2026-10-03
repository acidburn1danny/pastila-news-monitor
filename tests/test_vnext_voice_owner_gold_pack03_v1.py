from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; A=ROOT/"docs/artifacts"
def load(n): return json.loads((A/n).read_text(encoding="utf-8"))
def test_pack03_admission_partition_and_margin():
 d=load("vnext-voice-owner-gold-pack03-v1-dataset-successor.json"); assert d["admission"]["admitted_record_numbers"]==[1,2,3,4,5,6,7,8,9]; assert d["admission"]["rejected_record_numbers"]==[]; assert (d["counts"]["train_positive"],d["counts"]["validation_positive"])==(39,15); assert all(x["pass"] for x in d["second_experiment_readiness"]["gates"].values())
def test_pack03_safety_and_sealed_evaluation():
 d=load("vnext-voice-owner-gold-pack03-v1-dataset-successor.json"); assert d["factual_safety"]["unsupported_fact_records"]==0; assert d["partition"]["holdout_exposure"]==d["partition"]["qwen3_bakeoff_exposure"]==0; assert not d["training_performed"] and not d["weights_modified"] and d["voice_state"]=="DISABLED_UNTIL_PROMOTION"
def test_pack03_corpus_freeze_is_non_promotable():
 f=load("vnext-voice-owner-gold-pack03-v1-corpus-freeze.json"); assert f["status"]=="FROZEN_READY_FOR_SECOND_EXPERIMENTAL_NON_PROMOTABLE_QWEN3_LORA"; assert not f["training_authorized"] and not f["promotion_ready"]

def test_pack03_record05_owner_clarification_is_bounded():
 d=load("vnext-voice-owner-gold-pack03-v1-dataset-successor.json"); assert d["factual_safety"]["record05_owner_semantic_clarification"]=="BOUND_TO_AGENCY_AUTHORITY_SENSE_ONLY"; assert d["factual_safety"]["unsupported_fact_records"]==0

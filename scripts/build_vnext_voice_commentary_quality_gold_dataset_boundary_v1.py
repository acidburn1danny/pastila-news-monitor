#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def identify(v,field):
    body={k:x for k,x in v.items() if k!=field}; return {**body,field:hashlib.sha256(canonical(body)).hexdigest()}
def load(root,name): return json.loads((root/name).read_text(encoding="utf-8"))
def lines(root,name): return [json.loads(x) for x in (root/name).read_text(encoding="utf-8").splitlines() if x.strip()]

def build(repo:Path)->dict:
    art=repo/"docs/artifacts"
    curriculum=load(art,"humor-mechanics-curriculum-v1.manifest.json")
    rights=load(art,"humor-mechanics-batch2-owned-authority-rights-instruments-v1.json")
    discovery=load(art,"humor-mechanics-curriculum-v1-batch2-current-authority-discovery-v1.json")
    plan=load(art,"humor-mechanics-curriculum-v1-batch2-acquisition-plan-v2.json")
    p3=load(art,"humor-mechanics-batch2-development-pilot03-candidate01-g05-owner-freeze-v1.json")
    p4=load(art,"humor-mechanics-batch2-development-pilot04-candidate01-g05-owner-freeze-v1.json")
    m20=load(art,"humor-mechanics-curriculum-v1-batch2-m20-owner-freeze-v1.json")
    m12=load(art,"humor-mechanics-curriculum-v1-batch2-m12-case01-contrast-freeze-v1.json")
    negatives=load(art,"humor-mechanics-curriculum-v1-batch2-historical-g02-negative-freeze-v1.json")
    bakeoff=lines(art,"editor-vnext-voice-bakeoff-boundary-v1-cases.jsonl")
    assert curriculum["mechanism_count"]==50 and curriculum["authority"]["training_authority"]=="none"
    assert rights["current_grants"]["training"] is False
    assert plan["authority"]["training_authorized"] is False
    assert p3["eligibility"]["training_eligible"] is False and p4["eligibility"]["training_eligible"] is False
    assert m20["authority"]["training_eligible"] is False and m12["model_visibility"] is False
    assert negatives["status"]=="FROZEN_NON_MODEL_VISIBLE_NEGATIVE_CONFUSABLE_EVIDENCE"
    assert len(bakeoff)==24 and len({x["case_identity"] for x in bakeoff})==24
    admissions=[
      {"corpus":"HUMOR_MECHANICS_CURRICULUM_V1","records":50,"disposition":"REJECT_AS_TRAINING_CORPUS","reason":"TAXONOMY_ONLY_TRAINING_AUTHORITY_NONE"},
      {"corpus":"BATCH2_OWNER_FROZEN_PILOT03","records":1,"disposition":"REJECT","reason":"DEVELOPMENT_ONLY_TRAINING_ELIGIBLE_FALSE"},
      {"corpus":"BATCH2_OWNER_FROZEN_PILOT04","records":1,"disposition":"REJECT","reason":"DEVELOPMENT_ONLY_TRAINING_ELIGIBLE_FALSE"},
      {"corpus":"BATCH2_M20_OWNER_FREEZE","records":1,"disposition":"REJECT","reason":"SUPPORTING_ONLY_TRAINING_ELIGIBLE_FALSE"},
      {"corpus":"BATCH2_M12_CONTRAST_FREEZE","records":1,"disposition":"REJECT","reason":"CONTRAST_ONLY_MODEL_VISIBILITY_FALSE"},
      {"corpus":"BATCH2_HISTORICAL_G02_NEGATIVES","records":len(negatives["records"]),"disposition":"REJECT","reason":"HISTORICAL_EVIDENCE_ONLY_NON_MODEL_VISIBLE"},
      {"corpus":"EDITORIAL_MECHANICS_BRIDGE","records":96,"disposition":"REJECT","reason":"FACTUAL_EDITOR_TASK_NOT_OWNER_GOLD_VOICE_COMMENTARY"},
      {"corpus":"QWEN3_BAKEOFF_CASES","records":24,"disposition":"RESERVE_HOLDOUT","reason":"EVALUATION_ONLY_NO_TRAINING_EXPOSURE"},
      {"corpus":"OWNER_WRITTEN_EPISODE_34","records":0,"disposition":"REJECT_PENDING_ADMISSION_PACKAGE","reason":"TEXT_BYTES_FACTUAL_SETUP_COMMENTARY_PROVENANCE_RIGHTS_AND_TRAINING_ELIGIBILITY_NOT_MATERIALIZED"},
    ]
    case_ids=sorted(x["case_identity"] for x in bakeoff)
    holdout_identity=hashlib.sha256(canonical(case_ids)).hexdigest()
    result=identify({
      "schema":"vnext-voice-commentary-quality-gold-dataset-boundary","schema_version":1,
      "status":"PASS_BOUNDARY_DATASET_NOT_READY","authority_head":"89bbea8065f0996ffd830c6e8122560e5f404bd0",
      "admissions":admissions,"gold_records":0,"train_records":0,"validation_records":0,
      "holdout":{"records":24,"case_set_identity":holdout_identity,"source":"QWEN3_BAKEOFF","model_exposure":False,"training_exposure":False},
      "future_blind_holdout_required":True,
      "partition_contract":{"assignment_before_construction":True,"split_unit":"TRANSITIVE_FAMILY_CLOSURE","family_level_isolation":True,"revision_co_location":True,"answer_keys_separately_custodied":True},
      "leakage_closure":{"train_holdout_identity_overlap":0,"train_holdout_path_overlap":0,"gold_deduplication":"VACUOUS_ZERO_GOLD","status":"PASS"},
      "rights_closure":{"concrete_training_grants":0,"training_eligible_records":0,"model_visible_records":0,"status":"FAIL_CLOSED_NO_ELIGIBLE_CORPUS"},
      "mechanism_coverage":{"curriculum_mechanisms":50,"train_positive_mechanisms":0,"train_compositional_examples":0,"positive_gaps":[x["id"] for x in curriculum["mechanisms"]],"quota_fill":False},
      "declared_batch2_priority_gaps":[x["mechanism"] for x in discovery["mechanism_inventory"] if x["status"] in {"GAP","POSITIVE_GAP"}],
      "factual_safety":{"setup_commentary_separate_required":True,"unsupported_fact_negatives_required":True,"abstention_gold_required":True,"constrained_projection_remains_runtime":True,"current_dataset_examples_checked":0,"status":"PASS_SCHEMA_ZERO_ADMITTED"},
      "lora_training_ready":False,"training_performed":False,"weights_modified":False,"promotion":False,"active_integration":False,
      "voice_state":"DISABLED_UNTIL_PROMOTION","legacy_dependency_count":0,
    },"result_identity")
    (art/"vnext-voice-commentary-quality-gold-dataset-boundary-v1.json").write_bytes(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n")
    (art/"vnext-voice-commentary-quality-gold-dataset-train-v1.jsonl").write_bytes(b"")
    return result
if __name__=="__main__":
 import argparse
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,default=Path.cwd());a=p.parse_args();print(json.dumps(build(a.repo.resolve()),ensure_ascii=False,sort_keys=True))

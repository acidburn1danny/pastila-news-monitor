import json
from pathlib import Path
from scripts.build_vnext_voice_owner_gold_scale_v1 import build
from scripts.audit_vnext_voice_owner_gold_scale_v1 import audit
ROOT=Path(__file__).resolve().parents[1]
def test_counts():
 d=build(ROOT); assert d['records']=={'positive':24,'negative':24,'abstention':4,'train_positive':18,'validation_positive':6}
def test_dedup_and_family_contamination_close():
 d=build(ROOT); assert d['deduplication']['status']=='PASS'; assert d['contamination']['train_validation_family_overlap']==0
def test_holdout_never_read_or_exposed():
 c=build(ROOT)['contamination']; assert c['owner_holdout_content_read'] is False and c['qwen3_bakeoff_content_read'] is False and c['qwen3_bakeoff_training_exposure'] is False
def test_negatives_reuse_exact_owner_bytes_without_generation():
 build(ROOT); rows=[json.loads(x) for x in (ROOT/'docs/artifacts/vnext-voice-owner-gold-scale-negatives-v1.jsonl').read_text().splitlines()]; assert len(rows)==24 and all(not r['new_text_generated'] and r['label']=='REJECT' for r in rows)
def test_abstention_is_metadata_only():
 build(ROOT); rows=[json.loads(x) for x in (ROOT/'docs/artifacts/vnext-voice-owner-gold-scale-abstention-v1.jsonl').read_text().splitlines()]; assert len(rows)==4 and all(r['model_visible_text'] is False for r in rows)
def test_training_remains_closed(): assert build(ROOT)['training_readiness']['qwen3_lora']=='NOT_READY'
def test_auditor(): assert audit(ROOT)['status']=='PASS'

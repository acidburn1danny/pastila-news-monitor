from pathlib import Path
from scripts.build_vnext_voice_training_ready_dataset_freeze_v1 import build
from scripts.audit_vnext_voice_training_ready_dataset_freeze_v1 import audit
ROOT=Path(__file__).resolve().parents[1]
def test_exhaustive_accounting():
 d=build(ROOT)['exhaustive_span_adjudication']; assert d['topic_sections_total']==69 and d['positive_records_admitted']==24 and d['sections_not_admitted']==45 and d['owner_corpus_defensibly_exhausted']
def test_manifest_is_content_addressed(): assert all(len(x['sha256'])==64 for x in build(ROOT)['frozen_dataset']['files'])
def test_holdout_is_identity_only(): assert all(x['content_access']=='DENIED' for x in build(ROOT)['frozen_dataset']['holdout_families'])
def test_abstention_fails_closed():
 d=build(ROOT); assert d['frozen_dataset']['abstention_evidence_records']==4 and d['frozen_dataset']['model_visible_abstention_records']==0
def test_objective_thresholds_fail_current_dataset():
 d=build(ROOT); assert d['actuals']['positive_train_records']<d['readiness_thresholds']['positive_train_records_min']; assert d['qwen3_lora_readiness']=='FAIL_CLOSED_NOT_READY'
def test_no_quota_fill(): assert build(ROOT)['mechanism_coverage']['quota_fill'] is False
def test_auditor(): assert audit(ROOT)['status']=='PASS'

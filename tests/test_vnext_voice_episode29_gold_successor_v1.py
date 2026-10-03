from pathlib import Path
from scripts.build_vnext_voice_episode29_gold_successor_v1 import build
from scripts.audit_vnext_voice_episode29_gold_successor_v1 import audit
ROOT=Path(__file__).resolve().parents[1]
def test_admission_identity():
 a=build(ROOT)['episode29_admission']; assert a['bytes']==17973 and a['sha256']=='6d945468828d8e0570535c8c1931371b21db4b129ae17af11ef5109a6fa6d194'
def test_partition():
 d=build(ROOT)['dataset']; assert d['train_families']==[22,23,24,25,26,27] and d['validation_families']==[28,29,30] and d['holdout_families']==[31,32,33,34]
def test_span_adjudication():
 s=build(ROOT)['span_adjudication']; assert s=={'topic_sections':10,'admitted':3,'rejected':7,'rejection_reason':'NO_ADDITIONAL_EXACT_FACTUAL_COMMENTARY_PAIR_WITHOUT_INFERENCE_OR_REWRITE'}
def test_successor_counts():
 d=build(ROOT)['dataset']; assert d['positive']==27 and d['negative']==27 and d['train_positive']==18 and d['validation_positive']==9
def test_coverage_and_dedup():
 d=build(ROOT); assert d['mechanism_coverage']['covered_total']==23 and len(d['mechanism_coverage']['positive_gaps'])==27 and d['deduplication']['status']=='PASS'
def test_holdout_closed(): assert build(ROOT)['contamination']['holdout_exposure']==0
def test_training_closed(): assert build(ROOT)['qwen3_lora_readiness']=='FAIL_CLOSED_NOT_READY'
def test_auditor(): assert audit(ROOT)['status']=='PASS'

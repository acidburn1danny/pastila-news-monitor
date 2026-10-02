import json
from pathlib import Path
from scripts.build_vnext_voice_owner_span_gold_v1 import build
from scripts.audit_vnext_voice_owner_span_gold_v1 import audit
ROOT=Path(__file__).resolve().parents[1]
def rows(name): return [json.loads(x) for x in (ROOT/f'docs/artifacts/vnext-voice-owner-span-gold-{name}-v1.jsonl').read_text().splitlines()]
def test_volume_and_partitions():
 d=build(ROOT); assert d['gold_volume']['train_records']==12 and d['gold_volume']['validation_records']==4
 assert {r['episode'] for r in rows('train')}=={22,23,24,25,26,27}; assert {r['episode'] for r in rows('validation')}=={28,30}
def test_exact_distinct_source_spans():
 build(ROOT)
 for r in rows('train')+rows('validation'):
  assert r['factual_setup']['line_end']<r['gold_commentary']['line_start']; assert r['rewritten'] is False and r['training_eligible'] is True
def test_holdout_is_not_read_or_emitted():
 d=build(ROOT); assert d['partition_leakage']['holdout_episodes_not_read']==[31,32,33,34]
 assert not ({31,32,33,34}&{r['episode'] for r in rows('train')+rows('validation')})
def test_mechanisms_are_curriculum_bound_without_quota_fill():
 m=build(ROOT)['mechanism_coverage']; assert m['curriculum_total']==50 and 0<m['covered_total']<50 and m['quota_fill'] is False
 for r in rows('train')+rows('validation'):
  roles=r['mechanisms']; assert len(set(roles['individual']+roles['supporting']+roles['composition']))==sum(map(len,roles.values()))
def test_rejections_are_explicit(): assert build(ROOT)['span_adjudication']['rejected']==4
def test_lora_remains_fail_closed(): assert build(ROOT)['training_readiness']['qwen3_lora']=='NOT_READY'
def test_auditor(): assert audit(ROOT)['status']=='PASS'

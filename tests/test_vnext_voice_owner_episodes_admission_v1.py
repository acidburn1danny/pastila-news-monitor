from pathlib import Path
from scripts.build_vnext_voice_owner_episodes_admission_v1 import build
from scripts.audit_vnext_voice_owner_episodes_admission_v1 import audit

ROOT = Path(__file__).resolve().parents[1]

def test_exact_source_admission_and_missing_29():
    d=build(ROOT); assert d["source_corpus"]["documents"]==12
    assert d["source_corpus"]["bytes_admitted"]==179756
    assert d["source_corpus"]["episode_29"]=="ABSENT_NOT_RECONSTRUCTED"

def test_rights_close_at_source_but_records_fail_closed():
    d=build(ROOT); assert d["rights_closure"]["source_documents_training_authorized"]==12
    assert d["gold_commentary"]["train_rows"]==0
    assert d["training_readiness"]["qwen3_lora"]=="NOT_READY"

def test_family_partition_is_disjoint_and_complete():
    p=build(ROOT)["partition"]; sets=[set(p[k]) for k in ("train","validation","owner_blind_holdout")]
    assert set.union(*sets)=={22,23,24,25,26,27,28,30,31,32,33,34}
    assert not (sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])

def test_curriculum_is_annotation_authority_only():
    m=build(ROOT)["mechanism_annotation"]
    assert m["curriculum_is_training_corpus"] is False and len(m["positive_gaps"])==50
    assert m["positive_training_mechanisms"]==[] and m["quota_fill"] is False

def test_holdouts_and_historical_evidence_are_unexposed():
    l=build(ROOT)["leakage_closure"]
    assert l["qwen3_bakeoff_training_exposure"] is False
    assert l["historical_development_evidence_training_exposure"] is False

def test_episode_34_keeps_draft_final_uncertainty():
    row=next(x for x in build(ROOT)["source_corpus"]["sources"] if x["episode"]==34)
    assert row["draft_final_status"]=="OWNER_ATTESTED_FILMED_SOURCE_DRAFT_LABEL_RETAINED"

def test_auditor_is_self_contained(): assert audit(ROOT)["status"]=="PASS"

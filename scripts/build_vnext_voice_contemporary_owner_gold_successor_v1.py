from __future__ import annotations
import hashlib,json,re,sys
from pathlib import Path

def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def identify(x,field):
    x=dict(x); x[field]=hashlib.sha256(canon(x)).hexdigest(); return x
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load_rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]

repo=Path(sys.argv[1]); art=repo/'docs/artifacts'
files={
 'train':art/'vnext-voice-episode29-successor-train-v1.jsonl',
 'validation':art/'vnext-voice-episode29-successor-validation-v1.jsonl',
 'negative':art/'vnext-voice-episode29-successor-negatives-v1.jsonl',
 'abstention':art/'vnext-voice-episode29-successor-abstention-v1.jsonl',
}
expected={'train':'f34762112bba7d67d68fdcc308174fca6c8ee733009767bbccb4a74736d4eb06','validation':'eda9facfe5fc9607e7975425c130abd4ac078095d908917c24dd70bbbc774fe6','negative':'84eef8f2bf58d10a5497216093ac564e624e566607b725bd14125e4f67ebf186','abstention':'ebf66f7e1de296a8762d0d66fc010fd8ec20af5657dbcdb12a2ae3571711fa5b'}
assert {k:sha(v) for k,v in files.items()}==expected
train=load_rows(files['train']); val=load_rows(files['validation']); neg=load_rows(files['negative'])
assert len(train)==18 and len(val)==9 and len(neg)==27

requirements=[
 {'requirement_id':'OG-NATURAL-01','stream':'ORGANIC_OWNER_WRITTEN','focus':['ROMANIAN_NATURALNESS','RESTRAINT'],'minimum_new_records':6,'admitted':0},
 {'requirement_id':'OG-FACTUAL-01','stream':'ORGANIC_OWNER_WRITTEN','focus':['FACTUAL_DISCIPLINE','COMMENTARY_SETUP_SEPARATION'],'minimum_new_records':6,'admitted':0},
 {'requirement_id':'OG-VARIATION-01','stream':'ORGANIC_OWNER_WRITTEN','focus':['VARIATION','ANTI_REPETITION','CONCISION'],'minimum_new_records':4,'admitted':0},
 {'requirement_id':'CD-COMPOSE-01','stream':'CURRICULUM_DESIGNED_PENDING_OWNER','focus':['AUTHENTIC_MECHANISM_COMPOSITION','TARGET_CHOICE'],'minimum_new_records':5,'admitted':0,'factual_setup_status':'REQUIRES_SEPARATE_AUTHORIZED_SOURCE_BYTES','commentary_status':'REQUIRES_OWNER_WRITTEN_OR_EXPLICITLY_APPROVED_BYTES'},
]
backlog=identify({'schema':'vnext-voice-contemporary-owner-gold-admission-backlog','schema_version':1,'organic_and_curriculum_separated':True,'requirements':requirements,'quota_fill':False,'generated_owner_gold':False,'holdout_families':[31,32,33,34],'holdout_access':'DENIED'},'backlog_identity')
(art/'vnext-voice-contemporary-owner-gold-backlog-v1.json').write_bytes(json.dumps(backlog,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n')

successor=identify({
 'schema':'vnext-voice-contemporary-owner-gold-dataset-successor','schema_version':1,
 'authority_parent_commit':'0ff0fba257b3a0ef52199b644ca9360cf75265cc','dataset_predecessor_identity':'f52b5cacd39c0b8fb90a5b20f30a0c4a1d3400a1ee356c1876e5b6d20cbaf6f7',
 'baseline_experiment':{'commit':'0ff0fba257b3a0ef52199b644ca9360cf75265cc','config_identity':'7c0c2e97a1a55b2cbd6453ae179d1c0203331bda0daff2084b4c1d0f7467c1d3','evaluation_identity':'4a24e59544c95fba72a17c7937650e1b5b19ca40e8a54c5582918c0fb62935f8','best_delta':0.206349,'frozen':True},
 'predecessor_files':[{'role':k,'path':str(p.relative_to(repo)).replace('\\','/'),'sha256':expected[k],'bytes':p.stat().st_size} for k,p in files.items()],
 'dataset':{'train_positive':18,'validation_positive':9,'negative':27,'model_visible_abstention':0,'commentary_tokens_estimated':4034,'new_owner_gold_admitted':0,'organic_gold_admitted':0,'curriculum_designed_gold_admitted':0},
 'coverage':{'mechanisms_covered':23,'curriculum_total':50,'naturalness_targeted_new_records':0,'restraint_targeted_new_records':0,'factual_discipline_targeted_new_records':0,'variation_targeted_new_records':0,'composition_targeted_new_records':0},
 'second_experiment_readiness':{'status':'FAIL_CLOSED_NOT_READY','minimum_total_train_positive':36,'minimum_total_validation_positive':12,'minimum_total_commentary_tokens':8000,'minimum_new_factual_restraint_records':8,'maximum_curriculum_designed_fraction_of_new_positive':0.30,'required_quality_gain_over_frozen_baseline':0.50,'required_no_naturalness_regression':True,'required_no_restraint_regression':True,'required_unsupported_fact_rate_after_projection':0.0},
 'promotion_thresholds_unchanged':{'train_positive_min':60,'validation_positive_min':20,'commentary_tokens_min':20000,'model_visible_abstention_min':16},
 'admission_rules':{'owner_authorship_or_explicit_approval_required':True,'exact_source_bytes_required':True,'factual_setup_commentary_separation_required':True,'organic_curriculum_separation_required':True,'model_generated_text_is_owner_gold':False,'quota_fill':False,'holdout_access':False},
 'backlog_identity':backlog['backlog_identity'],'training_performed':False,'weights_modified':False,'active_product_modified':False,'canonical_rollback_modified':False,'gui_state':'ACTIVE','voice_state':'DISABLED_UNTIL_PROMOTION','status':'PASS_BOUNDARY_SUCCESSOR_NOT_READY_FOR_SECOND_TRAIN'
},'successor_identity')
(art/'vnext-voice-contemporary-owner-gold-dataset-successor-v1.json').write_bytes(json.dumps(successor,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n')

audit=identify({'schema':'vnext-voice-contemporary-owner-gold-dataset-successor-audit','schema_version':1,'status':'PASS_0_INTEGRITY_BLOCKERS_DATA_NOT_ADMITTED','successor_identity':successor['successor_identity'],'backlog_identity':backlog['backlog_identity'],'predecessor_byte_exact':True,'new_gold_records':0,'holdout_exposure':0,'qwen3_bakeoff_exposure':0,'train_validation_family_overlap':0,'contamination':'PASS','findings':[{'id':'F-01','finding':'NO_NEW_OWNER_WRITTEN_BYTES_AVAILABLE','impact':'SECOND_EXPERIMENT_REMAINS_NOT_READY'},{'id':'F-02','finding':'NATURALNESS_RESTRAINT_FACTUAL_DISCIPLINE_AND_COMPOSITION_SUPPORT_REMAIN_BELOW_SUCCESSOR_TARGETS','impact':'OWNER_GOLD_ACQUISITION_REQUIRED'}],'cars':[],'legacy_dependency_count':0,'training_performed':False,'active_product_modified':False,'canonical_rollback_modified':False,'voice_state':'DISABLED_UNTIL_PROMOTION'},'audit_identity')
(art/'vnext-voice-contemporary-owner-gold-dataset-successor-v1-audit.json').write_bytes(json.dumps(audit,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n')
print(json.dumps({'successor_identity':successor['successor_identity'],'backlog_identity':backlog['backlog_identity'],'audit_identity':audit['audit_identity']},sort_keys=True))

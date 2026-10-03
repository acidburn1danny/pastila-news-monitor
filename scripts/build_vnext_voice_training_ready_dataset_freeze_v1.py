import hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_vnext_voice_owner_gold_scale_v1 import build as build_scale,canon

EPISODES=[22,23,24,25,26,27,28,30]
EXPECTED={22:8,23:9,24:9,25:8,26:9,27:9,28:8,30:9}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def topic_count(ep,text):
 lines=text.splitlines()
 if ep in {22,23,24,25,30}:
  floor={22:40,23:10,24:40,25:30,30:20}[ep]
  return sum(i>=floor and bool(re.match(r'^\s*[1-9]️⃣',x)) for i,x in enumerate(lines,1))
 if ep==26: return sum(bool(re.match(r'^# [1-9]\.',x)) for x in lines)
 if ep==27: return sum(bool(re.match(r'^# [1-9]️⃣',x)) for x in lines)
 if ep==28: return sum(bool(re.match(r'^## [1-9]\.',x)) for x in lines)
 raise AssertionError(ep)

def build(root:Path):
 scale=build_scale(root)
 inventory=[]
 for ep in EPISODES:
  p=root/f'docs/artifacts/vnext-voice-owner-episodes-v1/sources/episode-{ep}.txt'; count=topic_count(ep,p.read_text(encoding='utf-8-sig'))
  if count!=EXPECTED[ep]: raise ValueError(f'topic inventory mismatch {ep}: {count}')
  admitted=3
  inventory.append({'episode':ep,'family_identity':f'PASTILA_ACIDA_EPISODE_{ep}','topic_sections':count,'admitted_gold_records':admitted,'excluded_sections':count-admitted,'disposition':'EXHAUSTED_UNDER_EXACT_SEPARATION_CRITERION'})
 dataset_files=['vnext-voice-owner-gold-scale-train-v1.jsonl','vnext-voice-owner-gold-scale-validation-v1.jsonl','vnext-voice-owner-gold-scale-negatives-v1.jsonl','vnext-voice-owner-gold-scale-abstention-v1.jsonl']
 frozen=[{'path':'docs/artifacts/'+n,'sha256':sha(root/'docs/artifacts'/n),'bytes':(root/'docs/artifacts'/n).stat().st_size} for n in dataset_files]
 admission=json.loads((root/'docs/artifacts/vnext-voice-owner-episodes-admission-v1.json').read_text())
 holdout=[{'episode':x['episode'],'family_identity':x['family_identity'],'source_sha256':x['sha256'],'content_access':'DENIED'} for x in admission['source_corpus']['sources'] if x['episode'] in {31,32,33,34}]
 thresholds={'positive_train_records_min':60,'positive_validation_records_min':20,'gold_commentary_tokens_min':20000,'per_covered_mechanism_train_examples_min':3,'per_covered_mechanism_validation_examples_min':1,'negative_to_positive_ratio_min':1.0,'model_visible_abstention_records_min':16,'exact_duplicates_max':0,'normalized_duplicates_max':0,'family_overlap_max':0,'holdout_exposure_max':0,'unsupported_fact_rate_max':0.0,'required_blind_evaluation':'PASS'}
 actual={'positive_train_records':18,'positive_validation_records':6,'gold_commentary_tokens_estimated':3582,'covered_mechanisms':20,'negative_to_positive_ratio':1.0,'model_visible_abstention_records':0,'exact_duplicates':0,'normalized_duplicates':0,'family_overlap':0,'holdout_exposure':0,'blind_evaluation':'NOT_RUN_FOR_FROZEN_DATASET'}
 gates={'positive_train_records':False,'positive_validation_records':False,'gold_commentary_tokens':False,'per_mechanism_train_support':False,'per_mechanism_validation_support':False,'negative_ratio':True,'model_visible_abstention':False,'deduplication':True,'family_isolation':True,'holdout_isolation':True,'blind_evaluation':False}
 result={'schema':'vnext-voice-training-ready-dataset-freeze','schema_version':1,'status':'PASS_FREEZE_DATASET_NOT_TRAINING_READY','authority_parent':'7736fec40516b3781b0a777de4dcb6b66b9753cd','exhaustive_span_adjudication':{'topic_sections_total':sum(EXPECTED.values()),'positive_records_admitted':24,'sections_not_admitted':sum(EXPECTED.values())-24,'inventory':inventory,'exclusion_reason':'NO_ADDITIONAL_EXACT_FACTUAL_COMMENTARY_PAIR_ADJUDICATED_WITHOUT_REWRITE_OR_INFERENCE','owner_corpus_defensibly_exhausted':True},'frozen_dataset':{'files':frozen,'positive_records':24,'negative_records':24,'abstention_evidence_records':4,'model_visible_abstention_records':0,'train_families':[22,23,24,25,26,27],'validation_families':[28,30],'holdout_families':holdout,'qwen3_bakeoff':'EVALUATION_ONLY_CONTENT_ACCESS_DENIED'},'mechanism_coverage':scale['mechanism_coverage'],'deduplication':scale['deduplication'],'contamination':scale['contamination'],'factual_safety':scale['factual_safety'],'readiness_thresholds':thresholds,'actuals':actual,'readiness_gates':gates,'qwen3_lora_readiness':'FAIL_CLOSED_NOT_READY','training_performed':False,'weights_modified':False,'active_product_modified':False,'canonical_rollback_modified':False,'gui_state':'ACTIVE','voice_state':'DISABLED_UNTIL_PROMOTION','legacy_dependency_count':0}
 result['result_identity']=hashlib.sha256(canon(result)).hexdigest(); (root/'docs/artifacts/vnext-voice-training-ready-dataset-freeze-v1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n'); return result
if __name__=='__main__': build(Path(__file__).resolve().parents[1])

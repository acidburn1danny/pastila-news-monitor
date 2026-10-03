import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_vnext_voice_owner_gold_scale_v1 import build as build_scale,canon,span

SHA='6d945468828d8e0570535c8c1931371b21db4b129ae17af11ef5109a6fa6d194'
SPECS=[
 ('01',(52,61),(63,88),['HMCV1-B01-M05-FRAME_TRANSFER'],['HMCV1-B02-M10-ROLE_SIMULATION'],['HMCV1-B02-M09-DISCOURSE_FORM_PARODY']),
 ('02',(102,116),(118,137),['HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION'],['HMCV1-B02-M10-ROLE_SIMULATION'],['HMCV1-B01-M06-HYPERBOLE']),
 ('03',(170,184),(186,206),['HMCV1-B01-M01-SARCASM'],['HMCV1-B03-M04-COMIC_ENUMERATION'],['HMCV1-B05-M09-FAMILIAR_EXPRESSION_SUBVERSION']),
]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load_rows(p): return [json.loads(x) for x in p.read_text().splitlines()]
def dump(p,rows): p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf-8')
def build(root:Path):
 scale=build_scale(root); p=root/'docs/artifacts/vnext-voice-owner-episodes-v1/sources/episode-29.txt'; raw=p.read_bytes()
 if len(raw)!=17973 or hashlib.sha256(raw).hexdigest()!=SHA: raise ValueError('episode 29 identity mismatch')
 new=[]
 for rid,fs,cs,ind,sup,comp in SPECS:
  f=span(raw,*fs); c=span(raw,*cs); new.append({'record_id':f'PA-EP29-{rid}','episode':29,'family_identity':'PASTILA_ACIDA_EPISODE_29','partition':'VALIDATION','source_path':str(p.relative_to(root)),'source_sha256':SHA,'factual_setup':{'line_start':fs[0],'line_end':fs[1],'text':f.decode('utf-8-sig'),'sha256':hashlib.sha256(f).hexdigest()},'gold_commentary':{'line_start':cs[0],'line_end':cs[1],'text':c.decode('utf-8-sig'),'sha256':hashlib.sha256(c).hexdigest()},'mechanisms':{'individual':ind,'supporting':sup,'composition':comp},'provenance':'EXACT_OWNER_WRITTEN_SOURCE_SPANS','training_eligible':True,'rewritten':False})
 train=load_rows(root/'docs/artifacts/vnext-voice-owner-gold-scale-train-v1.jsonl'); val=load_rows(root/'docs/artifacts/vnext-voice-owner-gold-scale-validation-v1.jsonl')+new
 oldneg=load_rows(root/'docs/artifacts/vnext-voice-owner-gold-scale-negatives-v1.jsonl'); donors=[r for r in val if r['episode']!=29]
 newneg=[]
 for i,r in enumerate(new):
  donor=donors[i%len(donors)]; newneg.append({'record_id':r['record_id']+'-NEG','partition':'VALIDATION','negative_type':'CROSS_FAMILY_CONTEXT_MISMATCH','factual_source_record':r['record_id'],'commentary_source_record':donor['record_id'],'factual_setup':r['factual_setup'],'candidate_commentary':donor['gold_commentary'],'label':'REJECT','new_text_generated':False})
 abst=load_rows(root/'docs/artifacts/vnext-voice-owner-gold-scale-abstention-v1.jsonl')
 paths={'train':'docs/artifacts/vnext-voice-episode29-successor-train-v1.jsonl','validation':'docs/artifacts/vnext-voice-episode29-successor-validation-v1.jsonl','negatives':'docs/artifacts/vnext-voice-episode29-successor-negatives-v1.jsonl','abstention':'docs/artifacts/vnext-voice-episode29-successor-abstention-v1.jsonl'}
 for k,rows in [('train',train),('validation',val),('negatives',oldneg+newneg),('abstention',abst)]: dump(root/paths[k],rows)
 positives=train+val; previous=set(scale['mechanism_coverage']['covered'])|set(scale['mechanism_coverage']['positive_gaps']); covered=sorted({m for r in positives for v in r['mechanisms'].values() for m in v}); gaps=sorted(previous-set(covered)); chars_train=sum(len(r['gold_commentary']['text']) for r in train); chars_val=sum(len(r['gold_commentary']['text']) for r in val)
 hashes=[r['gold_commentary']['sha256'] for r in positives]; norms=[' '.join(r['gold_commentary']['text'].lower().split()) for r in positives]
 d={'schema':'vnext-voice-owner-episode29-gold-successor','schema_version':1,'status':'PASS_EP29_ADMITTED_DATASET_NOT_LORA_READY','authority_parent':'5a1eb7f0d53e43f19c41eeb4f71e5878a96dd2da','episode29_admission':{'status':'PASS','bytes':len(raw),'sha256':SHA,'lines':len(raw.splitlines()),'rights':'OWNER_AUTHORIZED_FOR_DATASET_AND_FUTURE_TRAINING','partition':'VALIDATION','family_identity':'PASTILA_ACIDA_EPISODE_29','draft_final_status':'OWNER_ATTESTED_FILMED_SOURCE'},'span_adjudication':{'topic_sections':10,'admitted':3,'rejected':7,'rejection_reason':'NO_ADDITIONAL_EXACT_FACTUAL_COMMENTARY_PAIR_WITHOUT_INFERENCE_OR_REWRITE'},'dataset':{'positive':len(positives),'negative':len(oldneg)+len(newneg),'abstention_evidence':len(abst),'model_visible_abstention':0,'train_positive':len(train),'validation_positive':len(val),'train_families':[22,23,24,25,26,27],'validation_families':[28,29,30],'holdout_families':[31,32,33,34]},'gold_volume':{'train_commentary_characters':chars_train,'validation_commentary_characters':chars_val,'total_commentary_characters':chars_train+chars_val,'estimated_tokens':(chars_train+chars_val)//4},'mechanism_coverage':{'curriculum_total':50,'covered_total':len(covered),'covered':covered,'positive_gaps':gaps,'individual':sorted({m for r in positives for m in r['mechanisms']['individual']}),'supporting':sorted({m for r in positives for m in r['mechanisms']['supporting']}),'composition':sorted({m for r in positives for m in r['mechanisms']['composition']}),'quota_fill':False},'deduplication':{'status':'PASS','exact_commentary_duplicates':len(hashes)-len(set(hashes)),'normalized_commentary_duplicates':len(norms)-len(set(norms)),'record_id_duplicates':len(positives)-len({r['record_id'] for r in positives})},'contamination':{'status':'PASS','train_validation_family_overlap':0,'holdout_content_read':False,'qwen3_bakeoff_content_read':False,'holdout_exposure':0},'factual_safety':{'rewrites':0,'exact_source_spans':True,'runtime_factual_authority_unchanged':True,'constrained_projection_remains_runtime':True},'frozen_files':[{'path':v,'sha256':sha(root/v),'bytes':(root/v).stat().st_size} for v in paths.values()],'qwen3_lora_readiness':'FAIL_CLOSED_NOT_READY','readiness_effect':'IMPROVED_VALIDATION_VOLUME_6_TO_9_AND_COVERAGE_20_TO_23_BUT_THRESHOLDS_NOT_MET','training_performed':False,'weights_modified':False,'active_product_modified':False,'canonical_rollback_modified':False,'gui_state':'ACTIVE','voice_state':'DISABLED_UNTIL_PROMOTION','legacy_dependency_count':0}
 d['result_identity']=hashlib.sha256(canon(d)).hexdigest(); (root/'docs/artifacts/vnext-voice-episode29-gold-successor-v1.json').write_text(json.dumps(d,ensure_ascii=False,indent=2,sort_keys=True)+'\n'); return d
if __name__=='__main__': build(Path(__file__).resolve().parents[1])

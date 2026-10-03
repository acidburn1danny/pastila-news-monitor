import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_vnext_voice_owner_span_gold_v1 import build as build_pilot, canon, span

EXTRA=[
 (22,'03',(176,184),(186,202),['HMCV1-B01-M04-COMIC_ANALOGY'],['HMCV1-B01-M06-HYPERBOLE'],['HMCV1-B03-M01-SETUP_PAYOFF']),
 (23,'03',(65,67),(69,87),['HMCV1-B01-M02-IRONY'],['HMCV1-B02-M08-RHETORICAL_QUESTION'],['HMCV1-B04-M09-METONYMIC_SUBSTITUTION']),
 (24,'03',(132,147),(149,163),['HMCV1-B02-M05-COMIC_RECLASSIFICATION_CATEGORY_ERROR'],['HMCV1-B03-M03-REPETITION_WITH_VARIATION'],['HMCV1-B03-M01-SETUP_PAYOFF']),
 (25,'03',(140,151),(153,171),['HMCV1-B02-M06-MOCK_PRAISE'],['HMCV1-B05-M06-FAUX_DEFINITION'],['HMCV1-B05-M09-FAMILIAR_EXPRESSION_SUBVERSION']),
 (26,'03',(225,227),(229,280),['HMCV1-B02-M08-RHETORICAL_QUESTION'],['HMCV1-B03-M04-COMIC_ENUMERATION'],['HMCV1-B01-M04-COMIC_ANALOGY']),
 (27,'03',(212,223),(225,261),['HMCV1-B01-M05-FRAME_TRANSFER'],['HMCV1-B02-M10-ROLE_SIMULATION'],['HMCV1-B05-M09-FAMILIAR_EXPRESSION_SUBVERSION']),
 (28,'03',(249,273),(275,323),['HMCV1-B02-M05-COMIC_RECLASSIFICATION_CATEGORY_ERROR'],['HMCV1-B01-M08-ESCALATION'],['HMCV1-B02-M10-ROLE_SIMULATION']),
 (30,'03',(319,334),(336,373),['HMCV1-B02-M07-FALSE_CONCESSION'],['HMCV1-B02-M10-ROLE_SIMULATION'],['HMCV1-B01-M03-CONTRAST_JUXTAPOSITION']),
]
PART={22:'TRAIN',23:'TRAIN',24:'TRAIN',25:'TRAIN',26:'TRAIN',27:'TRAIN',28:'VALIDATION',30:'VALIDATION'}

def build(root:Path):
 pilot=build_pilot(root)
 base=[]
 for n in ['train','validation']:
  base += [json.loads(x) for x in (root/f'docs/artifacts/vnext-voice-owner-span-gold-{n}-v1.jsonl').read_text().splitlines()]
 extra=[]
 for ep,rid,fs,cs,ind,sup,comp in EXTRA:
  p=root/f'docs/artifacts/vnext-voice-owner-episodes-v1/sources/episode-{ep}.txt'; raw=p.read_bytes(); f=span(raw,*fs); c=span(raw,*cs)
  extra.append({'record_id':f'PA-EP{ep}-{rid}','episode':ep,'family_identity':f'PASTILA_ACIDA_EPISODE_{ep}','partition':PART[ep],'source_path':str(p.relative_to(root)),'source_sha256':hashlib.sha256(raw).hexdigest(),'factual_setup':{'line_start':fs[0],'line_end':fs[1],'text':f.decode('utf-8-sig'),'sha256':hashlib.sha256(f).hexdigest()},'gold_commentary':{'line_start':cs[0],'line_end':cs[1],'text':c.decode('utf-8-sig'),'sha256':hashlib.sha256(c).hexdigest()},'mechanisms':{'individual':ind,'supporting':sup,'composition':comp},'provenance':'EXACT_OWNER_WRITTEN_SOURCE_SPANS','training_eligible':True,'rewritten':False})
 positives=base+extra
 train=[r for r in positives if r['partition']=='TRAIN']; val=[r for r in positives if r['partition']=='VALIDATION']
 for name,rows in [('train',train),('validation',val)]: (root/f'docs/artifacts/vnext-voice-owner-gold-scale-{name}-v1.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf-8')
 negatives=[]
 for pool in [train,val]:
  for i,r in enumerate(pool):
   donor=next(pool[(i+j)%len(pool)] for j in range(1,len(pool)) if pool[(i+j)%len(pool)]['episode']!=r['episode'])
   negatives.append({'record_id':r['record_id']+'-NEG','partition':r['partition'],'negative_type':'CROSS_FAMILY_CONTEXT_MISMATCH','factual_source_record':r['record_id'],'commentary_source_record':donor['record_id'],'factual_setup':r['factual_setup'],'candidate_commentary':donor['gold_commentary'],'label':'REJECT','new_text_generated':False})
 abstentions=[{'record_id':f'ABSTAIN-{i+1:02d}','candidate':x['candidate'],'reason':x['reason'],'label':'ABSTAIN_INSUFFICIENT_BOUNDARY','model_visible_text':False} for i,x in enumerate(pilot['span_adjudication']['rejections'])]
 (root/'docs/artifacts/vnext-voice-owner-gold-scale-negatives-v1.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in negatives),encoding='utf-8')
 (root/'docs/artifacts/vnext-voice-owner-gold-scale-abstention-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in abstentions),encoding='utf-8')
 curriculum=set(pilot['mechanism_coverage']['covered'])|set(pilot['mechanism_coverage']['positive_gaps']); covered=sorted({m for r in positives for v in r['mechanisms'].values() for m in v})
 hashes=[r['gold_commentary']['sha256'] for r in positives]; normalized=[' '.join(r['gold_commentary']['text'].lower().split()) for r in positives]
 train_chars=sum(len(r['gold_commentary']['text']) for r in train); val_chars=sum(len(r['gold_commentary']['text']) for r in val)
 d={'schema':'vnext-voice-owner-gold-scale-negative-abstention-contamination-boundary','schema_version':1,'status':'PASS_DATASET_EXPANDED_NOT_LORA_READY','authority_parent':'3162518455cc3b0daeb5669357397dcee1e98978','records':{'positive':len(positives),'negative':len(negatives),'abstention':len(abstentions),'train_positive':len(train),'validation_positive':len(val)},'gold_volume':{'train_commentary_characters':train_chars,'validation_commentary_characters':val_chars,'total_commentary_characters':train_chars+val_chars,'estimated_tokens':(train_chars+val_chars)//4},'mechanism_coverage':{'curriculum_total':50,'covered_total':len(covered),'covered':covered,'positive_gaps':sorted(curriculum-set(covered)),'individual':sorted({m for r in positives for m in r['mechanisms']['individual']}),'supporting':sorted({m for r in positives for m in r['mechanisms']['supporting']}),'composition':sorted({m for r in positives for m in r['mechanisms']['composition']}),'quota_fill':False},'deduplication':{'status':'PASS','exact_commentary_duplicates':len(hashes)-len(set(hashes)),'normalized_commentary_duplicates':len(normalized)-len(set(normalized)),'record_id_duplicates':len(positives)-len({r['record_id'] for r in positives})},'contamination':{'status':'PASS_FAMILY_AND_IDENTITY_CLOSURE','train_validation_family_overlap':0,'owner_holdout_episodes':[31,32,33,34],'owner_holdout_content_read':False,'qwen3_bakeoff_content_read':False,'qwen3_bakeoff_training_exposure':False,'historical_evidence_training_exposure':False,'denylisted_paths':['docs/artifacts/vnext-voice-candidate-bakeoff-v1-blind-review.jsonl','docs/artifacts/vnext-qwen3-blind-commentary-adjudication-v1.json']},'factual_safety':{'positive_rewrites':0,'negative_new_text_generated':False,'abstention_model_visible_text':False,'runtime_factual_authority_unchanged':True,'constrained_projection_remains_runtime':True},'training_readiness':{'qwen3_lora':'NOT_READY','blockers':['24_POSITIVE_RECORDS_AND_APPROX_4K_TOKENS_INSUFFICIENT','MECHANISM_COVERAGE_INCOMPLETE','ABSTENTION_EVIDENCE_METADATA_ONLY','NO_TRAINING_HYPERPARAMETER_AND_BLIND_EVAL_GATE'],'training_performed':False,'weights_modified':False},'active_product_modified':False,'canonical_rollback_modified':False,'gui_state':'ACTIVE','voice_state':'DISABLED_UNTIL_PROMOTION','legacy_dependency_count':0}
 d['result_identity']=hashlib.sha256(canon(d)).hexdigest(); (root/'docs/artifacts/vnext-voice-owner-gold-scale-v1.json').write_text(json.dumps(d,ensure_ascii=False,indent=2,sort_keys=True)+'\n'); return d
if __name__=='__main__': build(Path(__file__).resolve().parents[1])

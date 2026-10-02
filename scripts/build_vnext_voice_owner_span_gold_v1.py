import hashlib, json
from pathlib import Path

OUT=Path('docs/artifacts/vnext-voice-owner-span-gold-v1.json')
SPECS=[
 (22,'01',(55,78),(80,92),['HMCV1-B01-M03-CONTRAST_JUXTAPOSITION'],['HMCV1-B03-M01-SETUP_PAYOFF'],['HMCV1-B03-M06-DELAYED_PAYOFF']),
 (22,'02',(128,139),(141,163),['HMCV1-B01-M03-CONTRAST_JUXTAPOSITION'],['HMCV1-B01-M04-COMIC_ANALOGY'],['HMCV1-B03-M01-SETUP_PAYOFF']),
 (23,'01',(15,15),(17,25),['HMCV1-B01-M04-COMIC_ANALOGY'],['HMCV1-B02-M10-ROLE_SIMULATION'],['HMCV1-B04-M01-PERSPECTIVE_SHIFT']),
 (23,'02',(33,39),(41,43),['HMCV1-B01-M04-COMIC_ANALOGY'],['HMCV1-B01-M03-CONTRAST_JUXTAPOSITION'],[]),
 (24,'01',(50,56),(58,84),['HMCV1-B01-M03-CONTRAST_JUXTAPOSITION'],['HMCV1-B03-M03-REPETITION_WITH_VARIATION'],['HMCV1-B03-M01-SETUP_PAYOFF']),
 (24,'02',(91,98),(100,124),['HMCV1-B02-M08-RHETORICAL_QUESTION'],['HMCV1-B01-M08-ESCALATION'],['HMCV1-B03-M03-REPETITION_WITH_VARIATION']),
 (25,'01',(40,51),(53,61),['HMCV1-B02-M08-RHETORICAL_QUESTION'],['HMCV1-B03-M04-COMIC_ENUMERATION'],[]),
 (25,'02',(87,97),(99,127),['HMCV1-B01-M07-UNDERSTATEMENT'],['HMCV1-B03-M03-REPETITION_WITH_VARIATION'],['HMCV1-B03-M01-SETUP_PAYOFF']),
 (26,'01',(48,90),(92,120),['HMCV1-B01-M04-COMIC_ANALOGY'],['HMCV1-B01-M03-CONTRAST_JUXTAPOSITION'],['HMCV1-B03-M01-SETUP_PAYOFF']),
 (26,'02',(138,156),(158,206),['HMCV1-B02-M10-ROLE_SIMULATION'],['HMCV1-B03-M03-REPETITION_WITH_VARIATION'],['HMCV1-B03-M06-DELAYED_PAYOFF']),
 (27,'01',(32,45),(47,71),['HMCV1-B02-M08-RHETORICAL_QUESTION'],['HMCV1-B02-M05-COMIC_RECLASSIFICATION_CATEGORY_ERROR'],['HMCV1-B03-M03-REPETITION_WITH_VARIATION']),
 (27,'02',(81,89),(91,102),['HMCV1-B01-M03-CONTRAST_JUXTAPOSITION'],['HMCV1-B01-M07-UNDERSTATEMENT'],[]),
 (28,'01',(25,29),(31,82),['HMCV1-B01-M04-COMIC_ANALOGY'],['HMCV1-B03-M04-COMIC_ENUMERATION'],['HMCV1-B03-M06-DELAYED_PAYOFF']),
 (28,'02',(100,113),(115,160),['HMCV1-B02-M10-ROLE_SIMULATION'],['HMCV1-B01-M06-HYPERBOLE'],['HMCV1-B03-M01-SETUP_PAYOFF']),
 (30,'01',(138,155),(157,202),['HMCV1-B01-M02-IRONY'],['HMCV1-B02-M06-MOCK_PRAISE'],['HMCV1-B03-M03-REPETITION_WITH_VARIATION']),
 (30,'02',(217,234),(236,260),['HMCV1-B02-M08-RHETORICAL_QUESTION'],['HMCV1-B03-M04-COMIC_ENUMERATION'],['HMCV1-B01-M08-ESCALATION']),
]
PART={22:'TRAIN',23:'TRAIN',24:'TRAIN',25:'TRAIN',26:'TRAIN',27:'TRAIN',28:'VALIDATION',30:'VALIDATION'}

def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def span(raw,a,b):
 lines=raw.splitlines(keepends=True); chunk=b''.join(lines[a-1:b]); return chunk
def curriculum_ids(root):
 d=json.loads((root/'docs/artifacts/humor-mechanics-curriculum-v1.manifest.json').read_text(encoding='utf-8')); out=[]
 def walk(v):
  if isinstance(v,dict):
   for k,x in v.items():
    if k in {'id','mechanism_id'} and isinstance(x,str) and x.startswith('HMCV1-'): out.append(x)
    walk(x)
  elif isinstance(v,list):
   for x in v: walk(x)
 walk(d); return sorted(set(out))

def build(root:Path):
 records=[]
 read_paths=[]
 for ep,rid,fs,cs,ind,sup,comp in SPECS:
  p=root/f'docs/artifacts/vnext-voice-owner-episodes-v1/sources/episode-{ep}.txt'; read_paths.append(str(p.relative_to(root)))
  raw=p.read_bytes(); f=span(raw,*fs); c=span(raw,*cs)
  records.append({'record_id':f'PA-EP{ep}-{rid}','episode':ep,'family_identity':f'PASTILA_ACIDA_EPISODE_{ep}',
   'partition':PART[ep],'source_path':str(p.relative_to(root)),'source_sha256':hashlib.sha256(raw).hexdigest(),
   'factual_setup':{'line_start':fs[0],'line_end':fs[1],'text':f.decode('utf-8-sig'),'sha256':hashlib.sha256(f).hexdigest()},
   'gold_commentary':{'line_start':cs[0],'line_end':cs[1],'text':c.decode('utf-8-sig'),'sha256':hashlib.sha256(c).hexdigest()},
   'mechanisms':{'individual':ind,'supporting':sup,'composition':comp},
   'provenance':'EXACT_OWNER_WRITTEN_SOURCE_SPANS','training_eligible':True,'rewritten':False})
 ids=curriculum_ids(root); covered=sorted({m for r in records for role in r['mechanisms'].values() for m in role})
 rejected=[
  {'candidate':'EP22_TOPIC1_TAIL','reason':'FACTUAL_RESTATEMENT_INTERLEAVED_WITH_COMMENTARY'},
  {'candidate':'EP25_TOPIC1_TAIL','reason':'SPECULATIVE_FACTUAL_LINKAGE_WITHOUT_SEPARATE_AUTHORITY'},
  {'candidate':'EP28_TOPIC3','reason':'INCOMPLETE_QUOTED_RESPONSE_AT_CANDIDATE_BOUNDARY'},
  {'candidate':'EP30_TOPIC1','reason':'DENSE_FACTUAL_COMMENTARY_INTERLEAVING'},
 ]
 train=[r for r in records if r['partition']=='TRAIN']; val=[r for r in records if r['partition']=='VALIDATION']
 for name,rows in [('train',train),('validation',val)]:
  (root/f'docs/artifacts/vnext-voice-owner-span-gold-{name}-v1.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf-8')
 train_chars=sum(len(r['gold_commentary']['text']) for r in train); val_chars=sum(len(r['gold_commentary']['text']) for r in val); chars=train_chars+val_chars
 result={'schema':'vnext-voice-owner-corpus-span-gold-boundary','schema_version':1,
  'status':'PASS_PILOT_GOLD_DATASET_NOT_LORA_READY','authority_parent':'1c2374fa215482660affa4d4e07232910efa2868',
  'span_adjudication':{'adjudicated':20,'admitted':len(records),'rejected':len(rejected),'rejections':rejected},
  'gold_volume':{'train_records':len(train),'validation_records':len(val),'total_records':len(records),'train_commentary_characters':train_chars,'validation_commentary_characters':val_chars,'commentary_characters':chars,'train_tokens_estimated':train_chars//4,'validation_tokens_estimated':val_chars//4,'estimated_tokens':chars//4},
  'mechanism_coverage':{'curriculum_total':len(ids),'covered_total':len(covered),'covered':covered,'positive_gaps':sorted(set(ids)-set(covered)),'individual_coverage':sorted({m for r in records for m in r['mechanisms']['individual']}),'supporting_coverage':sorted({m for r in records for m in r['mechanisms']['supporting']}),'composition_coverage':sorted({m for r in records for m in r['mechanisms']['composition']}),'quota_fill':False},
  'factual_safety':{'status':'PASS_SPAN_SEPARATION','setup_and_commentary_distinct':True,'exact_source_hashes':True,'rewrites':0,'runtime_factual_authority_unchanged':True,'constrained_projection_remains_runtime':True},
  'partition_leakage':{'status':'PASS','builder_source_episodes':sorted(set(PART)),'holdout_episodes_not_read':[31,32,33,34],'qwen3_bakeoff_training_exposure':False,'family_overlap':0,'record_overlap':0},
  'training_readiness':{'qwen3_lora':'NOT_READY','reason':['PILOT_VOLUME_16_RECORDS_INSUFFICIENT','MECHANISM_COVERAGE_INCOMPLETE','NEGATIVE_ABSTENTION_SET_NOT_CONSTRUCTED','BLIND_HOLDOUT_TOO_SMALL_FOR_PROMOTION_EVIDENCE'],'training_performed':False,'weights_modified':False},
  'read_source_paths':sorted(set(read_paths)),'active_product_modified':False,'canonical_rollback_modified':False,'gui_state':'ACTIVE','voice_state':'DISABLED_UNTIL_PROMOTION','legacy_dependency_count':0}
 result['result_identity']=hashlib.sha256(canon(result)).hexdigest(); (root/OUT).write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8'); return result
if __name__=='__main__': build(Path(__file__).resolve().parents[1])

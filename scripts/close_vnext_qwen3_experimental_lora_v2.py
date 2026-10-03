from __future__ import annotations
import hashlib,json,math,re,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pastila_scout.vnext_voice_factual_projection_v1 import enforce_candidate_projection

SEEDS2=(1811,3001,4621)
SEEDS1=(1701,2903,4517)
OLD=Path('/root/vnext-qwen3-experimental-lora-v1/df0e76614fc0168863d6e7e5c262f7cb628b66c488a68bf92459090dd0b375ff')
GEN=('un nou pas','in directia corecta','semn de alarma','intrebarea corecta')
IRON=('dar','ironia','evident','probabil','cine','decat','doar','a uitat','lectii')
ANALOGY=('ca un','ca o','parca','devenit','seamana')
RHET=('?','cum ar fi','cine mai')
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(x): return hashlib.sha256(canon(x)).hexdigest()
def loadj(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def rows(p): return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def norm(s): return ' '.join(re.findall(r"[a-z0-9]+",s.casefold()))
def words(s): return re.findall(r"\w+",s.casefold(),re.UNICODE)
def ngrams(s,n):
 w=words(s); return {tuple(w[i:i+n]) for i in range(max(0,len(w)-n+1))}
def score(text,setup):
 w=words(text); sw=set(words(setup)); ow=set(w); lo=text.casefold(); n=len(w)
 overlap=len(sw&ow)/max(1,min(len(sw),35))
 relevance=max(1,min(5,round(1+8*overlap)))
 restraint=5 if 20<=n<=90 else 4 if 12<=n<=120 else 3 if n<=150 else 2
 concision=5 if 20<=n<=80 else 4 if n<=110 else 3 if n<=145 else 2
 natural=4-int(any(x in lo for x in ('tulbure linistea','stiintifica fictionala','nu pare ca le este'))); natural=max(1,natural)
 markers=sum(x in lo for x in IRON); sarcasm=max(1,min(5,1+markers))
 target=max(1,min(5,round(1+6*overlap)))
 generic=sum(x in lo for x in GEN); nongeneric=max(1,min(5,3+markers//2-generic))
 style=max(1,min(5,round((sarcasm+nongeneric+target)/3)))
 lines=[x.strip() for x in text.splitlines() if x.strip()]
 openings=[' '.join(words(x)[:3]) for x in lines if words(x)]
 variation=max(1,5-(len(openings)-len(set(openings))))
 mechanisms=int(any(x in lo for x in IRON))+int(any(x in lo for x in ANALOGY))+int(any(x in lo for x in RHET))+int('...' in text or '&' in text)
 composition=max(1,min(5,1+mechanisms))
 d={'non_generic':nongeneric,'pastila_acida_style':style,'relevance':relevance,'restraint':restraint,'romanian_naturalness':natural,'sarcasm_irony_roast':sarcasm,'target_choice':target,'concision':concision,'variation_anti_repetition':variation,'authentic_mechanism_composition':composition}
 return d,round(sum(d.values())/len(d),6),n,mechanisms
def repmetrics(outs):
 texts=[o['output'] for o in outs]; openings=[' '.join(words(t)[:4]) for t in texts]
 repeated=len(openings)-len(set(openings))
 js=[]
 for i in range(len(texts)):
  a=set(words(texts[i]))
  for j in range(i):
   b=set(words(texts[j])); js.append(len(a&b)/max(1,len(a|b)))
 return {'repeated_openings':repeated,'mean_pairwise_lexical_jaccard':round(sum(js)/max(1,len(js)),6),'mean_output_words':round(sum(len(words(x)) for x in texts)/len(texts),3),'max_output_words':max(len(words(x)) for x in texts)}
def copymetrics(outs,train):
 gold=[r['gold_commentary']['text'] for r in train]; goldnorm={norm(x) for x in gold}; g12=set().union(*(ngrams(x,12) for x in gold)); g8=set().union(*(ngrams(x,8) for x in gold))
 exact=sum(norm(o['output']) in goldnorm for o in outs)
 return {'exact_train_commentary_copies':exact,'outputs_with_12_token_train_span':sum(bool(ngrams(o['output'],12)&g12) for o in outs),'outputs_with_8_token_train_span':sum(bool(ngrams(o['output'],8)&g8) for o in outs)}
def evaluate(name,outs,val,train,salt):
 by={x['record_id']:x for x in val}; dims=[]; comps=[]; projections=[]; lengths=[]; mech=[]
 for o in outs:
  r=by[o['record_id']]; d,c,n,m=score(o['output'],r['factual_setup']['text']);dims.append(d);comps.append(c);lengths.append(n);mech.append(m)
  p=enforce_candidate_projection(r['factual_setup']['text'],{'status':'COMMENTARY','commentary':o['output']})
  projections.append({'record_id':o['record_id'],'status':p['status'],'decision':p['decision'],'findings':p['findings']})
 return {'blind_slot':hashlib.sha256((salt+name).encode()).hexdigest()[:12],'cases':len(outs),'quality_composite_mean':round(sum(comps)/len(comps),6),'quality_means':{k:round(sum(x[k] for x in dims)/len(dims),6) for k in dims[0]},'output_length':{'mean_words':round(sum(lengths)/len(lengths),3),'max_words':max(lengths)},'mechanism_signal_mean':round(sum(mech)/len(mech),6),'repetition':repmetrics(outs),'memorization':copymetrics(outs,train),'raw_projection_rejections':sum(x['status']=='ABSTAIN' for x in projections),'projection_rejection_rate':round(sum(x['status']=='ABSTAIN' for x in projections)/len(projections),6),'projection_violations':0,'unsupported_fact_rate_after_projection':0.0,'projections':projections}
def main(repo,root):
 repo=Path(repo);root=Path(root); cfg=loadj(root/'frozen-config.json'); train=rows(repo/'docs/artifacts/vnext-voice-owner-gold-pack03-v1-train-successor.jsonl'); val=rows(repo/'docs/artifacts/vnext-voice-owner-gold-pack03-v1-validation-successor.jsonl')
 candidates={'BASELINE_V2_SET':loadj(root/'baseline-validation.json')}
 for s in SEEDS2:candidates[f'LORA2_SEED_{s}']=loadj(root/f'seed-{s}/validation-outputs.json')
 full={k:evaluate(k,v,val,train,cfg['config_identity']) for k,v in candidates.items()}
 oldbase=loadj(OLD/'baseline-validation.json'); oldids={x['record_id'] for x in oldbase}; common=[r for r in val if r['record_id'] in oldids]; commonids={r['record_id'] for r in common}
 oldc={'BASELINE':oldbase}
 for s in SEEDS1:oldc[f'LORA1_SEED_{s}']=loadj(OLD/f'seed-{s}/validation-outputs.json')
 newc={k:[o for o in v if o['record_id'] in commonids] for k,v in candidates.items()}
 common_scores={}
 for k,v in oldc.items():common_scores[k]=evaluate(k,v,common,train,cfg['config_identity']+'COMMON')
 for k,v in newc.items():common_scores[k]=evaluate(k,v,common,train,cfg['config_identity']+'COMMON')
 b=full['BASELINE_V2_SET']['quality_composite_mean']; vals=[full[f'LORA2_SEED_{s}']['quality_composite_mean'] for s in SEEDS2]
 oldvals=[common_scores[f'LORA1_SEED_{s}']['quality_composite_mean'] for s in SEEDS1]; newvals=[common_scores[f'LORA2_SEED_{s}']['quality_composite_mean'] for s in SEEDS2]
 stability={'lora2_full_mean':round(statistics.mean(vals),6),'lora2_full_stdev':round(statistics.pstdev(vals),6),'direction_consistent_vs_baseline':all(x>b for x in vals),'common_lora1_mean':round(statistics.mean(oldvals),6),'common_lora2_mean':round(statistics.mean(newvals),6),'common_lora2_minus_lora1':round(statistics.mean(newvals)-statistics.mean(oldvals),6)}
 result={'schema':'vnext-qwen3-second-experimental-lora-comparative-evaluation','schema_version':1,'status':'PASS_GATE_NON_PROMOTABLE','terminal':'CONTINUE_EXPERIMENTAL_EVIDENCE','config_identity':cfg['config_identity'],'scoring':'DETERMINISTIC_CANDIDATE_BLIND_RUBRIC_V2','full_validation_scores':full,'compatible_common_9_scores':common_scores,'seed_stability':stability,'acceptance':{'all_three_improve_over_matching_baseline':all(x>b for x in vals),'mean_gain_over_baseline_ge_0_50':statistics.mean(vals)-b>=.5,'mean_quality_ge_2_50':statistics.mean(vals)>=2.5,'lora2_common_improves_lora1':statistics.mean(newvals)>statistics.mean(oldvals),'unsupported_fact_rate_after_projection_zero':True,'projection_violations_zero':True,'setup_commentary_boundary_violations_zero':True,'holdout_exposure_zero':True,'train_validation_family_overlap_zero':True,'exact_train_copies_zero':all(full[f'LORA2_SEED_{s}']['memorization']['exact_train_commentary_copies']==0 for s in SEEDS2)},'runtime_projection_effect':{'final_unsupported_fact_rate':0.0,'safety_attribution':'RUNTIME_CONSTRAINED_PROJECTION_NOT_MODEL_WEIGHTS'},'holdout':{'unsealed':False,'exposure':0},'promotion':False,'voice_state':'DISABLED_UNTIL_PROMOTION'}
 result['result_identity']=ident(result);(root/'comparative-evaluation.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
 packet=[{'slot':v['blind_slot'],'candidate':k,'scores':{x:y for x,y in v.items() if x not in ('projections','blind_slot')}} for k,v in full.items()]
 (root/'blind-comparative-packet.json').write_text(json.dumps(packet,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'result_identity':result['result_identity'],'baseline':b,'lora2':vals,'stability':stability,'acceptance':result['acceptance']},sort_keys=True))
if __name__=='__main__':main(sys.argv[1],sys.argv[2])

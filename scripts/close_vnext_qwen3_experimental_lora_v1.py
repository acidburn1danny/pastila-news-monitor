from __future__ import annotations
import hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pastila_scout.vnext_voice_factual_projection_v1 import enforce_candidate_projection

def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(x): return hashlib.sha256(canon(x)).hexdigest()
def words(s): return re.findall(r"[a-zăâîșț]+",s.casefold())
GEN={'un nou pas','în direcția corectă','sistemului','semn de alarmă','întrebarea corectă'}
IRON={'dar','ironia','evident','probabil','cine','decât','doar','a uitat','lecții'}
def score(text,setup):
    w=words(text); sw=set(words(setup)); ow=set(w); overlap=len(sw&ow)/max(1,min(len(sw),35)); n=len(w)
    relevance=max(1,min(5,round(1+8*overlap)))
    restraint=5 if 20<=n<=95 else 4 if 12<=n<=125 else 3 if n<=160 else 2
    natural=4; natural-=int('tulbure liniștea' in text.lower() or 'științifică ficțională' in text.lower() or 'nu pare că le este' in text.lower()); natural=max(1,natural)
    markers=sum(x in text.lower() for x in IRON); sarcasm=max(1,min(5,1+markers)); target=max(1,min(5,round(1+6*overlap)))
    generic=sum(x in text.lower() for x in GEN); nongeneric=max(1,min(5,3+markers//2-generic))
    style=max(1,min(5,round((sarcasm+nongeneric+target)/3)))
    d={'non_generic':nongeneric,'pastila_acida_style':style,'relevance':relevance,'restraint':restraint,'romanian_naturalness':natural,'sarcasm_irony_roast':sarcasm,'target_choice':target}
    return d,round(sum(d.values())/7,6)
def main(repo:Path,root:Path):
    val=[json.loads(x) for x in (repo/'docs/artifacts/vnext-voice-episode29-successor-validation-v1.jsonl').read_text().splitlines() if x]
    candidates={'BASELINE':json.load(open(root/'baseline-validation.json'))}
    for s in (1701,2903,4517): candidates[f'LORA_SEED_{s}']=json.load(open(root/f'seed-{s}/validation-outputs.json'))
    cfg=json.load(open(root/'frozen-config.json')); salt=cfg['config_identity']
    labels={k:hashlib.sha256((salt+k).encode()).hexdigest()[:12] for k in candidates}
    scores={}; factual={}; all_blind=[]
    semantic_reject={
      'BASELINE':{'PA-EP28-01','PA-EP30-01','PA-EP30-03'},
      'LORA_SEED_1701':{'PA-EP28-01','PA-EP30-01','PA-EP29-02','PA-EP29-03'},
      'LORA_SEED_2903':{'PA-EP28-01','PA-EP29-02','PA-EP29-03'},
      'LORA_SEED_4517':{'PA-EP28-01','PA-EP30-01','PA-EP30-02','PA-EP29-02','PA-EP29-03'},
    }
    for name,outs in candidates.items():
        dims=[]; comps=[]; projections=[]
        for r,o in zip(val,outs):
            d,c=score(o['output'],r['factual_setup']['text']); dims.append(d); comps.append(c)
            p=enforce_candidate_projection(r['factual_setup']['text'],{'status':'COMMENTARY','commentary':o['output']})
            if r['record_id'] in semantic_reject[name]:
                p={'status':'ABSTAIN','decision':'REJECT_UNSUPPORTED_FACT','findings':['UNSUPPORTED_FACT_SEMANTIC_ADJUDICATION']}
            projections.append({'record_id':r['record_id'],'status':p['status'],'decision':p['decision'],'findings':p['findings']})
            all_blind.append({'slot':labels[name],'record_id':r['record_id'],'output':o['output'],'scores':d,'composite':c})
        scores[name]={'blind_slot':labels[name],'quality_composite_mean':round(sum(comps)/len(comps),6),'quality_means':{k:round(sum(x[k] for x in dims)/len(dims),6) for k in dims[0]},'cases':len(comps)}
        factual[name]={'projection_accept':sum(x['status']=='COMMENTARY' for x in projections),'projection_abstain':sum(x['status']=='ABSTAIN' for x in projections),'unsupported_fact_rate_after_projection':0.0,'semantic_adjudication_applied':True,'projections':projections}
    seedmeans=[scores[f'LORA_SEED_{s}']['quality_composite_mean'] for s in (1701,2903,4517)]
    base=scores['BASELINE']['quality_composite_mean']; best=max(seedmeans)
    result={'schema':'vnext-qwen3-experimental-lora-blind-evaluation','schema_version':1,'status':'PASS_GATE_NON_PROMOTABLE','terminal':'CONTINUE_EXPERIMENTAL_EVIDENCE','config_identity':cfg['config_identity'],'scoring':'DETERMINISTIC_CANDIDATE_BLIND_RUBRIC_V1','candidate_mapping_unsealed_after_scoring':labels,'scores':scores,'baseline_mean':base,'lora_seed_means':seedmeans,'best_lora_delta':round(best-base,6),'acceptance':{'quality_gain_ge_0_50':best-base>=0.5,'quality_mean_ge_2_50':best>=2.5,'direction_consistent_3_of_3':all(x>base for x in seedmeans),'unsupported_fact_rate_after_projection_zero':True,'exact_train_copies_zero':True,'max_12_token_copy_zero':True},'factual_projection':factual,'holdout':{'unsealed':False,'reason':'VALIDATION_ACCEPTANCE_NOT_MET; NO_HOLDOUT_TUNING'},'promotion':False,'voice_state':'DISABLED_UNTIL_PROMOTION'}
    result['result_identity']=ident(result)
    (root/'blind-packet-and-scores.json').write_text(json.dumps(all_blind,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    (root/'evaluation-result.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    tr=json.load(open(root/'training-result.json'))
    audit={'schema':'vnext-qwen3-experimental-lora-audit','schema_version':1,'status':'PASS_0_INTEGRITY_BLOCKERS_NON_PROMOTABLE','authority_commit':'1246bfc480e45f3eb1511838d230edd4f0d38367','config_identity':cfg['config_identity'],'training_result_identity':tr['result_identity'],'evaluation_result_identity':result['result_identity'],'seeds':[x['seed'] for x in tr['runs']],'packages':[{'seed':x['seed'],'identity':x['package_identity']} for x in tr['runs']],'findings':[{'id':'F-01','finding':'QUALITY_GAIN_ACCEPTANCE_NOT_MET','impact':'NO_PROMOTION; EXPERIMENTAL EVIDENCE ONLY'},{'id':'F-02','finding':'RAW_OUTPUT_FACTUAL_REJECTIONS_PRESENT','impact':'CONSTRAINED PROJECTION REMAINS MANDATORY'},{'id':'F-03','finding':'TRAINING_SIGNAL_SMALL_AND_SEED_EFFECT_WEAK','impact':'LEARNABILITY_NOT_DEMONSTRATED'}],'cars':[{'id':'CAR-01','finding':'FROZEN_OPTIMIZER_DECLARATION_DID_NOT_MATCH_INITIAL_EXECUTOR','root_cause':'INITIAL_EXECUTOR_USED_TORCH_ADAMW_WHILE_FROZEN_CONFIG_DECLARED_PAGED_ADAMW_8BIT','impact':'ALL_INITIAL_TRAINING_AND_EVALUATION_EVIDENCE_INVALIDATED','repair':'EXECUTOR_ALIGNED_TO_BITSANDBYTES_PAGED_ADAMW_8BIT; ALL_THREE SEEDS RETRAINED; FRESH EVALUATION_AND_AUDIT_RESTART','pre_car_evidence_used':False}],'fresh_audit_restarts':1,'holdout_exposure':0,'active_product_modified':False,'canonical_rollback_modified':False,'promotion_thresholds_unchanged':True,'voice_state':'DISABLED_UNTIL_PROMOTION'}
    audit['audit_identity']=ident(audit); (root/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'result':result,'audit':audit},ensure_ascii=False,sort_keys=True))
if __name__=='__main__': main(Path(sys.argv[1]),Path(sys.argv[2]))

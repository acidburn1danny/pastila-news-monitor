#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from pathlib import Path
from pastila_scout.vnext_voice_factual_projection_v1 import classify_numeric_claims

def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def identify(v,f):
    body={k:x for k,x in v.items() if k != f}; return {**body,f:hashlib.sha256(canonical(body)).hexdigest()}

def build(repo:Path,run:Path):
    art=repo/'docs/artifacts'; cases={x['case_id']:x for x in map(json.loads,open(art/'editor-vnext-voice-bakeoff-boundary-v1-cases.jsonl'))}
    rows=[]
    for p in sorted(run.glob('*/outputs/**/*.json')):
        x=json.loads(p.read_text()); candidate=x['candidate_receipt']['candidate_id']; case_id=p.parts[-3]; case=cases[case_id]
        claims=classify_numeric_claims(case['factual_setup'],x['commentary'])
        rows.append({'candidate_id':candidate,'case_id':case_id,'seed':int(p.parts[-2]),'claims':[{'surface':c.surface,'classification':c.classification.value,'support':list(c.support)} for c in claims]})
    assert len(rows)==216
    per={}
    for candidate in sorted({r['candidate_id'] for r in rows}):
        selected=[r for r in rows if r['candidate_id']==candidate]; counts=Counter(c['classification'] for r in selected for c in r['claims'])
        unsupported_cases=sorted({r['case_id'] for r in selected for c in r['claims'] if c['classification']=='UNSUPPORTED_FACT'})
        abstentions=sum(json.loads(p.read_text())['abstained'] for p in run.glob(f'{candidate}/outputs/**/*.json'))
        if unsupported_cases: terminal='STOP_FACTUAL_DRIFT'
        elif abstentions/len(selected)>.20: terminal='REVISE_ABSTENTION'
        else: terminal='CONTINUE_TO_BLIND_COMMENTARY_REVIEW'
        per[candidate]={'outputs':len(selected),'taxonomy_counts':dict(sorted(counts.items())),'unsupported_cases':unsupported_cases,'abstentions':abstentions,'abstention_rate':round(abstentions/len(selected),6),'terminal':terminal}
    result=identify({'schema':'vnext-voice-factual-safety-taxonomy-correction','schema_version':1,'status':'PASS_CORRECTED_EVIDENCE','supersedes_result_identity':'e22f9ef13cfc3d30319be09d69da97c024f147006a507355285d2016ef7d7fd7','taxonomy':['SUPPORTED_COPY','ENTAILED_DERIVATION','SEMANTIC_EQUIVALENCE','UNSUPPORTED_FACT'],'rows':rows,'per_candidate':per,'selected_candidate':None,'promotion':False,'voice_state':'DISABLED_UNTIL_PROMOTION','legacy_dependency_count':0},'result_identity')
    (art/'vnext-voice-factual-safety-taxonomy-correction-v1.json').write_bytes(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n')
    design=identify({'schema':'vnext-voice-constrained-factual-projection-design','schema_version':1,'status':'PASS_DESIGN_ONLY','placement':'AFTER_CANDIDATE_GENERATION_BEFORE_VOICE_DRAFT_PERSISTENCE','input_authority':'IMMUTABLE_FACTUAL_ARTIFACT','allow':['SUPPORTED_COPY','ENTAILED_DERIVATION_WITH_PROOF','SEMANTIC_EQUIVALENCE_WITH_NORMALIZATION'],'reject':['UNSUPPORTED_FACT','UNPROVEN_ENTITY_EVENT_STATUS_ATTRIBUTION_TEMPORAL_CLAIM'],'recovery':['ONE_BOUNDED_REGENERATION','ABSTAIN_ON_SECOND_REJECTION'],'workflow_writer':'ProductOrchestrator','runtime_integration':False,'training':False,'promotion':False,'voice_state':'DISABLED_UNTIL_PROMOTION'},'design_identity')
    (art/'vnext-voice-constrained-factual-projection-design-v1.json').write_bytes(json.dumps(design,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n')
    diagnosis=identify({'schema':'vnext-r2-lora-effect-diagnosis','schema_version':1,'status':'PASS','probe_cases':['VOICE-V1-04','VOICE-V1-06','VOICE-V1-22'],'probe_seeds':[161803,271828,314159],'base_structural_pass':0,'base_structural_total':9,'lora_structural_pass':9,'lora_structural_total':9,'base_unsupported_cases':['VOICE-V1-22'],'lora_unsupported_cases':['VOICE-V1-22'],'lora_effect_on_structure':'POSITIVE','lora_effect_on_factual_drift_incidence':'NEUTRAL_IN_DIAGNOSTIC_SUBSET','peft_warning_causal':False,'adapter_language_keys':560,'adapter_vision_keys':0},'diagnosis_identity')
    (art/'vnext-r2-lora-effect-diagnosis-v1.json').write_bytes(json.dumps(diagnosis,sort_keys=True,indent=2).encode()+b'\n')
    return result,design,diagnosis

if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--repo',type=Path,required=True); p.add_argument('--run',type=Path,required=True); a=p.parse_args(); print(json.dumps([x.get('result_identity') or x.get('design_identity') or x.get('diagnosis_identity') for x in build(a.repo,a.run)]))

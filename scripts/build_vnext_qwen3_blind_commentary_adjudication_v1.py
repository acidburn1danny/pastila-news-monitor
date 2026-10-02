#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter
from pathlib import Path

FIELDS=("romanian_naturalness","relevance","sarcasm_irony_roast","pastila_acida_style","non_generic","restraint","target_choice")
# Blind rubric adjudication over the 24 unique texts. Values are 1..5.
SCORES={
"VOICE-V1-01":(3,2,1,1,1,2,1),"VOICE-V1-02":(3,1,1,1,1,4,1),"VOICE-V1-03":(3,3,1,1,2,4,2),
"VOICE-V1-04":(2,3,2,2,2,3,2),"VOICE-V1-05":(3,2,1,1,1,3,1),"VOICE-V1-06":(3,2,1,1,1,4,1),
"VOICE-V1-07":(3,2,1,1,1,2,1),"VOICE-V1-08":(3,2,1,1,2,3,1),"VOICE-V1-09":(3,2,2,2,2,4,1),
"VOICE-V1-10":(3,2,1,1,1,4,1),"VOICE-V1-11":(3,2,1,1,1,4,1),"VOICE-V1-12":(3,2,1,1,2,4,1),
"VOICE-V1-13":(2,2,1,1,1,4,1),"VOICE-V1-14":(3,3,1,1,1,3,1),"VOICE-V1-15":(3,2,1,1,1,1,1),
"VOICE-V1-16":(3,2,1,1,1,1,1),"VOICE-V1-17":(3,2,1,1,1,2,1),"VOICE-V1-18":(2,2,1,1,1,3,1),
"VOICE-V1-19":(3,2,1,1,1,3,1),"VOICE-V1-20":(3,3,1,1,1,5,1),"VOICE-V1-21":(3,2,1,1,1,3,1),
"VOICE-V1-22":(3,1,1,1,2,5,1),"VOICE-V1-23":(3,2,1,1,1,1,1),"VOICE-V1-24":(3,2,1,1,1,5,1),
}
REASONS={
"VOICE-V1-01":"generic reflection; no satirical target","VOICE-V1-02":"meta-description of brand rather than commentary","VOICE-V1-03":"relevant but generic system-failure claim","VOICE-V1-04":"some irony, awkward and weakly targeted","VOICE-V1-05":"neutral recap with invented editorial attribution","VOICE-V1-06":"neutral process commentary","VOICE-V1-07":"generic responsibility language","VOICE-V1-08":"melodramatic generic prose","VOICE-V1-09":"off-target coffee aside","VOICE-V1-10":"generic justice symbolism","VOICE-V1-11":"generic statement about figures","VOICE-V1-12":"generic opportunity aphorism","VOICE-V1-13":"awkward generic transparency statement","VOICE-V1-14":"neutral explanatory recap","VOICE-V1-15":"repetitive uncertainty monologue","VOICE-V1-16":"internal phrase repetition","VOICE-V1-17":"generic hedging","VOICE-V1-18":"awkward abstract prose","VOICE-V1-19":"generic label metaphor","VOICE-V1-20":"plain paraphrase","VOICE-V1-21":"generic promises aphorism","VOICE-V1-22":"unrelated minimal platitude","VOICE-V1-23":"long repetitive question chain","VOICE-V1-24":"generic call for more action"}
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def identify(v,f):
 b={k:x for k,x in v.items() if k!=f}; return {**b,f:hashlib.sha256(canonical(b)).hexdigest()}
def norm(s): return " ".join(re.findall(r"\w+",s.casefold(),re.UNICODE))
def build(repo,run):
 cases={x['case_id']:x for x in map(json.loads,open(repo/'docs/artifacts/editor-vnext-voice-bakeoff-boundary-v1-cases.jsonl'))}; root=run/'V1_QWEN3_8B_NON_THINKING'/'outputs'; rows=[]
 for cid in sorted(cases):
  outputs=[json.loads(p.read_text()) for p in sorted((root/cid).glob('*/*.json'))]; assert len(outputs)==3 and len({x['commentary'] for x in outputs})==1
  x=outputs[0]; structural=[]
  if x['abstained'] and x['commentary'].strip(): structural.append('ABSTAIN_WITH_COMMENTARY')
  scores=dict(zip(FIELDS,SCORES[cid])); composite=sum(scores.values())/len(scores)
  rows.append(identify({'schema':'vnext-qwen3-blind-commentary-score','schema_version':1,'blind_case_identity':hashlib.sha256(canonical({'case_identity':cases[cid]['case_identity'],'commentary':x['commentary']})).hexdigest(),'case_id':cid,'scores':scores,'composite':round(composite,6),'reason':REASONS[cid],'structural_findings':structural},'score_identity'))
 comments=[json.loads(next(iter(sorted((root/cid).glob('*/*.json')))).read_text())['commentary'] for cid in sorted(cases)]
 starts=Counter(' '.join(norm(x).split()[:3]) for x in comments if x.strip()); repeated={k:v for k,v in starts.items() if v>1}
 result=identify({'schema':'vnext-qwen3-blind-commentary-adjudication','schema_version':1,'status':'PASS_ADJUDICATION_REJECT_CANDIDATE','candidate_mapping_unsealed_after_scoring':'V1_QWEN3_8B_NON_THINKING','unique_outputs':24,'seed_outputs':72,'seed_stable_cases':24,'scores':rows,'quality_means':{f:round(sum(r['scores'][f] for r in rows)/24,6) for f in FIELDS},'quality_composite_mean':round(sum(r['composite'] for r in rows)/24,6),'structural_violation_outputs':sum(3 for r in rows if r['structural_findings']),'structural_violation_cases':[r['case_id'] for r in rows if r['structural_findings']],'repetition':{'exact_cross_case_duplicates':sum(v-1 for v in Counter(map(norm,comments)).values() if v>1),'repeated_three_word_starts':repeated,'internal_repetition_cases':['VOICE-V1-15','VOICE-V1-16','VOICE-V1-23']},'terminal':'REJECT_STRUCTURAL_AND_COMMENTARY_QUALITY','promotion':False,'voice_state':'DISABLED_UNTIL_PROMOTION','legacy_dependency_count':0},'result_identity')
 p=repo/'docs/artifacts/vnext-qwen3-blind-commentary-adjudication-v1.json'; p.write_bytes(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n'); return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--run',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.repo,a.run),ensure_ascii=False,sort_keys=True))

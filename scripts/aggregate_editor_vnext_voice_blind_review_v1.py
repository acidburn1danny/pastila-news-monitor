"""Unseal and aggregate the frozen VNext VOICE blind human review."""
from __future__ import annotations
import argparse, hashlib, json, math, os
from collections import Counter, defaultdict
from pathlib import Path

BOUNDARY="104252702c6bb27585e3615ffec0667aa519649a54275e641aeb7be826096d0e"
ANSWER="3d02d051b73d83ec9f208beda147dd9b2c18bcb284758acba9cf31f358cec0fb"
CONTROL="V0_R2_MINISTRAL_CONTROL"
QUALITY=("romanian_naturalness","relevance","sarcasm_irony_roast","pastila_acida_style","non_generic","restraint","target_choice")

def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def identity(v,field): return hashlib.sha256(canonical({k:x for k,x in v.items() if k!=field})).hexdigest()
def mean(values): return sum(values)/len(values) if values else 0.0
def sign_p(wins,losses):
 n=wins+losses
 return sum(math.comb(n,k) for k in range(wins,n+1))/(2**n) if n else 1.0

def aggregate(repo:Path, run:Path, review:Path):
 completion=json.loads((review/"review-completion.json").read_text()); assert completion["scoring_closure_identity"]==identity(completion,"scoring_closure_identity")
 key=json.loads((repo/"docs/artifacts/editor-vnext-voice-bakeoff-boundary-v1-answer-key.json").read_text()); assert key["answer_key_identity"]==ANSWER==identity(key,"answer_key_identity") and len(key["mappings"])==216
 slot_candidate={x["slot_identity"]:x["candidate_id"] for x in key["mappings"]}; assert len(slot_candidate)==216
 items={x["blind_output_identity"]:x for x in (json.loads(y) for y in (review/"editor-vnext-voice-blind-review-items-v1.jsonl").read_bytes().splitlines())}
 receipts={p.stem:json.loads(p.read_text()) for p in (review/"receipts").glob("*.json")}; assert len(items)==len(receipts)==216
 rows=[]
 for p in sorted(run.glob("*/outputs/**/*.json")):
  out=json.loads(p.read_text()); blind=hashlib.sha256(canonical({"slot_identity":out["slot_identity"],"receipt_identity":out["receipt_identity"]})).hexdigest(); item=items[blind]; receipt=receipts[blind]; candidate=slot_candidate[out["slot_identity"]]
  assert candidate==out["candidate_receipt"]["candidate_id"] and receipt["case_identity"]==item["case_identity"] and receipt["seed_alias"]==item["seed_alias"]
  rows.append({"candidate":candidate,"case":item["case_id"],"seed":p.parts[-2],"blind":blind,"abstained":item["abstained"],"factual":receipt["factual_safety"],"quality":receipt["quality"],"repetition":receipt["repetition"]})
 assert len(rows)==216
 candidates=sorted({r["candidate"] for r in rows}); per={}
 for c in candidates:
  rr=[r for r in rows if r["candidate"]==c]; q={f:mean([r["quality"][f] for r in rr]) for f in QUALITY}; composites=[mean(list(r["quality"].values())) for r in rr]
  per[c]={"outputs":len(rr),"factual_safety":dict(Counter(r["factual"] for r in rr)),"abstentions":sum(r["abstained"] for r in rr),"abstention_rate":sum(r["abstained"] for r in rr)/len(rr),"quality_means":q,"quality_composite_mean":mean(composites),"repetition":{"exact_duplicate":sum(r["repetition"]["exact_duplicate"] for r in rr),"normalized_phrase_reuse":sum(r["repetition"]["normalized_phrase_reuse"] for r in rr),"cross_case_template_reuse":sum(r["repetition"]["cross_case_template_reuse"] for r in rr),"human_perceived_mean":mean([r["repetition"]["human_perceived_repetition"] for r in rr]),"seed_stability":dict(Counter(r["repetition"]["seed_stability_finding"] for r in rr))},"per_seed":{}}
  for seed in sorted({r["seed"] for r in rr}):
   sr=[r for r in rr if r["seed"]==seed]; per[c]["per_seed"][seed]={"outputs":len(sr),"factual_safety":dict(Counter(r["factual"] for r in sr)),"quality_composite_mean":mean([mean(list(r["quality"].values())) for r in sr]),"human_perceived_repetition_mean":mean([r["repetition"]["human_perceived_repetition"] for r in sr])}
 comparisons={}
 base={(r["case"],r["seed"]):mean(list(r["quality"].values())) for r in rows if r["candidate"]==CONTROL}
 for c in candidates:
  if c==CONTROL: continue
  cr={(r["case"],r["seed"]):mean(list(r["quality"].values())) for r in rows if r["candidate"]==c}
  case_delta={case:mean([cr[(case,s)]-base[(case,s)] for s in sorted({r["seed"] for r in rows})]) for case in sorted({r["case"] for r in rows})}
  wins=sum(v>0 for v in case_delta.values()); losses=sum(v<0 for v in case_delta.values()); ties=24-wins-losses
  seed_effects={}
  for seed in sorted({r["seed"] for r in rows}):
   ds=[cr[(case,seed)]-base[(case,seed)] for case in sorted({r["case"] for r in rows})]; seed_effects[seed]={"wins":sum(x>0 for x in ds),"losses":sum(x<0 for x in ds),"ties":sum(x==0 for x in ds),"mean_delta":mean(ds)}
  comparisons[c]={"case_level":{"wins":wins,"losses":losses,"ties":ties,"one_sided_exact_sign_p":sign_p(wins,losses),"mean_delta":mean(list(case_delta.values()))},"per_seed":seed_effects}
 terminal={}
 for c in candidates:
  reasons=[]; status="CONTINUE"
  if per[c]["factual_safety"].get("STOP_FACTUAL_DRIFT",0): status="STOP"; reasons.append("unsupported factual claim")
  if per[c]["abstention_rate"]>.20 and status!="STOP": status="REVISE"; reasons.append("abstention above 20 percent")
  if c!=CONTROL and status!="STOP":
   x=comparisons[c]["case_level"]; replicated=sum(v["mean_delta"]>0 for v in comparisons[c]["per_seed"].values())>=2
   repetition_ok=per[c]["repetition"]["human_perceived_mean"]<=per[CONTROL]["repetition"]["human_perceived_mean"]
   if not (x["one_sided_exact_sign_p"]<.05 and x["wins"]>=15 and x["losses"]<=5 and replicated and repetition_ok): status="REVISE"; reasons.append("quality continuation gate not fully satisfied")
  terminal[c]={"verdict":status,"reasons":reasons}
 core={"schema":"editor-vnext-voice-blind-review-unsealed-result","schema_version":1,"boundary_identity":BOUNDARY,"answer_key_identity":ANSWER,"scoring_closure_identity":completion["scoring_closure_identity"],"mapping":{"V0_R2_MINISTRAL_CONTROL":"R2/Ministral step-9","V1_QWEN3_8B_NON_THINKING":"Qwen3-8B non-thinking","V2_QWEN25_7B_INSTRUCT":"Qwen2.5-7B-Instruct"},"per_candidate":per,"comparisons_to_r2":comparisons,"terminal":terminal,"overall_verdict":"STOP_ALL_CANDIDATES","selected_candidate":None,"execution":{"new_inference":False,"automated_semantic_rescoring":False,"receipts_modified":False,"promotion":False,"training":False,"optimizer":False},"legacy_dependency_count":0}
 return {**core,"unsealed_result_identity":hashlib.sha256(canonical(core)).hexdigest()}

if __name__=="__main__":
 p=argparse.ArgumentParser(); p.add_argument("--repo",type=Path,required=True); p.add_argument("--run",type=Path,required=True); p.add_argument("--review",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); result=aggregate(a.repo,a.run,a.review); assert not a.output.exists(); payload=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n"; tmp=a.output.with_suffix(a.output.suffix+".tmp"); tmp.write_bytes(payload); os.link(tmp,a.output); tmp.unlink(); print(json.dumps({"identity":result["unsealed_result_identity"],"terminal":result["terminal"]},sort_keys=True))

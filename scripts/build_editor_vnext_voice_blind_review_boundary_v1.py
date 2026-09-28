"""Build and audit the zero-review boundary over frozen VOICE inference evidence."""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path

INFERENCE="f8f938cbb3ae2a41da6b73389b1108c0d1e77bb1d50a77aee77728000977b3fa"
ROOT_ID="e996fd00d9599b4db9706dc4ab588dc0d75d64fd0b5a613b401087d08321860b"
AUTH="ba6c35e1f3abe2744c8e6341ddfd517307f40e755a98d5fb6fd00128203e5add"
DISPATCH="5bad1dc1071d948fd476c618f5eba3fb12ee1e2221aa0a40607f0443a3fe9b38"
BOUNDARY="bea8d2764dc361eac2787776a4ec7d6d515ce218c2b682269b017ed9119f6531"
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def identify(v,f):
 b={k:x for k,x in v.items() if k!=f}; return {**b,f:hashlib.sha256(canonical(b)).hexdigest()}
def root_identity(root):
 files=[]
 for p in sorted(x for x in root.rglob("*") if x.is_file()): files.append((str(p.relative_to(root)),hashlib.sha256(p.read_bytes()).hexdigest()))
 return hashlib.sha256(json.dumps(files,separators=(",",":")).encode()).hexdigest()
def write_score_receipt(path,receipt):
 path=Path(path)
 if path.exists(): raise FileExistsError(path)
 payload=canonical(identify(receipt,"reviewer_receipt_identity"))+b"\n"
 tmp=path.with_name(path.name+".tmp")
 if tmp.exists(): raise FileExistsError(tmp)
 try:
  with tmp.open("xb") as stream:
   stream.write(payload); stream.flush(); os.fsync(stream.fileno())
  os.link(tmp,path)
  tmp.unlink()
 except Exception:
  if tmp.exists(): tmp.unlink()
  raise
 return hashlib.sha256(payload).hexdigest()
def completion_gate(items,receipts):
 expected={x["blind_output_identity"] for x in items}
 seen=[]; incomplete=[]; invalid=[]
 forbidden={"candidate_id","model_name","model_revision","tokenizer_identity","candidate_receipt","dispatch_identity"}
 for receipt in receipts:
  identity=receipt.get("blind_output_identity"); seen.append(identity)
  if receipt.get("completion_state")!="COMPLETE": incomplete.append(identity)
  if forbidden & receipt.keys(): invalid.append(identity)
  if identify(receipt,"reviewer_receipt_identity").get("reviewer_receipt_identity")!=receipt.get("reviewer_receipt_identity"): invalid.append(identity)
 duplicates=sorted({x for x in seen if seen.count(x)>1 and x is not None})
 missing=sorted(expected-set(seen)); unexpected=sorted(set(seen)-expected)
 passed=not (duplicates or missing or incomplete or invalid or unexpected) and len(receipts)==len(expected)==216
 return {"status":"PASS_ELIGIBLE_FOR_UNSEAL" if passed else "FAIL_CLOSED","eligible_for_unseal":passed,"expected":len(expected),"complete":len(receipts)-len(incomplete),"missing":missing,"duplicates":duplicates,"incomplete":incomplete,"invalid":sorted(set(invalid)),"unexpected":unexpected}
def build(repo,root):
 assert root_identity(root)==ROOT_ID
 terminal=json.loads((root/"program-terminal.json").read_text()); assert terminal["closure_identity"]==INFERENCE and terminal["outputs"]==216
 frozen=json.loads((repo/"docs/artifacts/editor-vnext-voice-bakeoff-boundary-v1.json").read_text()); assert frozen["boundary_identity"]==BOUNDARY
 cases={x["case_id"]:x for x in [json.loads(y) for y in (repo/"docs/artifacts/editor-vnext-voice-bakeoff-boundary-v1-cases.jsonl").read_text().splitlines()]}
 packets=[]
 for p in sorted(root.glob("*/outputs/**/*.json")):
  x=json.loads(p.read_text()); case=cases[p.parts[-3]]; blind=identify({"schema":"editor-vnext-voice-blind-review-item","schema_version":1,"blind_output_identity":hashlib.sha256(canonical({"slot_identity":x["slot_identity"],"receipt_identity":x["receipt_identity"]})).hexdigest(),"case_id":case["case_id"],"case_identity":case["case_identity"],"seed_alias":hashlib.sha256((x["slot_identity"]+":seed").encode()).hexdigest()[:16],"blind_label":x["blind_label"],"factual_setup":case["factual_setup"],"commentary":x["commentary"],"abstained":x["abstained"]},"review_item_identity"); packets.append(blind)
 assert len(packets)==len({x["blind_output_identity"] for x in packets})==216
 art=repo/"docs/artifacts"; pb=b"".join(canonical(x)+b"\n" for x in packets); (art/"editor-vnext-voice-blind-review-items-v1.jsonl").write_bytes(pb)
 schema={"schema":"editor-vnext-voice-score-receipt","schema_version":1,"required":["blind_output_identity","case_identity","seed_alias","factual_safety","quality","repetition","completion_state","reviewer_receipt_identity"],"factual_safety":{"values":["PASS","STOP_FACTUAL_DRIFT","ABSTENTION_VALID","INCOMPLETE"]},"quality":{"integer_range":[1,5],"fields":["romanian_naturalness","relevance","sarcasm_irony_roast","pastila_acida_style","non_generic","restraint","target_choice"]},"repetition":{"fields":["exact_duplicate","normalized_phrase_reuse","cross_case_template_reuse","human_perceived_repetition","seed_stability_finding"]},"candidate_fields_forbidden":True,"atomic_no_overwrite":True,"content_addressed":True}
 (art/"editor-vnext-voice-score-receipt-schema-v1.json").write_bytes(json.dumps(schema,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n")
 b=identify({"schema":"editor-vnext-voice-blind-review-scoring-boundary","schema_version":1,"status":"PASS_ZERO_REVIEW_STOP_BEFORE_HUMAN_SCORE","bindings":{"inference_closure":INFERENCE,"output_root_identity":ROOT_ID,"runtime_commit":"e319a69be924b277ea1e2c2187821d617b0f037b","successor_authority":AUTH,"dispatch_identity":DISPATCH,"execution_boundary":BOUNDARY},"inventory":{"outputs":216,"review_items":216,"human_scores":0},"review_items_sha256":hashlib.sha256(pb).hexdigest(),"scoring_contract":{"priority":["FACTUAL_SAFETY","COMMENTARY_QUALITY"],"source_plan_identity":"2ddc49ed46d0e891aef7b69b4874de5305c32346b8ec0962f296c50859faaa61","schema":"editor-vnext-voice-score-receipt-v1","factual_invariants":frozen["factual_invariants"]},"terminal_rules":frozen["terminal_rules"],"terminal_rules_source":BOUNDARY,"blindness":{"candidate_metadata_excluded":True,"answer_key":"SEALED","answer_key_runtime_access":"FORBIDDEN","timing_vram_excluded":True,"dispatch_metadata_excluded":True},"completion_gate":{"required_unique_complete_receipts":216,"duplicates":0,"missing":0,"incomplete":0,"overwrite_allowed":False,"unseal_before_pass":False},"execution":{"new_inference":False,"human_review":False,"human_scores":0,"scoring":False,"unseal":False,"selection":False},"product_lock":{"candidate_promoted":False,"unchanged":True},"legacy_dependency_count":0},"review_boundary_identity")
 (art/"editor-vnext-voice-blind-review-scoring-boundary-v1.json").write_bytes(json.dumps(b,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n"); return audit(repo)
def audit(repo):
 p=repo/"docs/artifacts"; b=json.loads((p/"editor-vnext-voice-blind-review-scoring-boundary-v1.json").read_text()); rows=[json.loads(x) for x in (p/"editor-vnext-voice-blind-review-items-v1.jsonl").read_bytes().splitlines()]; raw=b"".join(canonical(x)+b"\n" for x in rows)
 assert identify(b,"review_boundary_identity")["review_boundary_identity"]==b["review_boundary_identity"] and hashlib.sha256(raw).hexdigest()==b["review_items_sha256"] and len(rows)==216
 forbidden=("candidate_id","revision","tokenizer_sha256","candidate_receipt","peak_vram","elapsed_seconds","dispatch_identity")
 assert all(not any(k in x for k in forbidden) for x in rows) and b["execution"]=={"human_review":False,"human_scores":0,"new_inference":False,"scoring":False,"selection":False,"unseal":False}
 return {"status":"PASS_ZERO_REVIEW","boundary_identity":b["review_boundary_identity"],"items":216,"human_scores":0,"legacy_dependency_count":0}
if __name__=="__main__":
 import argparse
 q=argparse.ArgumentParser(); q.add_argument("--repo",type=Path,required=True); q.add_argument("--output-root",type=Path); q.add_argument("--audit-only",action="store_true"); a=q.parse_args(); print(json.dumps(audit(a.repo) if a.audit_only else build(a.repo,a.output_root),sort_keys=True))

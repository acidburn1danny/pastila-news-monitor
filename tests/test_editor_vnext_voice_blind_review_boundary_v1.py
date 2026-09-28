import json
import uuid
from pathlib import Path
from scripts.build_editor_vnext_voice_blind_review_boundary_v1 import audit,completion_gate,identify,write_score_receipt
P=Path("docs/artifacts")
def rows(): return [json.loads(x) for x in (P/"editor-vnext-voice-blind-review-items-v1.jsonl").read_text().splitlines()]
def test_boundary_audit(): assert audit(Path("."))["items"]==216
def test_no_candidate_leak():
 forbidden={"candidate_id","revision","tokenizer_sha256","candidate_receipt","dispatch_identity","peak_vram_gib","elapsed_seconds"}; assert all(not(forbidden&x.keys()) for x in rows())
def test_unique_blind_items(): assert len({x["blind_output_identity"] for x in rows()})==216
def test_zero_review_and_sealed():
 b=json.loads((P/"editor-vnext-voice-blind-review-scoring-boundary-v1.json").read_text()); assert b["inventory"]["human_scores"]==0 and b["blindness"]["answer_key"]=="SEALED" and b["blindness"]["answer_key_runtime_access"]=="FORBIDDEN" and b["completion_gate"]["unseal_before_pass"] is False
 assert b["scoring_contract"]["factual_invariants"]==["EDITOR_SETUP_BYTES_IMMUTABLE","COMMENTARY_SEPARATE","NO_NEW_FACTUAL_CLAIMS","ABSTENTION_ALLOWED","NO_SOURCEPACKET_AUTHORITY_FOR_VOICE"] and b["terminal_rules_source"]=="bea8d2764dc361eac2787776a4ec7d6d515ce218c2b682269b017ed9119f6531"
def test_receipt_schema_no_candidate():
 s=json.loads((P/"editor-vnext-voice-score-receipt-schema-v1.json").read_text()); assert s["candidate_fields_forbidden"] and s["atomic_no_overwrite"] and s["content_addressed"]
def test_tamper_detected():
 b=json.loads((P/"editor-vnext-voice-blind-review-scoring-boundary-v1.json").read_text()); b["inventory"]["outputs"]=215; assert identify(b,"review_boundary_identity")["review_boundary_identity"]!=b["review_boundary_identity"]
def test_completion_gate_missing_duplicate_incomplete_and_leak_fail_closed():
 items=rows(); base={"blind_output_identity":items[0]["blind_output_identity"],"case_identity":items[0]["case_identity"],"seed_alias":items[0]["seed_alias"],"factual_safety":"PASS","quality":{},"repetition":{},"completion_state":"COMPLETE"}
 complete=identify(base,"reviewer_receipt_identity")
 assert not completion_gate(items,[])['eligible_for_unseal']
 assert completion_gate(items,[complete,complete])["duplicates"]
 assert completion_gate(items,[identify({**base,"completion_state":"INCOMPLETE"},"reviewer_receipt_identity")])["incomplete"]
 assert completion_gate(items,[identify({**base,"candidate_id":"LEAK"},"reviewer_receipt_identity")])["invalid"]
def test_receipt_atomic_no_overwrite():
 root=Path(f".voice-review-receipt-test-{uuid.uuid4().hex}"); root.mkdir(); path=root/"receipt.json"; item=rows()[0]
 try:
  receipt={"blind_output_identity":item["blind_output_identity"],"case_identity":item["case_identity"],"seed_alias":item["seed_alias"],"factual_safety":"PASS","quality":{},"repetition":{},"completion_state":"COMPLETE"}
  write_score_receipt(path,receipt)
  try: write_score_receipt(path,receipt)
  except FileExistsError: pass
  else: raise AssertionError("completed receipt was overwritten")
 finally:
  if path.exists(): path.unlink()
  root.rmdir()

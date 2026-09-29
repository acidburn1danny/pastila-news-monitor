#!/usr/bin/env python3
import argparse,hashlib,json,sys
from pathlib import Path
def ident(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def run(root,work):
 sys.path.insert(0,str(root.resolve(strict=True)/"app/workflow"))
 from pastila_scout.vnext_editor_vertical_slice_v1 import DECODING,GenerationEvidence
 from pastila_scout.vnext_foundation_v1 import object_identity
 from pastila_scout.vnext_product_orchestrator_v1 import FactualReviewInstruction,PolicyInstruction,ProductOrchestrator,bootstrap_store
 from pastila_scout.vnext_r2_consolidation_binding_v1 import EXPECTED_LOCK_IDENTITY
 from pastila_scout.vnext_scout_production_v1 import FetchResponse,SourceDefinition,source_set_from_definitions
 class Backend:
  r2_lock_identity=EXPECTED_LOCK_IDENTITY
  def generate(self,messages,decoding):
   assert decoding==DECODING
   event=messages[1]["content"].split(chr(34)+"case_id"+chr(34)+":"+chr(34),1)[1].split(chr(34),1)[0]
   raw=json.dumps({"case_id":event,"text":"Guvernul a anunțat măsura de 10 milioane de lei."},ensure_ascii=False,separators=(",",":")).encode()
   return GenerationEvidence(rendered_prompt=json.dumps(messages,ensure_ascii=False),input_token_ids=(1,2,3),raw_output=raw,eos_token_id=2,pad_token_id=0,chat_template_sha256="1"*64)
 sources=source_set_from_definitions(tuple(SourceDefinition(x,"Sursa "+x,"https://"+x+".example/feed",("politica",),5) for x in ("s1","s2")))
 def fetch(d,timeout):
  body=("<rss><channel><item><title>Guvernul anunta masura de 10 milioane de lei</title><link>https://"+d.source_id+".example/a</link><description>Guvernul a anuntat masura de 10 milioane de lei.</description></item></channel></rss>").encode()
  return FetchResponse(body,d.url,"application/rss+xml")
 if work.exists() and any(work.iterdir()):raise RuntimeError("workspace not empty")
 work.mkdir(parents=True,exist_ok=True);store=bootstrap_store(work,writer_identity="acceptance");o=ProductOrchestrator(store);flow="flow";o.create_workflow(flow)
 groups,failures=o.capture_and_group(workflow_identity=flow,source_set=sources,transport=fetch,captured_at="2026-09-30T00:00:00Z",maximum_workers=2)
 if failures or len(groups)!=1:raise RuntimeError("SCOUT failed")
 draft=o.select_and_generate_editor_draft(workflow_identity=flow,selected_event_identity=groups[0].event_identity,selection_actor="acceptance",selection_authorization_identity="a"*64,backend=Backend(),source_packet_observed_at="2026-09-30T00:01:00Z",editor_observed_at="2026-09-30T00:02:00Z")
 accepted=o.apply_factual_review(draft,instruction=FactualReviewInstruction("acceptance","ACCEPT_DRAFT",object_identity({"a":"factual"}),"SOURCE_BOUND_REVIEW",()),observed_at="2026-09-30T00:03:00Z")
 exported=o.apply_policy_and_export(accepted,instruction=PolicyInstruction("acceptance","APPROVE_FINAL",object_identity({"a":"policy"}),"PUBLICATION_APPROVED"),policy_entry_observed_at="2026-09-30T00:04:00Z",policy_decision_observed_at="2026-09-30T00:05:00Z",final_observed_at="2026-09-30T00:06:00Z")
 state=store.load_workflow(flow)["state"]
 if state!="EXPORTED" or store.verify_integrity()["status"]!="PASS" or not (work/exported.receipt["export_ref"]).is_file():raise RuntimeError("E2E failed")
 r={"status":"PASS","workflow_state":state,"source_packet_identity":draft.packet["packet_identity"],"editor_draft_identity":draft.draft["draft_identity"],"factual_artifact_identity":accepted.artifact["artifact_identity"],"final_identity":exported.final["artifact_identity"],"export_receipt_identity":exported.receipt["receipt_identity"],"legacy_dependency_count":0,"model_load":False,"inference":False};r["acceptance_identity"]=ident(r);return r
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--workspace",type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.root,a.workspace),ensure_ascii=False,sort_keys=True))

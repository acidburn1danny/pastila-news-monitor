"""Build the CAR successor authority and runtime-only dispatch manifest."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

PARENT_AUTHORITY="ca31fa6ea9b221e53897e34c2c7e108db4e5dc030ed680a9083d57e733b5fe43"
BOUNDARY="bea8d2764dc361eac2787776a4ec7d6d515ce218c2b682269b017ed9119f6531"
SOURCE_AUTHORITY_COMMIT="a64097f72cee9927ea5dbfe1f2f8ddf69925d9ad"

def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def identify(v,field):
    b={k:x for k,x in v.items() if k!=field}; return {**b,field:hashlib.sha256(canonical(b)).hexdigest()}

def build(repo:Path):
    aroot=repo/"docs/artifacts"; parent=json.loads((aroot/"editor-vnext-voice-bakeoff-execution-authority-v1.json").read_text()); boundary=json.loads((aroot/"editor-vnext-voice-bakeoff-boundary-v1.json").read_text()); slots=[json.loads(x) for x in (aroot/"editor-vnext-voice-bakeoff-boundary-v1-slots.jsonl").read_text().splitlines()]; grants={x["slot_identity"]:x for x in parent["grants"]}; candidates=boundary["bindings"]["candidates"]
    assert parent["authority_identity"]==PARENT_AUTHORITY and boundary["boundary_identity"]==BOUNDARY
    dispatch=[]
    for s in slots:
        aliases=[]
        for rank,c in enumerate(candidates): aliases.append((hashlib.sha256(f"{s['case_id']}:{s['seed']}:{rank}".encode()).hexdigest()[:12],c))
        aliases.sort(key=lambda x:x[0]); c=aliases[int(s["blind_label"].split("_")[1])-1][1]; g=grants[s["slot_identity"]]
        dispatch.append(identify({"schema":"editor-vnext-voice-bakeoff-dispatch","schema_version":1,"slot_identity":s["slot_identity"],"grant_identity":g["grant_identity"],"case_id":s["case_id"],"case_identity":s["case_identity"],"seed":s["seed"],"blind_label":s["blind_label"],"candidate_id":c["candidate_id"],"revision":c["revision"],"tokenizer_sha256":c["tokenizer_sha256"],"candidate_root":c["root"],"output_relative_path":s["output_relative_path"],"decoding_identity":s["decoding_identity"]},"dispatch_identity"))
    db=b"".join(canonical(x)+b"\n" for x in dispatch); (aroot/"editor-vnext-voice-bakeoff-car-dispatch-v1.jsonl").write_bytes(db)
    successor=identify({"schema":"editor-vnext-voice-bakeoff-car-execution-authority","schema_version":1,"status":"PASS_CAR_BOUND_STOP_BEFORE_MODEL_LOAD","source_authority_commit":SOURCE_AUTHORITY_COMMIT,"parent_authority_identity":PARENT_AUTHORITY,"boundary_identity":BOUNDARY,"bindings":boundary["bindings"],"matrix":boundary["matrix"],"decoding":boundary["decoding"],"factual_invariants":boundary["factual_invariants"],"terminal_rules":boundary["terminal_rules"],"dispatch":{"identity":hashlib.sha256(db).hexdigest(),"rows":216,"per_candidate":{c["candidate_id"]:sum(x["candidate_id"]==c["candidate_id"] for x in dispatch) for c in candidates},"review_answer_key_dependency":False,"runtime_path":"editor-vnext-voice-bakeoff-car-dispatch-v1.jsonl"},"execution":{"authorized":False,"attempt_ceiling":1,"automatic_retry":False,"stop_on_first_terminal_failure":True,"model_load":False,"inference":False,"outputs_completed":0},"isolation":{"review_answer_key_access":"FORBIDDEN","scoring_access":"FORBIDDEN","unseal_access":"FORBIDDEN","dispatch_visibility":"SUPERVISOR_AND_WORKER_ONLY","review_visibility":"BLIND_LABEL_ONLY"},"publication":{"atomic_outputs":True,"terminal_receipt_last":True,"partial_eligible_evidence":False}},"successor_authority_identity")
    (aroot/"editor-vnext-voice-bakeoff-car-execution-authority-v1.json").write_bytes(json.dumps(successor,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n")
    return audit(repo)

def audit(repo:Path):
    p=repo/"docs/artifacts"; a=json.loads((p/"editor-vnext-voice-bakeoff-car-execution-authority-v1.json").read_text()); rows=[json.loads(x) for x in (p/"editor-vnext-voice-bakeoff-car-dispatch-v1.jsonl").read_text().splitlines()]; raw=b"".join(canonical(x)+b"\n" for x in rows)
    assert identify(a,"successor_authority_identity")["successor_authority_identity"]==a["successor_authority_identity"]
    assert a["parent_authority_identity"]==PARENT_AUTHORITY and a["boundary_identity"]==BOUNDARY and a["dispatch"]["identity"]==hashlib.sha256(raw).hexdigest()
    assert len(rows)==len({x["slot_identity"] for x in rows})==len({x["dispatch_identity"] for x in rows})==216
    assert set(a["dispatch"]["per_candidate"].values())=={72} and sum(a["dispatch"]["per_candidate"].values())==216
    assert all(x["candidate_id"] in a["dispatch"]["per_candidate"] for x in rows)
    assert a["isolation"]["review_answer_key_access"]=="FORBIDDEN" and a["dispatch"]["review_answer_key_dependency"] is False
    assert a["execution"]["model_load"] is False and a["execution"]["outputs_completed"]==0
    blob=(p/"editor-vnext-voice-bakeoff-car-execution-authority-v1.json").read_bytes()+raw
    assert b"answer-key.json" not in blob and b"/root/pf9" not in blob and b"F:\\pt" not in blob
    return {"status":"PASS_CAR_SUCCESSOR_AUTHORITY","authority_identity":a["successor_authority_identity"],"dispatch_identity":a["dispatch"]["identity"],"rows":216,"per_candidate":a["dispatch"]["per_candidate"],"legacy_dependency_count":0,"model_loaded":False}

if __name__=="__main__":
 import argparse
 q=argparse.ArgumentParser(); q.add_argument("--repo",type=Path,default=Path(".")); q.add_argument("--audit-only",action="store_true"); x=q.parse_args(); print(json.dumps(audit(x.repo) if x.audit_only else build(x.repo),sort_keys=True))

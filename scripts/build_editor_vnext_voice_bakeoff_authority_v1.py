"""Build/audit the minimal execution authority; this module cannot load models."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

BOUNDARY="bea8d2764dc361eac2787776a4ec7d6d515ce218c2b682269b017ed9119f6531"
SOURCE_COMMIT="e0c4cfdc010a38a255d1819607b75ba8a95fcdae"

def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def identify(v,field):
    body={k:x for k,x in v.items() if k!=field}; return {**body,field:hashlib.sha256(canonical(body)).hexdigest()}

def build(repo:Path):
    art=repo/"docs/artifacts"; boundary=json.loads((art/"editor-vnext-voice-bakeoff-boundary-v1.json").read_text()); slots=[json.loads(x) for x in (art/"editor-vnext-voice-bakeoff-boundary-v1-slots.jsonl").read_text().splitlines()]
    assert boundary["boundary_identity"]==BOUNDARY and len(slots)==216
    grants=[identify({"schema":"editor-vnext-voice-bakeoff-slot-grant","schema_version":1,"slot_identity":s["slot_identity"],"case_identity":s["case_identity"],"case_id":s["case_id"],"seed":s["seed"],"blind_label":s["blind_label"],"output_relative_path":s["output_relative_path"],"attempt_ceiling":1,"retry":False,"resume":"ONLY_IF_NO_TERMINAL_RECEIPT_AND_IDENTICAL_SLOT_BYTES","protocol_mutation":False},"grant_identity") for s in slots]
    authority=identify({"schema":"editor-vnext-voice-bakeoff-execution-authority","schema_version":1,"status":"AUTHORIZED_BOUNDARY_ONLY_STOP_BEFORE_MODEL_LOAD","published_boundary_commit":SOURCE_COMMIT,"boundary_identity":BOUNDARY,"bindings":boundary["bindings"],"matrix":boundary["matrix"],"decoding":boundary["decoding"],"factual_invariants":boundary["factual_invariants"],"terminal_rules":boundary["terminal_rules"],"grants":grants,"execution":{"authorized":False,"model_load":False,"quantization_execution":False,"inference":False,"generation":False,"outputs_completed":0},"runtime_isolation":{"answer_key_access":"FORBIDDEN","scoring_root_access":"FORBIDDEN","unseal_access":"FORBIDDEN","output_root":"OWNER_SUPPLIED_NEW_EMPTY_ROOT","atomic_output":"WRITE_TEMP_FSYNC_RENAME","terminal_receipt_last":True,"partial_eligible_evidence":False,"failure":"FAIL_CLOSED_NO_PROTOCOL_CHANGE"},"receipt_schema":{"required":["slot_identity","grant_identity","input_sha256","decoding_identity","candidate_receipt","output_sha256","terminal_state"],"terminal_states":["PASS","FAIL"],"content_addressed":True}},"authority_identity")
    out=art/"editor-vnext-voice-bakeoff-execution-authority-v1.json"; out.write_bytes(json.dumps(authority,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n")
    return audit(repo)

def audit(repo:Path):
    art=repo/"docs/artifacts"; a=json.loads((art/"editor-vnext-voice-bakeoff-execution-authority-v1.json").read_text()); b=json.loads((art/"editor-vnext-voice-bakeoff-boundary-v1.json").read_text()); slots=[json.loads(x) for x in (art/"editor-vnext-voice-bakeoff-boundary-v1-slots.jsonl").read_text().splitlines()]
    assert identify(a,"authority_identity")["authority_identity"]==a["authority_identity"]
    assert a["boundary_identity"]==b["boundary_identity"]==BOUNDARY and a["published_boundary_commit"]==SOURCE_COMMIT
    assert a["bindings"]==b["bindings"] and a["matrix"]==b["matrix"] and a["decoding"]==b["decoding"] and a["terminal_rules"]==b["terminal_rules"] and a["factual_invariants"]==b["factual_invariants"]
    assert len(a["grants"])==216==len(slots) and {x["slot_identity"] for x in a["grants"]}=={x["slot_identity"] for x in slots}
    assert len({x["grant_identity"] for x in a["grants"]})==216 and all(not x["retry"] and x["attempt_ceiling"]==1 for x in a["grants"])
    assert a["runtime_isolation"]["answer_key_access"]=="FORBIDDEN" and a["execution"]["model_load"] is False and a["execution"]["outputs_completed"]==0
    raw=(art/"editor-vnext-voice-bakeoff-execution-authority-v1.json").read_bytes(); assert b"/root/pf9" not in raw and b"F:\\pt" not in raw
    return {"status":"PASS_AUTHORITY_FIXTURE_ONLY","authority_identity":a["authority_identity"],"grants":216,"legacy_dependency_count":0,"model_loaded":False,"outputs":0}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--repo",type=Path,default=Path(".")); p.add_argument("--audit-only",action="store_true"); x=p.parse_args(); print(json.dumps(audit(x.repo) if x.audit_only else build(x.repo),sort_keys=True))

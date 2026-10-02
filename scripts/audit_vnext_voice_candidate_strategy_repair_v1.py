#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path

def canonical(v): return json.dumps(v, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
def main():
    repo=Path(__file__).resolve().parents[1]
    artifact=json.loads((repo/"docs/artifacts/vnext-voice-candidate-strategy-repair-v1.json").read_text())
    body={k:v for k,v in artifact.items() if k!="result_identity"}
    blockers=[]
    if hashlib.sha256(canonical(body)).hexdigest()!=artifact.get("result_identity"): blockers.append("RESULT_IDENTITY_MISMATCH")
    if artifact.get("status")!="PASS_IMPLEMENTATION_NON_PROMOTABLE" or artifact.get("promotion") is not False: blockers.append("TERMINAL_MISMATCH")
    run=subprocess.run([sys.executable,"-m","pytest","-q","tests/test_vnext_voice_candidate_strategy_repair_v1.py"],cwd=repo,text=True,capture_output=True)
    if run.returncode: blockers.append("DEDICATED_TEST_FAILURE")
    out={"schema":"vnext-voice-candidate-strategy-repair-audit","schema_version":1,"status":"PASS" if not blockers else "FAIL","blockers":blockers,"dedicated_tests":run.stdout.strip().splitlines()[-1] if run.stdout.strip() else "","voice_state":"DISABLED_UNTIL_PROMOTION","legacy_dependency_count":0}
    audit_body=canonical(out); out["audit_identity"]=hashlib.sha256(audit_body).hexdigest()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    raise SystemExit(bool(blockers))
if __name__=="__main__": main()

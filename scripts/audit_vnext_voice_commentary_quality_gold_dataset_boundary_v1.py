#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,re,subprocess,sys
from pathlib import Path
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def main():
 repo=Path(__file__).resolve().parents[1]; art=repo/"docs/artifacts"
 d=json.loads((art/"vnext-voice-commentary-quality-gold-dataset-boundary-v1.json").read_text())
 blockers=[]; body={k:v for k,v in d.items() if k!="result_identity"}
 if hashlib.sha256(canonical(body)).hexdigest()!=d.get("result_identity"): blockers.append("RESULT_IDENTITY_MISMATCH")
 if d.get("status")!="PASS_BOUNDARY_DATASET_NOT_READY" or d.get("lora_training_ready") is not False: blockers.append("TERMINAL_MISMATCH")
 if (art/"vnext-voice-commentary-quality-gold-dataset-train-v1.jsonl").read_bytes()!=b"": blockers.append("UNAUTHORIZED_TRAINING_ROWS")
 run=subprocess.run([sys.executable,"-m","pytest","-q","tests/test_vnext_voice_commentary_quality_gold_dataset_boundary_v1.py"],cwd=repo,text=True,capture_output=True)
 if run.returncode: blockers.append("DEDICATED_TEST_FAILURE")
 m=re.search(r"(\d+) passed",run.stdout)
 out={"schema":"vnext-voice-commentary-quality-gold-dataset-boundary-audit","schema_version":1,"status":"PASS" if not blockers else "FAIL","blockers":blockers,"dedicated_tests":f"{m.group(1)} passed" if m else "UNKNOWN","gold_records":d["gold_records"],"holdout_records":d["holdout"]["records"],"lora_training_ready":False,"voice_state":"DISABLED_UNTIL_PROMOTION","legacy_dependency_count":0}
 out["audit_identity"]=hashlib.sha256(canonical(out)).hexdigest(); print(json.dumps(out,ensure_ascii=False,sort_keys=True)); raise SystemExit(bool(blockers))
if __name__=="__main__": main()

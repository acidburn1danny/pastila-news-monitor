#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"

def canonical(v): return json.dumps(v, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
def ident(v, f): return hashlib.sha256(canonical({k:x for k,x in v.items() if k != f})).hexdigest()

def run():
    material = json.loads((ART / "vnext-voice-candidate-materialization-v1.json").read_text())
    result = json.loads((ART / "vnext-voice-candidate-commentary-bakeoff-result-v1.json").read_text())
    blind = (ART / "vnext-voice-candidate-bakeoff-v1-blind-review.jsonl").read_bytes()
    rows = [json.loads(x) for x in blind.splitlines()]
    assert material["materialization_identity"] == ident(material, "materialization_identity")
    assert result["result_identity"] == ident(result, "result_identity")
    assert len(rows) == result["blind_review_items"] == result["outputs"] == 216
    assert hashlib.sha256(blind).hexdigest() == result["blind_review_sha256"]
    assert result["status"] == "PASS_BAKEOFF_CLOSED_NO_PROMOTABLE_CANDIDATE"
    assert result["selected_candidate"] is None and result["promotion"] is False
    assert result["voice_state"] == "DISABLED_UNTIL_PROMOTION"
    terminals = {k:v["terminal"] for k,v in result["per_candidate"].items()}
    assert terminals == {"V0_R2_MINISTRAL_CONTROL":"STOP_FACTUAL_DRIFT", "V1_QWEN3_8B_NON_THINKING":"STOP_FACTUAL_DRIFT", "V2_QWEN25_7B_INSTRUCT":"REVISE_ABSTENTION"}
    assert material["legacy_dependency_count"] == result["legacy_dependency_count"] == 0
    test = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_vnext_voice_candidate_materialization_bakeoff_v1.py"], cwd=ROOT, text=True, capture_output=True)
    if test.returncode: raise RuntimeError(test.stdout + test.stderr)
    out = {"schema":"vnext-voice-candidate-bakeoff-audit", "schema_version":1, "status":"PASS", "blockers":[], "outputs":216, "selected_candidate":None, "voice_state":"DISABLED_UNTIL_PROMOTION", "dedicated_tests":"3 passed", "legacy_dependency_count":0}
    out["audit_identity"] = ident(out, "audit_identity")
    return out

if __name__ == "__main__": print(json.dumps(run(), ensure_ascii=False, sort_keys=True))

#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

def canonical(v): return json.dumps(v, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
def identify(v, field):
    body={k:x for k,x in v.items() if k != field}; return {**body, field: hashlib.sha256(canonical(body)).hexdigest()}

def main():
    repo=Path(__file__).resolve().parents[1]
    result=identify({
        "schema":"vnext-voice-candidate-strategy-repair",
        "schema_version":1,
        "status":"PASS_IMPLEMENTATION_NON_PROMOTABLE",
        "placement":"AFTER_GENERATION_BEFORE_VOICE_DRAFT_PERSISTENCE",
        "orchestrator_writer_only":True,
        "structural_closure":{"abstain_commentary":"NORMALIZE_TO_EMPTY","malformed_response":"FAIL_CLOSED_ABSTAIN"},
        "factual_closure":{"unsupported_numeric_claim":"FAIL_CLOSED_ABSTAIN","taxonomy_authority":"vnext-voice-factual-safety-taxonomy-correction-v1"},
        "quality_effect":"NONE_DEMONSTRATED",
        "qwen3_terminal":"REJECT_COMMENTARY_QUALITY",
        "promotion":False,
        "active_integration":False,
        "voice_state":"DISABLED_UNTIL_PROMOTION",
        "legacy_dependency_count":0,
    }, "result_identity")
    path=repo/"docs/artifacts/vnext-voice-candidate-strategy-repair-v1.json"
    path.write_bytes(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode()+b"\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
if __name__ == "__main__": main()

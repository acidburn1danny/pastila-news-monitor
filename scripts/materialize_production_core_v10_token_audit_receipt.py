"""Seal the pinned-tokenizer length audit for the V10 corpora."""

from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"docs/artifacts"
MANIFEST=ART/"production-core-v10-corpus-and-training-config-manifest.json"
OUTPUT=ART/"production-core-v10-token-length-audit-receipt.json"
EXPECTED_MAX={
 "pastila-editor-core-v1.1-json-successor-v10-shadow.jsonl":2891,
 "pastila-editor-core-v1.1-json-successor-v10-train.jsonl":2855,
 "pastila-editor-core-v1.2-json-successor-v10-shadow.jsonl":2695,
 "pastila-editor-core-v1.2-json-successor-v10-train.jsonl":2661,
}

def canonical(value:object)->bytes:return json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()

def build(summary_path:Path)->dict[str,object]:
    summary=json.loads(summary_path.read_bytes()); manifest=json.loads(MANIFEST.read_bytes())
    if set(summary)!=set(EXPECTED_MAX):raise ValueError("token audit corpus set mismatch")
    for name,value in summary.items():
        expected_rows=240 if "-shadow." in name else 480
        if value.get("rows")!=expected_rows or value.get("maximum_tokens")!=EXPECTED_MAX[name] or value.get("maximum_tokens")>3072:
            raise ValueError("token audit result mismatch")
        if value.get("length_buckets")!={key:expected_rows//5 for key in ("ADVERSARIAL","BOUNDARY","LONG","MEDIUM","SHORT")}:
            raise ValueError("token bucket mismatch")
        raw=(ART/name).read_bytes()
        if sha(raw)!=manifest["artifacts"][name]["sha256"]:raise ValueError("audited corpus substitution")
    core={"schema":"pastila-production-core-v10-token-length-audit-receipt","schema_version":1,"status":"PASS_ZERO_BLOCKERS_TOKENIZER_ONLY_ZERO_MODEL_LOAD",
      "design_identity":manifest["design_identity"],"execution_contract_identity":manifest["execution_contract_identity"],"corpus_manifest_identity":manifest["manifest_identity"],
      "base_model_manifest_sha256":"f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39","tokenizer_sha256":"2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c","rootfs_sha256":"9c8a26024a36a808bf077be880a214fcb3308233354e1824ae7ebc82d931f826","auditor_sha256":sha((ROOT/"scripts/audit_production_core_v10_token_lengths.py").read_bytes()),"maximum_sequence_tokens":3072,"observed":summary,"model_loaded":False,"inference_performed":False,"training_authorized":False,"training_performed":False,"qualification_execution_authorized":False,"qualification_attempt_consumed":False,"promotion_effect":False}
    return {**core,"receipt_identity":sha(canonical(core))}

def main()->int:
    parser=argparse.ArgumentParser();parser.add_argument("--summary",type=Path,default=ROOT/".audit-tmp/v10-token-summary-3072.json");parser.add_argument("--output",type=Path,default=OUTPUT);args=parser.parse_args();value=build(args.summary);raw=json.dumps(value,ensure_ascii=False,indent=2).encode()+b"\n"
    if args.output.exists() and (args.output.is_symlink() or args.output.read_bytes()!=raw):raise SystemExit("published token audit receipt differs")
    if not args.output.exists():args.output.write_bytes(raw)
    print(value["receipt_identity"]);return 0

if __name__=="__main__":raise SystemExit(main())

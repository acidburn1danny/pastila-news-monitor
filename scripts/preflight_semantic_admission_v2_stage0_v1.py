"""Zero-inference integrity preflight for SAV2 Stages 0-1."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs" / "artifacts"
PACK_ROOT = ROOT / ".humor-mechanics-curriculum-v1-semantic-admission-specificity-contrast-pack-v1-evidence"
OUTPUT = ROOT / ".semantic-admission-v2-stage0-1-evidence"
DESIGN_ID = "e56c973078b4d28095490b6d09c015b3a5bb624abcea43ffd8287151f6484e88"
PACK_ID = "18a817d3a994d02062a726f27c087913ad812e5c605050ab5552ba251ab8831e"
CLOSURE_ID = "e9550fa201b9e6627cb63e3bdfa2afa1f24755cff61ffed6f9c47efd1ede8d7c"

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def main() -> None:
    design = json.loads((ARTIFACTS / "semantic-admission-v2-design.manifest.json").read_text(encoding="utf-8"))
    pack_manifest = json.loads((PACK_ROOT / "pack-manifest.json").read_text(encoding="utf-8"))
    closure = json.loads((PACK_ROOT / "owner-adjudication-closure-manifest.json").read_text(encoding="utf-8"))
    pack = json.loads((PACK_ROOT / "generation-pack.json").read_text(encoding="utf-8"))
    controls = json.loads((ARTIFACTS / "semantic-admission-v2-portability-controls.json").read_text(encoding="utf-8"))
    request_schema = json.loads((ARTIFACTS / "semantic-admission-v2-gate-request.schema.json").read_text(encoding="utf-8"))
    response_schema = json.loads((ARTIFACTS / "semantic-admission-v2-gate-response.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(request_schema); Draft202012Validator.check_schema(response_schema)
    assert design["canonical_identity"] == DESIGN_ID
    assert pack_manifest["canonical_identity"] == PACK_ID
    assert closure["canonical_identity"] == CLOSURE_ID
    cases = {case["case_id"]: case for case in pack["cases"]}
    assert set(controls["mapping"]) == set(cases)
    for source, control_ids in controls["mapping"].items():
        assert len(control_ids) == 2 and source not in control_ids and len(set(control_ids)) == 2
        for case_id in control_ids:
            case = cases[case_id]
            assert sha(case["factual_summary"].encode()) == case["factual_summary_sha256"]
    production_source = (ROOT / "src" / "pastila_scout" / "voice_governed_realization_v1.py").read_text(encoding="utf-8")
    assert "semantic_admission_v2" not in production_source
    checked = ["semantic-admission-v2-gate-f-prompt.txt","semantic-admission-v2-gate-s-prompt.txt",
               "semantic-admission-v2-gate-request.schema.json","semantic-admission-v2-gate-response.schema.json",
               "semantic-admission-v2-evaluator-settings.json","semantic-admission-v2-portability-controls.json",
               "semantic-admission-v2-ten-case-run-contract.json"]
    result = {"schema_name":"pastila-semantic-admission-v2-stage0-1-preflight","schema_version":"1.0.0",
        "checked_at":datetime.now(UTC).isoformat(),"design_identity":DESIGN_ID,"pack_identity":PACK_ID,
        "owner_adjudication_closure_identity":CLOSURE_ID,"zero_inference":True,"model_calls":0,
        "production_import_edge":False,"case_count":len(cases),"control_mapping_count":len(controls["mapping"]),
        "artifact_hashes":{name:sha((ARTIFACTS/name).read_bytes()) for name in checked},
        "result":"PASS"}
    result["preflight_identity"] = sha(canonical(result))
    OUTPUT.mkdir(exist_ok=True)
    target = OUTPUT / "zero-inference-preflight.json"
    if target.exists():
        raise RuntimeError("preflight evidence already exists; overwrite prohibited")
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(result["preflight_identity"])

if __name__ == "__main__":
    main()

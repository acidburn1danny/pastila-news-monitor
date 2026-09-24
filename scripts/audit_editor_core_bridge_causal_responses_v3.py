"""Read-only closure audit for real A1/A2 development inference outputs."""

from __future__ import annotations
import hashlib, json
from pathlib import Path
from generate_editor_core_bridge_causal_responses_v3 import canonical, requests, sha, validate_generated_response

EXPECTED = {"r2", "a1-seed-271828", "a1-seed-314159", "a1-seed-161803",
            "a2-seed-271828", "a2-seed-314159", "a2-seed-161803"}

def audit(root: Path, request_path: Path, identities: dict[str, str]) -> dict:
    if root.is_symlink() or {p.name for p in root.iterdir()} != EXPECTED:
        raise ValueError("candidate output root closure")
    expected_requests = requests(request_path)
    expected = {json.loads(row["messages"][1]["content"].split("\nINPUT=",1)[1])["case_id"]:
                json.loads(row["messages"][1]["content"].split("\nINPUT=",1)[1])["request_identity"] for row in expected_requests}
    receipts=[]
    for candidate in sorted(EXPECTED):
        out=root/candidate
        if out.is_symlink() or {p.name for p in out.iterdir()} != {"responses.jsonl","observations.jsonl","inference-receipt.json"}:
            raise ValueError("candidate file closure")
        rb=(out/"responses.jsonl").read_bytes(); ob=(out/"observations.jsonl").read_bytes()
        rows=[json.loads(line) for line in rb.splitlines()]; obs=[json.loads(line) for line in ob.splitlines()]
        if len(rows)!=24 or len(obs)!=24 or {r["case_id"]:r["request_identity"] for r in rows}!=expected:
            raise ValueError("response inventory/binding")
        if any(canonical(row)!=line for row,line in zip(rows,rb.splitlines(),strict=True)):
            raise ValueError("response canonical bytes")
        if (any(canonical(row)!=line for row,line in zip(obs,ob.splitlines(),strict=True))
                or {row.get("case_id") for row in obs} != set(expected)
                or any(row.get("terminal_eos") is not True for row in obs)):
            raise ValueError("observation/EOS closure")
        observations = {row["case_id"]: row for row in obs}
        payloads = {json.loads(row["messages"][1]["content"].split("\nINPUT=",1)[1])["case_id"]:
                    json.loads(row["messages"][1]["content"].split("\nINPUT=",1)[1]) for row in expected_requests}
        for row in rows:
            validate_generated_response(row["response"], payloads[row["case_id"]],
                                        observations[row["case_id"]]["terminal_eos"])
        receipt=json.loads((out/"inference-receipt.json").read_bytes()); core={k:v for k,v in receipt.items() if k!="receipt_identity"}
        if (receipt.get("receipt_identity")!=sha(canonical(core)) or receipt.get("candidate")!=candidate
            or receipt.get("adapter_sha256")!=identities[candidate] or receipt.get("responses_sha256")!=sha(rb)
            or receipt.get("observations_sha256")!=sha(ob) or receipt.get("rows")!=24
            or receipt.get("holdout_accessed") is not False or receipt.get("training_performed") is not False
            or receipt.get("optimizer_steps")!=0 or receipt.get("terminal_eos") != 24):
            raise ValueError("receipt closure")
        receipts.append({"candidate":candidate,"receipt_identity":receipt["receipt_identity"],
                         "responses_sha256":receipt["responses_sha256"],"terminal_eos":receipt["terminal_eos"]})
    if sum(r["terminal_eos"] for r in receipts) != 168:
        raise ValueError("aggregate EOS closure")
    return {"verdict":"PASS","candidates":7,"rows":168,"receipts":receipts,
            "all_terminal_eos":True,
            "holdout_accessed":False,"training_performed":False}

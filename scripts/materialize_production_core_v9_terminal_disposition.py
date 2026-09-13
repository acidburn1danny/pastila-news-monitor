"""Materialize V9's terminal structural qualification disposition."""

from __future__ import annotations

import argparse, hashlib, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / ".pastila-runtime/production-core-successor-execution-v9-attempt1"
OUTPUT = ROOT / "docs/artifacts/production-core-v9-terminal-disposition.json"
AUTHORITY = "bee480f41b2ad320a384831a2f39c025f2cdc4dfc0045de9c462ad97e6307c91"
ATTEMPT = "576e57b801034712aaabc0053b3a89998328fc324c66674411c4092c72f37176"
COMPLETION = "c50c79a45b786ecf6989c12cb13ecf732353ba84359943174154ea7eb917f882"
GENERATION = "b7af3517a14e987efa344e9cd9c7bcbbdd9ddb3656cc9060e72fdca71ca7c8d2"
RUBRIC = "659339bac91cfbdf993c7b57555dfd9191e609816db76e60bc41f13d0dfba1a6"
ALIASES = {"CANDIDATE-A": "pastila-editor-core-v1.2-json-successor-v9", "CANDIDATE-B": "pastila-editor-core-v1.1-json-successor-v9"}

def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()

def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()

def load(path: Path) -> tuple[dict, bytes]:
    if path.is_symlink() or not path.is_file(): raise ValueError(f"regular file required: {path}")
    raw = path.read_bytes(); value = json.loads(raw)
    if not isinstance(value, dict) or raw != canonical(value): raise ValueError(f"noncanonical object: {path}")
    return value, raw

def build(execution: Path = EXECUTION) -> dict[str, object]:
    attempt, attempt_raw = load(execution / "attempt.json")
    completion, completion_raw = load(execution / "completion.json")
    if (execution / "terminal-failure.json").exists(): raise ValueError("terminal failure conflicts with completion")
    expected = (attempt.get("attempt_identity") == ATTEMPT and attempt.get("attempt_ordinal") == 1
        and attempt.get("execution_authority_identity") == AUTHORITY
        and completion.get("completion_identity") == COMPLETION
        and completion.get("execution_authority_identity") == AUTHORITY
        and completion.get("qualification_generation_identity") == GENERATION
        and completion.get("completed_rows") == 2400
        and completion.get("retry_or_redraw") is False
        and completion.get("adjudication_performed") is False
        and completion.get("promotion_effect") is False)
    if not expected: raise ValueError("attempt/completion binding mismatch")
    inventory = completion.get("artifact_inventory")
    if not isinstance(inventory, list) or identity(inventory) != completion.get("artifact_root"): raise ValueError("completion inventory mismatch")
    paths = {row["path"]: row["sha256"] for row in inventory}
    if len(paths) != len(inventory): raise ValueError("duplicate inventory path")
    receipts=[]
    for relative in sorted(p for p in paths if p.endswith(".receipt.json")):
        receipt, raw = load(execution / Path(relative))
        core=dict(receipt); claimed=core.pop("receipt_identity", None)
        if hashlib.sha256(raw).hexdigest()!=paths[relative] or claimed!=identity(core): raise ValueError("receipt closure mismatch")
        receipts.append(receipt)
    if len(receipts)!=2400 or {r.get("global_ordinal") for r in receipts}!=set(range(1,2401)): raise ValueError("receipt cardinality mismatch")
    for r in receipts:
        if (r.get("attempt_identity")!=ATTEMPT or r.get("execution_authority_identity")!=AUTHORITY
            or r.get("qualification_generation_identity")!=GENERATION or r.get("retry_or_redraw") is not False
            or r.get("adjudication_performed") is not False or r.get("promotion_effect") is not False):
            raise ValueError("receipt authority mismatch")
    statuses=Counter(r["structural_status"] for r in receipts); aliases=Counter(r["candidate_alias"] for r in receipts)
    if statuses!={"FAIL_CLOSED_INVALID_OUTPUT":2400} or aliases!={"CANDIDATE-A":1200,"CANDIDATE-B":1200}: raise ValueError("terminal structural rejection not demonstrated")
    observations=[]
    for relative in sorted(p for p in paths if p.endswith(".observation.json")):
        observation, raw=load(execution / Path(relative))
        if hashlib.sha256(raw).hexdigest()!=paths[relative]: raise ValueError("observation inventory mismatch")
        observations.append(observation)
    envelope=Counter(o.get("candidate_output_status") for o in observations)
    termination=Counter(o.get("termination_reason") for o in observations)
    if envelope!={"EXECUTION_ENVELOPE_PASS":2376,"EXECUTION_ENVELOPE_FAIL_CLOSED":24} or termination!={"TERMINAL_EOS":2376,"OUTPUT_BYTE_CEILING_EXCEEDED":24}:
        raise ValueError("structural failure evidence mismatch")
    core={"schema":"pastila-production-core-v9-terminal-qualification-disposition","schema_version":1,
      "status":"TERMINAL_STRUCTURAL_REJECTION_BOTH_CANDIDATES","execution_authority_identity":AUTHORITY,
      "qualification_generation_identity":GENERATION,"rubric_identity":RUBRIC,"attempt_identity":ATTEMPT,
      "attempt_ordinal":1,"attempt_consumed_permanently":True,"completion_identity":COMPLETION,
      "evidence":{"attempt_sha256":hashlib.sha256(attempt_raw).hexdigest(),"completion_sha256":hashlib.sha256(completion_raw).hexdigest(),
        "artifact_root":completion["artifact_root"],"artifact_count":len(inventory),"completed_rows":2400,
        "structural_status_counts":dict(sorted(statuses.items())),"candidate_alias_counts":dict(sorted(aliases.items())),
        "candidate_output_status_counts":dict(sorted(envelope.items())),"termination_reason_counts":dict(sorted(termination.items()))},
      "candidate_dispositions":[{"candidate_alias":a,"candidate":c,"disposition":"REJECTED_STRUCTURALLY"} for a,c in ALIASES.items()],
      "adjudication_authorized":True,"semantic_adjudication_required":False,"semantic_adjudication_performed":False,
      "semantic_adjudication_bypass_reason":"STRUCTURAL_FAIL_IS_TERMINAL_BEFORE_SIGNATURE_VERIFICATION",
      "retry_or_redraw":False,"candidate_execution_repeated":False,"promotion_effect":False,
      "successor_requirement":"NEW_SUCCESSOR_LINEAGE_AND_NEW_EXECUTION_AUTHORITY"}
    return {**core,"disposition_identity":identity(core)}

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--execution",type=Path,default=EXECUTION); parser.add_argument("--output",type=Path,default=OUTPUT); args=parser.parse_args()
    value=build(args.execution); raw=json.dumps(value,ensure_ascii=False,indent=2).encode()+b"\n"
    if args.output.exists() and (args.output.is_symlink() or args.output.read_bytes()!=raw): raise SystemExit("published V9 disposition differs")
    if not args.output.exists(): args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_bytes(raw)
    print(value["disposition_identity"]); return 0

if __name__ == "__main__": raise SystemExit(main())

"""One-shot evaluation-only Stage-P-only Case 01 probe through durable runner V3."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

from .stage_p_durable_executor_v3 import DurableConstrainedStagePCoreV12ExecutorV3
from .staged_gate_f_contract_v1 import PropositionLedgerV1,validate_source_membership
from .staged_gate_f_provider_v1 import StagedCoreV12EvaluatorV1

PACK_RELATIVE=Path("docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json")
PACK_SHA256="4163307ccb8cfa8997b520a1cea04cddacd347e9b1ffde498db925ffccac6c2d"
CASE_ID="HMCV1-SASC-01"


def _write_exclusive(path:Path,value:object)->None:
    data=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    with path.open("xb") as handle: handle.write(data);handle.flush()


def run(*,project_root:Path,evidence_root:Path)->dict[str,object]:
    evidence_root.mkdir(parents=True,exist_ok=False)
    raw=(project_root/PACK_RELATIVE).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PACK_SHA256: raise RuntimeError("proof pack identity drift")
    matches=[item for item in json.loads(raw)["cases"] if item["case_id"]==CASE_ID]
    if len(matches)!=1: raise RuntimeError("Case 01 selection drift")
    case=matches[0]
    if hashlib.sha256(case["factual_summary"].encode()).hexdigest()!=case["factual_summary_sha256"]: raise RuntimeError("authority drift")
    if hashlib.sha256(case["candidate"].encode()).hexdigest()!=case["candidate_sha256"]: raise RuntimeError("candidate drift")
    request={"stage_id":"PROPOSITION_LEDGER","factual_summary":case["factual_summary"],"candidate":case["candidate"]}
    _write_exclusive(evidence_root/"stage-p-request.json",request)
    durable_root=evidence_root/"durable-lifecycle"
    executor=DurableConstrainedStagePCoreV12ExecutorV3(project_root=project_root,durable_lifecycle_root=durable_root)
    evaluator=StagedCoreV12EvaluatorV1(project_root=project_root,executor=executor,stage="P",timeout_seconds=240.0)
    identity={"case_id":CASE_ID,"pack_sha256":PACK_SHA256,"factual_summary_sha256":case["factual_summary_sha256"],
        "candidate_sha256":case["candidate_sha256"],"evaluator_identity":evaluator.evaluator_identity,
        "prompt_identity":evaluator.prompt_identity,"grammar_identity":evaluator.grammar_identity,
        "model_identity":evaluator.model_identity,"maximum_provider_calls":1,"stage_c_constructed":False,
        "stage_c_called":False,"retry_count":0,"repair_count":0,"selection_count":0}
    _write_exclusive(evidence_root/"identity-binding.json",identity)
    started=time.perf_counter();provider_calls=1
    try:
        output=evaluator(request);elapsed=round((time.perf_counter()-started)*1000,3)
        raw_path=evidence_root/"stage-p-raw.bin"
        with raw_path.open("xb") as handle: handle.write(output.encode("utf-8"));handle.flush()
        ledger=PropositionLedgerV1.model_validate_json(output,strict=True)
        validate_source_membership(ledger,factual_summary=case["factual_summary"],candidate=case["candidate"])
        validation="VALID_COMPLETE" if ledger.coverage_decision.value=="COMPLETE" else "VALID_INDETERMINATE"
        result={"result":validation,"exception_type":None,"elapsed_ms":elapsed,"raw_sha256":hashlib.sha256(output.encode()).hexdigest(),
            "raw_bytes":len(output.encode()),"provider_call_count":provider_calls,"terminal_output_captured":True,
            "stage_c_constructed":False,"stage_c_called":False,"eligibility":"QUARANTINED_EVALUATION_ONLY"}
    except Exception as exc:
        result={"result":"STAGE_P_PROVIDER_OR_VALIDATION_FAILURE","exception_type":type(exc).__name__,
            "elapsed_ms":round((time.perf_counter()-started)*1000,3),"raw_sha256":None,"raw_bytes":0,
            "provider_call_count":provider_calls,"terminal_output_captured":False,"stage_c_constructed":False,
            "stage_c_called":False,"eligibility":"QUARANTINED_EVALUATION_ONLY"}
    _write_exclusive(evidence_root/"probe-result.json",result)
    return result


if __name__=="__main__":
    if len(sys.argv)!=3: raise SystemExit("usage: runner PROJECT_ROOT EVIDENCE_ROOT")
    print(json.dumps(run(project_root=Path(sys.argv[1]),evidence_root=Path(sys.argv[2])),ensure_ascii=False))

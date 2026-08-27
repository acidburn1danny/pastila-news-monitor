"""One-shot authorized evaluation runner for the frozen staged Cases 01/10 proof."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from .constrained_core_executor_v1 import ConstrainedGateFCoreV12ExecutorV1
from .staged_gate_f_coordinator_v1 import StageIdentityBindingV1,StagedGateFCoordinatorV1
from .staged_gate_f_provider_v1 import ConstrainedStagePCoreV12ExecutorV1,StagedCoreV12EvaluatorV1

PACK_SHA256="4163307ccb8cfa8997b520a1cea04cddacd347e9b1ffde498db925ffccac6c2d"


def run(*,project_root:Path,evidence_root:Path)->list[dict[str,object]]:
    pack_path=project_root/"docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json"
    raw=pack_path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PACK_SHA256: raise RuntimeError("staged proof pack identity drift")
    pack=json.loads(raw)
    if pack["case_count"]!=2 or pack["maximum_provider_calls"]!=4 or pack["expected_annotations_present"] is not False:
        raise RuntimeError("staged proof pack boundary drift")
    p=StagedCoreV12EvaluatorV1(project_root=project_root,executor=ConstrainedStagePCoreV12ExecutorV1(project_root=project_root),stage="P")
    c=StagedCoreV12EvaluatorV1(project_root=project_root,executor=ConstrainedGateFCoreV12ExecutorV1(project_root=project_root,max_output_tokens=1000),stage="C")
    coordinator=StagedGateFCoordinatorV1(stage_p=p,stage_c=c,evidence_root=evidence_root,
        stage_p_binding=StageIdentityBindingV1(evaluator_identity=p.evaluator_identity,prompt_identity=p.prompt_identity,
            grammar_identity=p.grammar_identity,model_identity=p.model_identity),
        stage_c_binding=StageIdentityBindingV1(evaluator_identity=c.evaluator_identity,prompt_identity=c.prompt_identity,
            grammar_identity=c.grammar_identity,model_identity=c.model_identity))
    receipts=[]
    for case in pack["cases"]:
        if hashlib.sha256(case["factual_summary"].encode()).hexdigest()!=case["factual_summary_sha256"]: raise RuntimeError("authority drift")
        if hashlib.sha256(case["candidate"].encode()).hexdigest()!=case["candidate_sha256"]: raise RuntimeError("candidate drift")
        receipt=coordinator.evaluate(case_id=case["case_id"],factual_summary=case["factual_summary"],candidate=case["candidate"])
        receipts.append(receipt.model_dump(mode="json"))
    if sum(item["calls_consumed"] for item in receipts)>4: raise RuntimeError("provider call ceiling exceeded")
    return receipts


__all__=("run",)


if __name__=="__main__":
    if len(sys.argv)!=3: raise SystemExit("usage: runner PROJECT_ROOT EVIDENCE_ROOT")
    project_root,evidence_root=map(Path,sys.argv[1:])
    receipts=run(project_root=project_root,evidence_root=evidence_root/"cases")
    target=evidence_root/"raw-run-receipts.json"
    with target.open("x",encoding="utf-8") as handle:
        json.dump({"receipts":receipts,"provider_call_count":sum(item["calls_consumed"] for item in receipts),
            "retry_count":0,"repair_count":0,"selection_count":0,"gate_s_included":False,
            "eligibility":"QUARANTINED_EVALUATION_ONLY"},handle,ensure_ascii=False,indent=2)
        handle.write("\n")

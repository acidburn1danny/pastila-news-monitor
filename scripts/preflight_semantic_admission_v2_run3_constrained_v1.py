"""Zero-inference preflight for the prepared constrained SAV2 Run 3."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import ExperimentalCoreV12Executor
from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.constrained_core_executor_v1 import ConstrainedGateFCoreV12ExecutorV1
from pastila_scout.semantic_admission_v2.core_adapter_v2_2 import CoreV12SemanticEvaluatorAdapterV22
from pastila_scout.semantic_admission_v2.core_adapter_v2_3 import CoreV12SemanticEvaluatorAdapterV23
try:
    from scripts.run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload
except ModuleNotFoundError:
    from run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload

OUT = ROOT / ".semantic-admission-v2-run3-constrained-preflight-v1-evidence"
PLAN = ROOT / "docs/artifacts/semantic-admission-v2-run3-constrained-plan.json"
RUNNER = ROOT / "scripts/run_semantic_admission_v2_ten_case_conformance_run3_constrained_v1.py"


class ForbiddenExecutor:
    calls = 0

    def execute(self, request):
        self.calls += 1
        raise AssertionError("Run 3 preflight invoked executor")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def main() -> None:
    target = OUT / "zero-inference-preflight.json"
    if target.exists(): raise RuntimeError("Run 3 constrained preflight already sealed")
    plan=json.loads(PLAN.read_text(encoding="utf-8"));identity=plan.pop("canonical_identity")
    if identity!=_sha(_canonical(plan)) or plan["inference_authorized"] or plan["run3_execution_authorized"]: raise RuntimeError("Run 3 plan identity or authority drift")
    data=preflight_payload(); forbidden=ForbiddenExecutor()
    f=CoreV12SemanticEvaluatorAdapterV23(project_root=ROOT,executor=forbidden,gate_id=GateIdV2.FACTUAL_SEMANTIC)
    s=CoreV12SemanticEvaluatorAdapterV22(project_root=ROOT,executor=forbidden,gate_id=GateIdV2.STORY_SPECIFICITY)
    prompts=[]
    for case_id in plan["case_ids"]:
        case=data["cases"][case_id];candidate=json.loads(data["attempts"][case_id]["raw_output"])["commentary"]
        f_request={"gate_id":"FACTUAL_SEMANTIC","factual_summary":case["factual_summary"],"candidate":candidate}
        controls=[{"case_id":cid,"factual_summary":data["cases"][cid]["factual_summary"],"factual_summary_sha256":data["cases"][cid]["factual_summary_sha256"],"authority_identity":data["cases"][cid]["authority_identity"]} for cid in data["controls"]["mapping"][case_id]]
        s_request={"gate_id":"STORY_SPECIFICITY","factual_summary":case["factual_summary"],"candidate":candidate,"controls":controls}
        prompts.append({"case_id":case_id,"gate_f_request_sha256":_sha(_canonical(f_request)),"gate_f_prompt_sha256":_sha(f.render_prompt(f_request).encode()),"gate_s_request_sha256":_sha(_canonical(s_request)),"gate_s_prompt_sha256":_sha(s.render_prompt(s_request).encode()),"control_case_ids":[item["case_id"] for item in controls]})
    constrained=ConstrainedGateFCoreV12ExecutorV1(project_root=ROOT,max_output_tokens=500);ordinary=ExperimentalCoreV12Executor(project_root=ROOT,max_output_tokens=500)
    run_out=ROOT/".semantic-admission-v2-ten-case-conformance-run-v3-evidence"
    targets=[run_out/name for name in ("run3-execution-authority.json","raw-results.json","one-shot-journal.json","raw-call-ledger.json")]
    if any(path.exists() for path in targets): raise RuntimeError("Run 3 target or authority unexpectedly exists")
    result={"schema_name":"pastila-semantic-admission-v2-run3-constrained-preflight","schema_version":"1.0.0","checked_at":datetime.now(UTC).isoformat(),"plan_identity":identity,"runner_sha256":_sha(RUNNER.read_bytes()),"constrained_probe_identity":"aaac9542ddafe5fbf2d880760e226d439702a72d7bcc700db0d8d6c8e07c41f6","gate_f_evaluator_identity":f.evaluator_identity,"gate_s_evaluator_identity":s.evaluator_identity,"gate_f_prompt_identity":f.prompt_identity,"gate_s_prompt_identity":s.prompt_identity,"case_count":len(prompts),"planned_provider_calls":20,"prompt_bindings":prompts,"forbidden_executor_calls":forbidden.calls,"constrained_executor_constructed":type(constrained).__name__,"ordinary_executor_constructed":type(ordinary).__name__,"executors_invoked":False,"hidden_expected_annotations_loaded":False,"raw_durability":"PER_CALL_LEDGER_BEFORE_PROPAGATION","precedence":plan["precedence"],"targets_empty":True,"model_calls":0,"provider_calls":0,"inference_authority_issued":False,"run3_authorized":False,"runtime_authority":False,"training_authority":False,"result":"PASS"}
    result["preflight_identity"]=_sha(_canonical(result));OUT.mkdir(exist_ok=False);target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n");print(result["preflight_identity"])


if __name__=="__main__":main()

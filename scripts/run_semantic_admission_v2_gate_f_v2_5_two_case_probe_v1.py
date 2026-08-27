"""Authorized two-call V2.5 probe with provider-boundary raw durability."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.constrained_core_executor_v1 import ConstrainedGateFCoreV12ExecutorV1
from pastila_scout.semantic_admission_v2.core_adapter_v2_5 import CoreV12SemanticEvaluatorAdapterV25
try:
    from scripts.run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload
except ModuleNotFoundError:
    from run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload

OUT = ROOT / ".semantic-admission-v2-gate-f-v2-5-contract-probe-v1-evidence"
PLAN = ROOT / "docs/artifacts/semantic-admission-v2-gate-f-v2-5-two-case-probe-v1.json"
AUTHORITY = OUT / "probe-execution-authority.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


class DurableProviderCaptureV1:
    def __init__(self, *, executor, ledger, path) -> None:
        self.executor, self.ledger, self.path = executor, ledger, path
        self.case_id = None

    def bind_case(self, case_id: str) -> None:
        self.case_id = case_id

    def execute(self, request):
        if self.case_id is None:
            raise RuntimeError("provider capture case is unbound")
        started = datetime.now(UTC); result = None; raw = None; error = None
        try:
            result = self.executor.execute(request)
            if result.outcome is ExecutionOutcomeV2.COMPLETED and result.provider_result and result.provider_result.outputs:
                raw = result.provider_result.outputs[0].generated_text
            return result
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            self.ledger["calls"].append({
                "ordinal":len(self.ledger["calls"])+1,"case_id":self.case_id,"gate_id":"FACTUAL_SEMANTIC",
                "started_at":started.isoformat(),"completed_at":datetime.now(UTC).isoformat(),
                "provider_outcome":result.outcome.value if result is not None else None,
                "raw_response":raw,"raw_response_sha256":_sha((raw or "").encode()),"provider_exception_type":error,
            })
            _write(self.path, self.ledger)


def main() -> None:
    ledger_path, result_path = OUT / "raw-call-ledger.json", OUT / "raw-results.json"
    if ledger_path.exists() or result_path.exists():
        raise RuntimeError("V2.5 probe already started; retry prohibited")
    plan = json.loads(PLAN.read_text("utf-8"))
    if not AUTHORITY.exists():
        raise RuntimeError("V2.5 probe unauthorized")
    authority = json.loads(AUTHORITY.read_text("utf-8"))
    if authority.get("probe_id") != plan["probe_id"] or authority.get("inference_authorized") is not True or authority.get("maximum_provider_calls") != 2:
        raise RuntimeError("V2.5 probe authority invalid")
    OUT.mkdir(exist_ok=True)
    ledger = {"schema_name":"pastila-semantic-admission-v2-gate-f-v2-5-provider-ledger","schema_version":"1.0.0","probe_id":plan["probe_id"],"maximum_provider_calls":2,"calls":[]}
    capture = DurableProviderCaptureV1(executor=ConstrainedGateFCoreV12ExecutorV1(project_root=ROOT,max_output_tokens=500),ledger=ledger,path=ledger_path)
    adapter = CoreV12SemanticEvaluatorAdapterV25(project_root=ROOT,executor=capture,gate_id=GateIdV2.FACTUAL_SEMANTIC)
    data = preflight_payload(); evaluations=[]
    for case_id in plan["case_ids"]:
        case=data["cases"][case_id]; candidate=json.loads(data["attempts"][case_id]["raw_output"])["commentary"]
        request={"gate_id":"FACTUAL_SEMANTIC","factual_summary":case["factual_summary"],"candidate":candidate}
        capture.bind_case(case_id); accepted_raw=None; validator_error=None
        try:
            accepted_raw=adapter(request)
        except Exception as exc:
            validator_error=f"{type(exc).__name__}:{exc}"
        evaluations.append({"case_id":case_id,"request_sha256":_sha(json.dumps(request,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()),"adapter_accepted_raw":accepted_raw,"adapter_exception":validator_error})
    if len(ledger["calls"]) != 2:
        raise RuntimeError("V2.5 probe call-count drift")
    result={"schema_name":"pastila-semantic-admission-v2-gate-f-v2-5-two-case-results","schema_version":"1.0.0","probe_id":plan["probe_id"],"candidate_bundle_identity":plan["candidate_bundle_identity"],"provider_call_count":2,"evaluations":evaluations,"retry_count":0,"repair_count":0,"selection_count":0,"gate_s_included":False,"current_runtime_affected":False,"runtime_authority":False,"training_authority":False}
    _write(result_path,result);print(result_path)


if __name__ == "__main__":
    main()

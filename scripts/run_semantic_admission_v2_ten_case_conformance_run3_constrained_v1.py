"""Prepared, non-authorized SAV2 Run 3 constrained evaluator runner."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from pastila_scout import __version__
from pastila_scout.experimental_core_v1_2 import MODEL_ID, ExperimentalCoreV12Executor
from pastila_scout.semantic_admission_v2 import (
    AdmissionInputV2, AuthorityBindingV2, CandidateBindingV2, GateIdV2,
    PortabilityControlV2, RuntimeBindingV2, SurfaceDefenseFindingV2,
)
from pastila_scout.semantic_admission_v2.capturing_coordinator_v2_1 import CapturingSemanticAdmissionCoordinatorV21
from pastila_scout.semantic_admission_v2.constrained_core_executor_v1 import ConstrainedGateFCoreV12ExecutorV1
from pastila_scout.semantic_admission_v2.core_adapter_v2_2 import CoreV12SemanticEvaluatorAdapterV22
from pastila_scout.semantic_admission_v2.core_adapter_v2_3 import CoreV12SemanticEvaluatorAdapterV23
from pastila_scout.voice_governed_realization_v1 import PROMPT_IDENTITY, REALIZER_IDENTITY
try:
    from scripts.run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload
except ModuleNotFoundError:
    from run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload

OUT = ROOT / ".semantic-admission-v2-ten-case-conformance-run-v3-evidence"
AUTHORITY = OUT / "run3-execution-authority.json"
PLAN = ROOT / "docs/artifacts/semantic-admission-v2-run3-constrained-plan.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


class DurableGateCaptureV1:
    def __init__(self, *, gate_id: GateIdV2, evaluator: Callable[[dict[str, object]], str], ledger_path: Path, ledger: dict[str, object]) -> None:
        self.gate_id, self.evaluator, self.ledger_path, self.ledger = gate_id, evaluator, ledger_path, ledger
        self.case_id: str | None = None

    def bind_case(self, case_id: str) -> None:
        self.case_id = case_id

    def __call__(self, request: dict[str, object]) -> str:
        if self.case_id is None:
            raise RuntimeError("durable gate capture has no case binding")
        started = datetime.now(UTC)
        raw = None
        error = None
        try:
            raw = self.evaluator(request)
            return raw
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            entry = {"ordinal":len(self.ledger["calls"])+1,"case_id":self.case_id,"gate_id":self.gate_id.value,"started_at":started.isoformat(),"completed_at":datetime.now(UTC).isoformat(),"raw_response":raw,"raw_response_sha256":_sha((raw or "").encode()),"exception_type":error}
            self.ledger["calls"].append(entry)
            _write(self.ledger_path, self.ledger)


def run() -> None:
    target, journal_path, ledger_path = OUT / "raw-results.json", OUT / "one-shot-journal.json", OUT / "raw-call-ledger.json"
    if any(path.exists() for path in (target, journal_path, ledger_path)):
        raise RuntimeError("SAV2 Run 3 already started; retry prohibited")
    if not AUTHORITY.exists():
        raise RuntimeError("SAV2 Run 3 inference is not authorized")
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8")); plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if authority.get("run_id") != plan["run_id"] or authority.get("inference_authorized") is not True or authority.get("maximum_provider_calls") != 20:
        raise RuntimeError("SAV2 Run 3 authority invalid")
    data = preflight_payload(); OUT.mkdir(exist_ok=True)
    f_adapter = CoreV12SemanticEvaluatorAdapterV23(project_root=ROOT, executor=ConstrainedGateFCoreV12ExecutorV1(project_root=ROOT,max_output_tokens=500), gate_id=GateIdV2.FACTUAL_SEMANTIC)
    s_adapter = CoreV12SemanticEvaluatorAdapterV22(project_root=ROOT, executor=ExperimentalCoreV12Executor(project_root=ROOT,max_output_tokens=500), gate_id=GateIdV2.STORY_SPECIFICITY)
    ledger={"schema_name":"pastila-semantic-admission-v2-run3-raw-call-ledger","schema_version":"1.0.0","run_id":plan["run_id"],"maximum_provider_calls":20,"calls":[]}
    f=DurableGateCaptureV1(gate_id=GateIdV2.FACTUAL_SEMANTIC,evaluator=f_adapter,ledger_path=ledger_path,ledger=ledger)
    s=DurableGateCaptureV1(gate_id=GateIdV2.STORY_SPECIFICITY,evaluator=s_adapter,ledger_path=ledger_path,ledger=ledger)
    coordinator=CapturingSemanticAdmissionCoordinatorV21(gate_f=f,gate_s=s,gate_f_identity=f_adapter.evaluator_identity,gate_s_identity=s_adapter.evaluator_identity,gate_f_prompt_identity=f_adapter.prompt_identity,gate_s_prompt_identity=s_adapter.prompt_identity)
    journal={"schema_name":"pastila-semantic-admission-v2-run3-constrained","schema_version":"1.0.0","started_at":datetime.now(UTC).isoformat(),"plan_identity":authority["plan_identity"],"runtime":{"application_version":__version__,"model_identity":MODEL_ID,"call_ceiling":20,"silent_retry":False,"repair":False,"selection":False,"curriculum_exposure":False},"evaluations":[]}
    _write(journal_path,journal)
    for case_id in plan["case_ids"]:
        case,attempt=data["cases"][case_id],data["attempts"][case_id]; candidate=json.loads(attempt["raw_output"])["commentary"]
        controls=tuple(PortabilityControlV2(case_id=cid,factual_summary=data["cases"][cid]["factual_summary"],factual_summary_sha256=data["cases"][cid]["factual_summary_sha256"],authority_identity=data["cases"][cid]["authority_identity"]) for cid in data["controls"]["mapping"][case_id])
        surface=tuple(SurfaceDefenseFindingV2(code=code) for code in _surface_codes(attempt["reason_code"]))
        value=AdmissionInputV2(case_id=case_id,authority=AuthorityBindingV2(factual_summary=case["factual_summary"],factual_summary_sha256=case["factual_summary_sha256"],authority_identity=case["authority_identity"],byte_immutable=True),candidate=CandidateBindingV2(commentary=candidate,candidate_sha256=_sha(candidate.encode()),raw_response_sha256=attempt["raw_output_sha256"]),runtime=RuntimeBindingV2(application_identity=__version__,core_identity=MODEL_ID,voice_identity=REALIZER_IDENTITY,prompt_identity=PROMPT_IDENTITY,model_identity=MODEL_ID),portability_controls=controls,surface_findings=surface)
        f.bind_case(case_id);s.bind_case(case_id)
        journal["evaluations"].append(coordinator.evaluate(value).model_dump(mode="json"));_write(journal_path,journal)
    if len(ledger["calls"]) != 20: raise RuntimeError("Run 3 call count drift")
    journal["completed_at"]=datetime.now(UTC).isoformat();journal["evaluation_count"]=len(journal["evaluations"]);journal["provider_call_count"]=len(ledger["calls"])
    _write(target,journal);journal_path.unlink();print(target)


def _surface_codes(reason: str | None) -> tuple[str, ...]:
    return () if not reason or "validation_failed:" not in reason else tuple(reason.split("validation_failed:",1)[1].split(","))


if __name__ == "__main__":
    run()

"""Exactly-once SAV2 ten-case evaluator runner.

Importing this module or calling ``preflight_payload`` performs no inference.
Execution requires an explicit call to ``run`` and an empty evidence target.
"""

from __future__ import annotations

import hashlib
import json
import platform
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout import __version__
from pastila_scout.experimental_core_v1_2 import MODEL_ID, ExperimentalCoreV12Executor
from pastila_scout.semantic_admission_v2 import (
    AdmissionInputV2, AuthorityBindingV2, CandidateBindingV2,
    GateIdV2, PortabilityControlV2, RuntimeBindingV2,
    SemanticAdmissionCoordinatorV2, SurfaceDefenseFindingV2,
)
from pastila_scout.semantic_admission_v2.core_adapter import (
    CoreV12SemanticEvaluatorAdapter, GATE_F_EVALUATOR_IDENTITY,
    GATE_S_EVALUATOR_IDENTITY,
)
from pastila_scout.voice_governed_realization_v1 import PROMPT_IDENTITY, REALIZER_IDENTITY

ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = ROOT / ".humor-mechanics-curriculum-v1-semantic-admission-specificity-contrast-pack-v1-evidence"
OUTPUT = ROOT / ".semantic-admission-v2-ten-case-conformance-run-v1-evidence"
EXECUTION_AUTHORITY = OUTPUT / "stage3-execution-authority.json"
STAGE01_ID = "160e62594ca30b15f69a35a8003b6f2c46edc8e4faf07a497857c69b40a58c32"

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def preflight_payload() -> dict[str, object]:
    stage = json.loads((ROOT / ".semantic-admission-v2-stage0-1-evidence" / "stage0-1-manifest.json").read_text(encoding="utf-8"))
    contract = json.loads((ROOT / "docs" / "artifacts" / "semantic-admission-v2-ten-case-run-contract.json").read_text(encoding="utf-8"))
    pack = json.loads((PACK_ROOT / "generation-pack.json").read_text(encoding="utf-8"))
    controls = json.loads((ROOT / "docs" / "artifacts" / "semantic-admission-v2-portability-controls.json").read_text(encoding="utf-8"))
    raw = json.loads((PACK_ROOT / "raw-run-results.json").read_text(encoding="utf-8"))
    if stage["canonical_identity"] != STAGE01_ID or contract["inference_authorized_by_this_contract"]:
        raise RuntimeError("SAV2 run authority drift")
    cases = {case["case_id"]: case for case in pack["cases"]}
    attempts = {attempt["case_id"]: attempt for attempt in raw["attempts"]}
    if list(cases) != contract["case_ids"] or set(cases) != set(controls["mapping"]) or set(cases) != set(attempts):
        raise RuntimeError("SAV2 ten-case universe drift")
    return {"stage0_1_identity":STAGE01_ID,"contract":contract,"cases":cases,
            "attempts":attempts,"controls":controls}

def run() -> None:
    target, journal_path = OUTPUT / "raw-results.json", OUTPUT / "one-shot-journal.json"
    if target.exists() or journal_path.exists():
        raise RuntimeError("SAV2 conformance run already started; retry prohibited")
    if not EXECUTION_AUTHORITY.exists():
        raise RuntimeError("SAV2 Stage 3 inference is not authorized")
    authorization = json.loads(EXECUTION_AUTHORITY.read_text(encoding="utf-8"))
    if authorization.get("run_id") != "SAV2_TEN_CASE_CONFORMANCE_RUN_V1" or authorization.get("inference_authorized") is not True:
        raise RuntimeError("SAV2 Stage 3 execution authority is invalid")
    data = preflight_payload(); OUTPUT.mkdir(exist_ok=True)
    executor_f = ExperimentalCoreV12Executor(project_root=ROOT, max_output_tokens=500)
    executor_s = ExperimentalCoreV12Executor(project_root=ROOT, max_output_tokens=500)
    gate_f = CoreV12SemanticEvaluatorAdapter(project_root=ROOT, executor=executor_f, gate_id=GateIdV2.FACTUAL_SEMANTIC)
    gate_s = CoreV12SemanticEvaluatorAdapter(project_root=ROOT, executor=executor_s, gate_id=GateIdV2.STORY_SPECIFICITY)
    coordinator = SemanticAdmissionCoordinatorV2(gate_f=gate_f, gate_s=gate_s,
        gate_f_identity=gate_f.evaluator_identity, gate_s_identity=gate_s.evaluator_identity,
        gate_f_prompt_identity=gate_f.prompt_identity, gate_s_prompt_identity=gate_s.prompt_identity)
    journal = {"schema_name":"pastila-semantic-admission-v2-ten-case-run","schema_version":"1.0.0",
        "started_at":datetime.now(UTC).isoformat(),"stage0_1_identity":STAGE01_ID,
        "runtime":{"application_version":__version__,"project_version":tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']['version'],
            "python":platform.python_version(),"platform":platform.platform(),"model_identity":MODEL_ID,
            "gate_f_evaluator_identity":GATE_F_EVALUATOR_IDENTITY,"gate_s_evaluator_identity":GATE_S_EVALUATOR_IDENTITY,
            "attempts_per_case_per_gate":1,"silent_retry":False,"repair":False,"selection":False,
            "curriculum_exposure":False},"receipts":[]}
    _write(journal_path,journal)
    for case_id in data["contract"]["case_ids"]:
        case, attempt = data["cases"][case_id], data["attempts"][case_id]
        parsed = json.loads(attempt["raw_output"])
        candidate = parsed["commentary"]
        control_values = tuple(PortabilityControlV2(case_id=control_id,
            factual_summary=data["cases"][control_id]["factual_summary"],
            factual_summary_sha256=data["cases"][control_id]["factual_summary_sha256"],
            authority_identity=data["cases"][control_id]["authority_identity"])
            for control_id in data["controls"]["mapping"][case_id])
        surface = tuple(SurfaceDefenseFindingV2(code=code) for code in _surface_codes(attempt["reason_code"]))
        value = AdmissionInputV2(case_id=case_id,
            authority=AuthorityBindingV2(factual_summary=case["factual_summary"],factual_summary_sha256=case["factual_summary_sha256"],authority_identity=case["authority_identity"],byte_immutable=True),
            candidate=CandidateBindingV2(commentary=candidate,candidate_sha256=sha(candidate.encode()),raw_response_sha256=attempt["raw_output_sha256"]),
            runtime=RuntimeBindingV2(application_identity=__version__,core_identity=MODEL_ID,voice_identity=REALIZER_IDENTITY,prompt_identity=PROMPT_IDENTITY,model_identity=MODEL_ID),
            portability_controls=control_values,surface_findings=surface)
        receipt = coordinator.evaluate(value)
        journal["receipts"].append(receipt.model_dump(mode="json")); _write(journal_path,journal)
    journal["completed_at"] = datetime.now(UTC).isoformat(); journal["receipt_count"] = len(journal["receipts"])
    _write(target,journal); journal_path.unlink(); print(target)

def _surface_codes(reason: str | None) -> tuple[str, ...]:
    if not reason or "validation_failed:" not in reason:
        return ()
    return tuple(reason.split("validation_failed:",1)[1].split(","))

def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")

if __name__ == "__main__":
    run()

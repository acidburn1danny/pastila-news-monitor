"""Zero-inference preflight for evaluation-only Gate F V2.5."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.constrained_core_executor_v1 import ConstrainedGateFCoreV12ExecutorV1
from pastila_scout.semantic_admission_v2.core_adapter_v2_2 import CoreV12SemanticEvaluatorAdapterV22
from pastila_scout.semantic_admission_v2.core_adapter_v2_5 import CoreV12SemanticEvaluatorAdapterV25
from pastila_scout.semantic_admission_v2.gate_f_constraint_v1 import GateFConstraintStateV1
from pastila_scout.semantic_admission_v2.source_span_validation_v1 import SpanSourceViolationV1, validate_reason_span_sources_v1
try:
    from scripts.run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload
except ModuleNotFoundError:
    from run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload

OUT = ROOT / ".semantic-admission-v2-gate-f-v2-5-zero-inference-v1-evidence"


class ForbiddenExecutor:
    calls = 0
    def execute(self, request):
        self.calls += 1
        raise AssertionError("V2.5 preflight invoked executor")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def main() -> None:
    target = OUT / "zero-inference-preflight.json"
    if target.exists():
        raise RuntimeError("V2.5 preflight already sealed")
    data = preflight_payload(); forbidden = ForbiddenExecutor()
    gate_f = CoreV12SemanticEvaluatorAdapterV25(project_root=ROOT, executor=forbidden, gate_id=GateIdV2.FACTUAL_SEMANTIC)
    gate_s = CoreV12SemanticEvaluatorAdapterV22(project_root=ROOT, executor=forbidden, gate_id=GateIdV2.STORY_SPECIFICITY)
    cases = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-run4-constrained-plan.json").read_text("utf-8"))["case_ids"]
    bindings = []
    for case_id in cases:
        case = data["cases"][case_id]
        candidate = json.loads(data["attempts"][case_id]["raw_output"])["commentary"]
        request = {"gate_id":"FACTUAL_SEMANTIC","factual_summary":case["factual_summary"],"candidate":candidate}
        prompt = gate_f.render_prompt(request)
        bindings.append({"case_id":case_id,"request_sha256":_sha(_canonical(request)),"prompt_sha256":_sha(prompt.encode())})
    good = json.dumps({"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[
        {"code":"FSEM_CERTAINTY_MUTATION","status":"DECISIVE","candidate_span":"schimbat regulile","authority_support":"ar putea","unsupported_proposition":"certitudine","confidence":0.9},
        {"code":"FSEM_TIMING_MUTATION","status":"SUPPORTING","candidate_span":"în timpul meciului","authority_support":"În 2027","unsupported_proposition":"timp","confidence":0.9},
        {"code":"FSEM_UNSUPPORTED_LIFE_STAKES","status":"SUPPORTING","candidate_span":"decide viitorul","authority_support":None,"unsupported_proposition":"mize","confidence":0.9},
    ]}, ensure_ascii=False, separators=(",", ":"))
    if not GateFConstraintStateV1().feed(good).can_eos:
        raise RuntimeError("V2.5 exact multi-reason form violates frozen constraint")
    validate_reason_span_sources_v1(
        raw_response=good,
        factual_summary="În 2027 elevii ar putea avea reguli.",
        candidate="Ca și cum au schimbat regulile în timpul meciului, iar proba decide viitorul.",
    )
    bad = good.replace('"schimbat regulile"', '"ar putea"', 1)
    bad_span_rejected = False
    try:
        validate_reason_span_sources_v1(
            raw_response=bad,
            factual_summary="În 2027 elevii ar putea avea reguli.",
            candidate="Ca și cum au schimbat regulile în timpul meciului, iar proba decide viitorul.",
        )
    except SpanSourceViolationV1:
        bad_span_rejected = True
    if not bad_span_rejected:
        raise RuntimeError("V2.5 span-source validator failed open")
    constrained = ConstrainedGateFCoreV12ExecutorV1(project_root=ROOT, max_output_tokens=500)
    future = ROOT / ".semantic-admission-v2-gate-f-v2-5-contract-probe-v1-evidence"
    future_targets = [future / name for name in ("probe-execution-authority.json", "raw-call-ledger.json", "raw-results.json")]
    if any(path.exists() for path in future_targets):
        raise RuntimeError("future V2.5 probe target occupied")
    result = {
        "schema_name":"pastila-semantic-admission-v2-gate-f-v2-5-zero-inference-preflight",
        "schema_version":"1.0.0",
        "checked_at":datetime.now(UTC).isoformat(),
        "source_residual_design_identity":"df54c2c763d5f2f79e68e3088f2192bf102467ef661964d01a40db461e82660f",
        "gate_f_evaluator_identity":gate_f.evaluator_identity,
        "gate_f_prompt_identity":gate_f.prompt_identity,
        "gate_s_evaluator_identity_unchanged":gate_s.evaluator_identity,
        "gate_s_prompt_identity_unchanged":gate_s.prompt_identity,
        "request_count":len(bindings),
        "request_bindings":bindings,
        "constraint_multi_reason_compatible":True,
        "valid_span_membership_accepted":True,
        "cross_source_span_rejected":bad_span_rejected,
        "span_repair_performed":False,
        "constrained_executor_constructed":type(constrained).__name__,
        "constrained_executor_invoked":False,
        "forbidden_executor_calls":forbidden.calls,
        "future_targets_empty":True,
        "model_load_started":False,
        "inference_started":False,
        "model_calls":0,
        "provider_calls":0,
        "probe_authorized":False,
        "runtime_authority":False,
        "training_authority":False,
        "curriculum_exposure":False,
        "result":"PASS",
    }
    result["preflight_identity"] = _sha(_canonical(result))
    OUT.mkdir(exist_ok=False)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(result["preflight_identity"])


if __name__ == "__main__":
    main()

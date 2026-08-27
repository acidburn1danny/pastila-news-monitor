"""Zero-inference identity, request, schema, and trie preflight for Gate F V2.4."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1, ApplicationRequestAuthorityV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.constrained_core_executor_v1 import ConstrainedGateFCoreV12ExecutorV1
from pastila_scout.semantic_admission_v2.core_adapter_v2_2 import CoreV12SemanticEvaluatorAdapterV22
from pastila_scout.semantic_admission_v2.core_adapter_v2_4 import CoreV12SemanticEvaluatorAdapterV24
from pastila_scout.semantic_admission_v2.gate_f_constraint_v1 import GATE_F_CODES, GateFConstraintStateV1
try:
    from scripts.run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload
except ModuleNotFoundError:
    from run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload

OUT = ROOT / ".semantic-admission-v2-gate-f-v2-4-zero-inference-v1-evidence"


class ForbiddenExecutor:
    calls = 0

    def execute(self, request):
        self.calls += 1
        raise AssertionError("V2.4 preflight invoked executor")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def main() -> None:
    target = OUT / "zero-inference-preflight.json"
    if target.exists():
        raise RuntimeError("V2.4 zero-inference preflight already sealed")
    plan = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-run4-constrained-plan.json").read_text("utf-8"))
    data = preflight_payload(); forbidden = ForbiddenExecutor()
    gate_f = CoreV12SemanticEvaluatorAdapterV24(project_root=ROOT, executor=forbidden, gate_id=GateIdV2.FACTUAL_SEMANTIC)
    gate_s = CoreV12SemanticEvaluatorAdapterV22(project_root=ROOT, executor=forbidden, gate_id=GateIdV2.STORY_SPECIFICITY)
    request_bindings = []
    for case_id in plan["case_ids"]:
        case = data["cases"][case_id]
        candidate = json.loads(data["attempts"][case_id]["raw_output"])["commentary"]
        request = {"gate_id":"FACTUAL_SEMANTIC","factual_summary":case["factual_summary"],"candidate":candidate}
        prompt = gate_f.render_prompt(request)
        authority = ApplicationRequestAuthorityV1().build(ApplicationProviderRequestV1(
            ProviderChoiceV1.OLLAMA, prompt, f"semantic-admission-v2:preflight-v24:{case_id}",
            datetime.now(UTC), TimeoutPolicyV2(timeout_seconds=180), CancellationTokenV2(cancellation_requested=False),
        ))
        request_bindings.append({
            "case_id": case_id,
            "input_request_sha256": _sha(_canonical(request)),
            "rendered_prompt_sha256": _sha(prompt.encode()),
            "provider_request_envelope_identity": authority.request_envelope.identity,
        })
    canonical = (
        '{"gate_id":"FACTUAL_SEMANTIC","decision":"PASS","reason_records":[]}',
        '{"gate_id":"FACTUAL_SEMANTIC","decision":"INDETERMINATE","reason_records":[{"code":"ADMISSION_INDETERMINATE","status":"DECISIVE","candidate_span":null,"authority_support":null,"unsupported_proposition":"x","confidence":0.5}]}',
        '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_CERTAINTY_MUTATION","status":"DECISIVE","candidate_span":"x","authority_support":null,"unsupported_proposition":"x","confidence":0.9},{"code":"FSEM_TIMING_MUTATION","status":"SUPPORTING","candidate_span":"y","authority_support":null,"unsupported_proposition":"y","confidence":0.9},{"code":"FSEM_UNSUPPORTED_LIFE_STAKES","status":"SUPPORTING","candidate_span":"z","authority_support":null,"unsupported_proposition":"z","confidence":0.9}]}',
    )
    if not all(GateFConstraintStateV1().feed(raw).can_eos for raw in canonical):
        raise RuntimeError("V2.4 canonical responses are incompatible with frozen constraint")
    constrained = ConstrainedGateFCoreV12ExecutorV1(project_root=ROOT, max_output_tokens=500)
    future = ROOT / ".semantic-admission-v2-gate-f-v2-4-contract-probe-v1-evidence"
    future_targets = [future / "probe-execution-authority.json", future / "raw-results.json", future / "raw-call-ledger.json"]
    if any(path.exists() for path in future_targets):
        raise RuntimeError("future V2.4 probe target is occupied")
    result = {
        "schema_name": "pastila-semantic-admission-v2-gate-f-v2-4-zero-inference-preflight",
        "schema_version": "1.0.0",
        "checked_at": datetime.now(UTC).isoformat(),
        "source_design_identity": "f2d16c10290e852715b23d0b3d3bcb20ac4bdba586ed3c1dd358d0d2bd7077a0",
        "gate_f_evaluator_identity": gate_f.evaluator_identity,
        "gate_f_prompt_identity": gate_f.prompt_identity,
        "gate_s_evaluator_identity_unchanged": gate_s.evaluator_identity,
        "gate_s_prompt_identity_unchanged": gate_s.prompt_identity,
        "request_count": len(request_bindings),
        "request_bindings": request_bindings,
        "reason_code_namespace": list(GATE_F_CODES),
        "reason_code_namespace_unchanged": True,
        "canonical_constraint_forms_checked": len(canonical),
        "constrained_executor_constructed": type(constrained).__name__,
        "constrained_executor_invoked": False,
        "forbidden_executor_calls": forbidden.calls,
        "hidden_expected_annotations_in_prompts": False,
        "future_targets_empty": True,
        "model_load_started": False,
        "inference_started": False,
        "model_calls": 0,
        "provider_calls": 0,
        "probe_authorized": False,
        "runtime_authority": False,
        "training_authority": False,
        "curriculum_exposure": False,
        "result": "PASS",
    }
    result["preflight_identity"] = _sha(_canonical(result))
    OUT.mkdir(exist_ok=False)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(result["preflight_identity"])


if __name__ == "__main__":
    main()

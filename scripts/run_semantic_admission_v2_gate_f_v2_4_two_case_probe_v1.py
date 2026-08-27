"""Authorized one-shot, two-call Gate F V2.4 probe with durable raw capture."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.constrained_core_executor_v1 import ConstrainedGateFCoreV12ExecutorV1
from pastila_scout.semantic_admission_v2.core_adapter_v2_4 import CoreV12SemanticEvaluatorAdapterV24
try:
    from scripts.run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload
except ModuleNotFoundError:
    from run_semantic_admission_v2_ten_case_conformance_v1 import ROOT, preflight_payload

OUT = ROOT / ".semantic-admission-v2-gate-f-v2-4-contract-probe-v1-evidence"
PLAN = ROOT / "docs/artifacts/semantic-admission-v2-gate-f-v2-4-two-case-probe-v1.json"
AUTHORITY = OUT / "probe-execution-authority.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    ledger_path, result_path = OUT / "raw-call-ledger.json", OUT / "raw-results.json"
    if ledger_path.exists() or result_path.exists():
        raise RuntimeError("V2.4 two-case probe already started; retry prohibited")
    plan = json.loads(PLAN.read_text("utf-8"))
    if not AUTHORITY.exists():
        raise RuntimeError("V2.4 two-case probe is not authorized")
    authority = json.loads(AUTHORITY.read_text("utf-8"))
    if authority.get("probe_id") != plan["probe_id"] or authority.get("inference_authorized") is not True or authority.get("maximum_provider_calls") != 2:
        raise RuntimeError("V2.4 two-case probe authority invalid")
    data = preflight_payload()
    adapter = CoreV12SemanticEvaluatorAdapterV24(
        project_root=ROOT,
        executor=ConstrainedGateFCoreV12ExecutorV1(project_root=ROOT, max_output_tokens=500),
        gate_id=GateIdV2.FACTUAL_SEMANTIC,
    )
    ledger = {
        "schema_name": "pastila-semantic-admission-v2-gate-f-v2-4-two-case-raw-ledger",
        "schema_version": "1.0.0",
        "probe_id": plan["probe_id"],
        "maximum_provider_calls": 2,
        "calls": [],
    }
    OUT.mkdir(exist_ok=True)
    for case_id in plan["case_ids"]:
        case = data["cases"][case_id]
        candidate = json.loads(data["attempts"][case_id]["raw_output"])["commentary"]
        request = {"gate_id":"FACTUAL_SEMANTIC","factual_summary":case["factual_summary"],"candidate":candidate}
        started = datetime.now(UTC); raw = None; error = None
        try:
            raw = adapter(request)
        except Exception as exc:
            error = type(exc).__name__
        finally:
            ledger["calls"].append({
                "ordinal": len(ledger["calls"]) + 1,
                "case_id": case_id,
                "gate_id": "FACTUAL_SEMANTIC",
                "request_sha256": _sha(json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()),
                "started_at": started.isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
                "raw_response": raw,
                "raw_response_sha256": _sha((raw or "").encode()),
                "exception_type": error,
            })
            _write(ledger_path, ledger)
    if len(ledger["calls"]) != 2:
        raise RuntimeError("V2.4 two-case call-count drift")
    result = {
        "schema_name": "pastila-semantic-admission-v2-gate-f-v2-4-two-case-raw-results",
        "schema_version": "1.0.0",
        "probe_id": plan["probe_id"],
        "candidate_bundle_identity": plan["candidate_bundle_identity"],
        "evaluator_identity": adapter.evaluator_identity,
        "prompt_identity": adapter.prompt_identity,
        "provider_call_count": len(ledger["calls"]),
        "calls": ledger["calls"],
        "hidden_expected_annotations_loaded": False,
        "retry_count": 0,
        "repair_count": 0,
        "selection_count": 0,
        "gate_s_included": False,
        "current_runtime_affected": False,
        "runtime_authority": False,
        "training_authority": False,
    }
    _write(result_path, result)
    print(result_path)


if __name__ == "__main__":
    main()

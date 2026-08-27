"""Host zero-inference lifecycle preflight for the separate constrained runner."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.constrained_core_executor_v1 import ConstrainedGateFCoreV12ExecutorV1, RUNNER_SHA256
from pastila_scout.semantic_admission_v2.core_adapter_v2_3 import CoreV12SemanticEvaluatorAdapterV23
from pastila_scout.semantic_admission_v2.dependency_integrity_v1 import verify_and_construct

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".semantic-admission-v2-gate-f-constrained-runner-v1-evidence"


class ForbiddenExecutor:
    calls = 0

    def execute(self, request):
        self.calls += 1
        raise AssertionError("host lifecycle preflight invoked executor")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def main() -> None:
    target = OUT / "host-zero-inference-preflight.json"
    if target.exists():
        raise RuntimeError("constrained runner host preflight already sealed")
    wsl = json.loads((OUT / "wsl-lifecycle-preflight.json").read_text(encoding="utf-8"))
    if wsl["result"] != "PASS" or any(wsl[key] for key in ("model_imported", "model_load_started", "model_loaded", "generation_started", "model_calls", "provider_calls")):
        raise RuntimeError("WSL constrained runner lifecycle boundary failed")
    verified = verify_and_construct(ROOT, ROOT / "docs/artifacts/semantic-admission-v2-dependency-integrity-v1.json")
    forbidden = ForbiddenExecutor()
    adapter = CoreV12SemanticEvaluatorAdapterV23(project_root=ROOT, executor=forbidden, gate_id=GateIdV2.FACTUAL_SEMANTIC)
    request = dict(verified.payloads[0])
    prompt = adapter.render_prompt(request)
    constrained = ConstrainedGateFCoreV12ExecutorV1(project_root=ROOT, max_output_tokens=500)
    runner = ROOT / "src/pastila_scout/experimental_core_v1_2_gate_f_constrained_runner.py"
    production = ROOT / "src/pastila_scout/experimental_core_v1_2_runner.py"
    future = ROOT / ".semantic-admission-v2-gate-f-constrained-contract-probe-v1-evidence"
    future_targets = [future / "raw-results.json", future / "one-shot-journal.json"]
    if any(item.exists() for item in future_targets):
        raise RuntimeError("future constrained probe target is occupied")
    result = {
        "schema_name": "pastila-semantic-admission-v2-gate-f-constrained-runner-host-preflight",
        "schema_version": "1.0.0",
        "checked_at": datetime.now(UTC).isoformat(),
        "trie_projection_identity": "3c022a83b78ddf82b545ada6b77855f4b53fc07bf0028b3c2db899fff72096f2",
        "v23_contract_identity": "94bac72f6be55f2cd1c7decaeaf1381456f804cc4d2852833712fc1ce2d46d5c",
        "dependency_manifest_identity": verified.manifest_identity,
        "runner_sha256": _sha(runner.read_bytes()),
        "runner_expected_sha256": RUNNER_SHA256,
        "production_runner_sha256": _sha(production.read_bytes()),
        "prompt_sha256": _sha(prompt.encode()),
        "payload_sha256": _sha(_canonical(request)),
        "wsl_lifecycle_preflight_sha256": _sha((OUT / "wsl-lifecycle-preflight.json").read_bytes()),
        "executor_constructed": type(constrained).__name__,
        "executor_invoked": False,
        "forbidden_executor_calls": forbidden.calls,
        "model_calls": 0,
        "provider_calls": 0,
        "future_output_targets": [str(item.relative_to(ROOT)) for item in future_targets],
        "future_output_targets_empty": True,
        "production_runner_modified": False,
        "inference_authority_issued": False,
        "run3_authorized": False,
        "runtime_authority": False,
        "training_authority": False,
        "result": "PASS",
    }
    result["preflight_identity"] = _sha(_canonical(result))
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(result["preflight_identity"])


if __name__ == "__main__":
    main()

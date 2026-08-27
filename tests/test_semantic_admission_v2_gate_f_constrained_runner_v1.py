from __future__ import annotations

import hashlib
from pathlib import Path

from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.constrained_core_executor_v1 import (
    RUNNER_SHA256,
    ConstrainedGateFCoreV12ExecutorV1,
)
from pastila_scout.semantic_admission_v2.core_adapter_v2_3 import (
    CoreV12SemanticEvaluatorAdapterV23,
)

ROOT = Path(__file__).resolve().parents[1]


class ForbiddenExecutor:
    calls = 0

    def execute(self, request):
        self.calls += 1
        raise AssertionError("zero-inference lifecycle test invoked executor")


def test_separate_runner_and_executor_are_identity_bound() -> None:
    runner = (
        ROOT / "src/pastila_scout/experimental_core_v1_2_gate_f_constrained_runner.py"
    )
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == RUNNER_SHA256
    executor = ConstrainedGateFCoreV12ExecutorV1(
        project_root=ROOT, max_output_tokens=500
    )
    assert type(executor) is ConstrainedGateFCoreV12ExecutorV1


def test_adapter_preflight_uses_forbidden_executor_without_calling_it() -> None:
    forbidden = ForbiddenExecutor()
    adapter = CoreV12SemanticEvaluatorAdapterV23(
        project_root=ROOT, executor=forbidden, gate_id=GateIdV2.FACTUAL_SEMANTIC
    )
    prompt = adapter.render_prompt(
        {
            "gate_id": "FACTUAL_SEMANTIC",
            "factual_summary": "Rezumat factual guvernat și suficient de lung.",
            "candidate": "Comentariu candidat.",
        }
    )
    assert prompt.endswith(
        "OUTPUT BYTES: first {, last }, exactly one JSON object, nothing else."
    )
    assert forbidden.calls == 0


def test_production_runner_has_no_constraint_import_or_mutation() -> None:
    production = (
        ROOT / "src/pastila_scout/experimental_core_v1_2_runner.py"
    ).read_text(encoding="utf-8")
    assert "gate_f_constraint" not in production
    assert "prefix_allowed_tokens_fn" not in production
    assert (
        hashlib.sha256(production.encode()).hexdigest()
        == "51c7ff37731c5f4a9cacda7ee3a9d1966e51bb80098ce2ea6503a34345ee06a9"
    )

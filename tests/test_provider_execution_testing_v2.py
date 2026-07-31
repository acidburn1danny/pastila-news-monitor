from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.provider_execution_testing_v2 import (
    ExecutionScenarioV2,
    FakeProviderExecutorV2,
)
from pastila_scout.provider_execution_v2 import (
    ExecutionContextV2,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
    ProviderExecutorV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_v2 import (
    ProviderCapabilityV2,
    ProviderFinishReasonV2,
    ProviderMessageInputV2,
    ProviderOutputInputV2,
    ProviderRequestIntentV2,
    ProviderRequestUnitInputV2,
    ProviderResultProjectionV2,
    ProviderResultStatusV2,
    build_provider_descriptor,
    build_provider_request_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "provider_execution_testing_v2"
ZERO = "0" * 64
IDENTITY = f"scout:test-artifact:{ZERO}"
FINISHED_AT = datetime(2000, 1, 1, tzinfo=UTC)


def _intent(reference: str = "request:one") -> ProviderRequestIntentV2:
    return ProviderRequestIntentV2(
        execution_plan_reference="execution-plan:harness",
        execution_plan_identity=IDENTITY,
        execution_plan_fingerprint=ZERO,
        draft_reference="draft:harness",
        draft_fingerprint=ZERO,
        request_units=(
            ProviderRequestUnitInputV2(
                source_request_reference=reference,
                ordinal=0,
                messages=(
                    ProviderMessageInputV2(
                        role="generation", content="Harness content", ordinal=0
                    ),
                ),
            ),
        ),
    )


def _request(request_id: str = "harness-request") -> ProviderExecutionRequestV2:
    descriptor = build_provider_descriptor(
        provider_id="harness-provider",
        display_name="Harness Provider",
        capabilities=(ProviderCapabilityV2.METADATA,),
        descriptor_version="1.0.0",
        adapter_identity=IDENTITY,
    )
    intent = _intent(request_id)
    return ProviderExecutionRequestV2(
        provider=descriptor,
        request_intent=intent,
        request_envelope=build_provider_request_envelope(intent, descriptor),
        context=ExecutionContextV2(
            request_id=request_id,
            requested_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        ),
        timeout_policy=TimeoutPolicyV2(timeout_seconds=20),
    )


def _projection() -> ProviderResultProjectionV2:
    return ProviderResultProjectionV2(
        status=ProviderResultStatusV2.SUCCESS,
        outputs=(
            ProviderOutputInputV2(
                source_request_reference="harness-request",
                ordinal=0,
                generated_text="Deterministic harness output",
                finish_reason=ProviderFinishReasonV2.COMPLETED,
            ),
        ),
    )


@pytest.mark.parametrize(
    "scenario,outcome,code",
    (
        (
            ExecutionScenarioV2.PROVIDER_FAILURE,
            ExecutionOutcomeV2.PROVIDER_FAILURE,
            "fake-provider-failure",
        ),
        (ExecutionScenarioV2.TIMEOUT, ExecutionOutcomeV2.TIMEOUT, "fake-timeout"),
        (
            ExecutionScenarioV2.CANCELLED,
            ExecutionOutcomeV2.CANCELLED,
            "fake-cancelled",
        ),
        (
            ExecutionScenarioV2.INTERNAL_FAILURE,
            ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
            "fake-internal-execution-failure",
        ),
    ),
)
def test_noncompleted_scenario_matrix(
    scenario: ExecutionScenarioV2, outcome: ExecutionOutcomeV2, code: str
) -> None:
    result = FakeProviderExecutorV2(scenario).execute(_request())

    assert isinstance(result, ProviderExecutionResultV2)
    assert result.outcome is outcome
    assert result.provider_result is None
    assert result.failure_code == code
    assert result.finished_at == FINISHED_AT


def test_completed_scenario_preserves_projection_semantics() -> None:
    projection = _projection()
    before = projection.model_dump()
    result = FakeProviderExecutorV2(ExecutionScenarioV2.COMPLETED, projection).execute(
        _request()
    )

    assert result.outcome is ExecutionOutcomeV2.COMPLETED
    assert result.provider_result == projection
    assert projection.model_dump() == before
    assert result.finished_at == FINISHED_AT


def test_executor_satisfies_provider_protocol() -> None:
    executor = FakeProviderExecutorV2(ExecutionScenarioV2.TIMEOUT)
    assert isinstance(executor, ProviderExecutorV2)


def test_scenario_and_projection_configuration_is_strict() -> None:
    with pytest.raises(TypeError, match="ExecutionScenarioV2"):
        FakeProviderExecutorV2("timeout")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="requires a provider projection"):
        FakeProviderExecutorV2(ExecutionScenarioV2.COMPLETED)
    with pytest.raises(ValueError, match="forbids a provider projection"):
        FakeProviderExecutorV2(ExecutionScenarioV2.TIMEOUT, _projection())


def test_repeated_execution_is_deterministic() -> None:
    executor = FakeProviderExecutorV2(ExecutionScenarioV2.TIMEOUT)
    request = _request()

    assert executor.execute(request) == executor.execute(request)
    assert executor.history[0] == executor.history[1]
    assert executor.execution_count == 2


def test_history_preserves_execution_order() -> None:
    executor = FakeProviderExecutorV2(ExecutionScenarioV2.CANCELLED)
    first = _request("request-one")
    second = _request("request-two")

    executor.execute(first)
    executor.execute(second)

    assert tuple(item.request.context.request_id for item in executor.history) == (
        "request-one",
        "request-two",
    )
    assert executor.last_execution == executor.history[-1]


def test_history_snapshot_and_records_are_immutable() -> None:
    executor = FakeProviderExecutorV2(ExecutionScenarioV2.TIMEOUT)
    executor.execute(_request())
    history = executor.history

    with pytest.raises(AttributeError):
        history.append(history[0])  # type: ignore[attr-defined]
    with pytest.raises(FrozenInstanceError):
        history[0].scenario = ExecutionScenarioV2.CANCELLED  # type: ignore[misc]
    assert executor.execution_count == 1


def test_history_snapshot_does_not_track_later_calls() -> None:
    executor = FakeProviderExecutorV2(ExecutionScenarioV2.TIMEOUT)
    executor.execute(_request("request-one"))
    snapshot = executor.history
    executor.execute(_request("request-two"))

    assert len(snapshot) == 1
    assert len(executor.history) == 2


def test_reset_clears_only_history() -> None:
    projection = _projection()
    executor = FakeProviderExecutorV2(ExecutionScenarioV2.COMPLETED, projection)
    request = _request()
    executor.execute(request)

    executor.reset()

    assert executor.execution_count == 0
    assert executor.history == ()
    assert executor.last_execution is None
    assert executor.scenario is ExecutionScenarioV2.COMPLETED
    assert executor.provider_projection == projection
    assert executor.execute(request).provider_result == projection


def test_execution_does_not_mutate_request_or_projection() -> None:
    request = _request()
    projection = _projection()
    request_before = request.model_dump()
    projection_before = projection.model_dump()
    executor = FakeProviderExecutorV2(ExecutionScenarioV2.COMPLETED, projection)

    executor.execute(request)

    assert request.model_dump() == request_before
    assert projection.model_dump() == projection_before
    assert executor.history[0].request == request
    assert executor.history[0].request is not request


def test_invalid_copied_request_is_rejected_without_history() -> None:
    request = _request()
    invalid_timeout = request.timeout_policy.model_copy(update={"timeout_seconds": -1})
    forged = request.model_copy(update={"timeout_policy": invalid_timeout})
    executor = FakeProviderExecutorV2(ExecutionScenarioV2.TIMEOUT)

    with pytest.raises(ValueError, match="invalid provider execution request"):
        executor.execute(forged)
    assert executor.history == ()


def test_exact_public_exports() -> None:
    import pastila_scout.provider_execution_testing_v2 as package

    assert package.__all__ == ("ExecutionScenarioV2", "FakeProviderExecutorV2")


def test_testing_dependency_direction_and_capability_absence() -> None:
    forbidden_imports = {
        "aiohttp",
        "asyncio",
        "httpx",
        "logging",
        "openai",
        "requests",
        "sqlite3",
        "subprocess",
        "threading",
    }
    forbidden_names = {
        "API_KEY",
        "backoff",
        "credential",
        "environment",
        "random",
        "retry",
        "sleep",
        "stream",
        "telemetry",
    }
    for path in PACKAGE.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        assert not any(item.split(".", 1)[0] in forbidden_imports for item in imports)
        assert "provider_adapters_v2" not in source
        assert "provider_composition_v2" not in source
        assert not any(name.lower() in source.lower() for name in forbidden_names)
    contracts = ROOT / "src" / "pastila_scout" / "provider_execution_v2"
    assert all(
        "provider_execution_testing_v2" not in path.read_text(encoding="utf-8")
        for path in contracts.glob("*.py")
    )


def test_clean_process_import_is_isolated() -> None:
    code = (
        "import importlib,json,sys;"
        "importlib.import_module('pastila_scout.provider_execution_testing_v2');"
        "print(json.dumps(sorted(sys.modules)))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    loaded = tuple(__import__("json").loads(completed.stdout))

    assert completed.stderr == ""
    assert not any("provider_adapters_v2" in item for item in loaded)
    assert "pastila_scout.provider_composition_v2" not in loaded
    assert not any("editor.script_composer" in item for item in loaded)

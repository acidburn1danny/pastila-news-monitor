"""Offline tests for the opt-in Scout workflow execution migration."""

from __future__ import annotations

import ast
import copy
import pickle
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

import pastila_scout.scout_workflow_execution_v1 as public_api
from pastila_scout.provider_adapters_v2.ollama import OllamaProviderAdapter
from pastila_scout.provider_adapters_v2.openai import OpenAIProviderAdapter
from pastila_scout.provider_execution_v2 import (
    ExecutionContextV2,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_selection_v1 import (
    ProviderChoiceV1,
    ProviderExecutorRegistrationV1,
    ProviderSelectionConfigV1,
    ProviderSelectorV1,
)
from pastila_scout.provider_v2 import (
    ProviderMessageInputV2,
    ProviderRequestIntentV2,
    ProviderRequestUnitInputV2,
    build_provider_request_envelope,
)
from pastila_scout.scout_runtime_execution_v1 import (
    ScoutRuntimeExecutionBridgeV1,
    ScoutRuntimeRequestV1,
    ScoutRuntimeResultV1,
)
from pastila_scout.scout_runtime_v1 import (
    ScoutCancellationV1,
    ScoutRuntimeCompositionV1,
    ScoutRuntimeConfigV1,
    ScoutRuntimeOptionsV1,
)
from pastila_scout.scout_workflow_execution_v1 import (
    ScoutWorkflowExecutionError,
    ScoutWorkflowExecutionV1,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "scout_workflow_execution_v1"
NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
ZERO = "0" * 64
IDENTITY = f"scout:workflow-artifact:{ZERO}"


@dataclass
class _Executor:
    result: ProviderExecutionResultV2
    calls: list[ProviderExecutionRequestV2]

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        self.calls.append(request)
        return self.result


@dataclass
class _LegacyWorkflow:
    result: ScoutRuntimeResultV1
    calls: list[ScoutRuntimeRequestV1]

    def execute(self, request: ScoutRuntimeRequestV1) -> ScoutRuntimeResultV1:
        self.calls.append(request)
        return self.result


def _request(choice: ProviderChoiceV1) -> ProviderExecutionRequestV2:
    descriptor = (
        OpenAIProviderAdapter.descriptor
        if choice is ProviderChoiceV1.OPENAI
        else OllamaProviderAdapter.descriptor
    )
    intent = ProviderRequestIntentV2(
        execution_plan_reference=f"plan:{choice.value}",
        execution_plan_identity=IDENTITY,
        execution_plan_fingerprint=ZERO,
        draft_reference=f"draft:{choice.value}",
        draft_fingerprint=ZERO,
        request_units=(
            ProviderRequestUnitInputV2(
                source_request_reference=f"source:{choice.value}",
                ordinal=0,
                messages=(
                    ProviderMessageInputV2(
                        role="generation", content="Execute request.", ordinal=0
                    ),
                ),
            ),
        ),
    )
    return ProviderExecutionRequestV2(
        provider=descriptor,
        request_intent=intent,
        request_envelope=build_provider_request_envelope(intent, descriptor),
        context=ExecutionContextV2(
            request_id=f"scout-workflow:{choice.value}", requested_at=NOW
        ),
        timeout_policy=TimeoutPolicyV2(timeout_seconds=11),
    )


def _result(request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
    return ProviderExecutionResultV2(
        request_id=request.context.request_id,
        provider_id=request.provider.provider_id,
        request_envelope_identity=request.request_envelope.identity,
        outcome=ExecutionOutcomeV2.PROVIDER_FAILURE,
        finished_at=NOW,
        failure_code="test-failure",
        failure_message="Deterministic provider-neutral failure.",
    )


def _workflow(choice: ProviderChoiceV1):
    request = _request(choice)
    selected = _Executor(_result(request), [])
    other_choice = (
        ProviderChoiceV1.OLLAMA
        if choice is ProviderChoiceV1.OPENAI
        else ProviderChoiceV1.OPENAI
    )
    other_request = _request(other_choice)
    other = _Executor(_result(other_request), [])
    executors = {choice: selected, other_choice: other}
    selector = ProviderSelectorV1(
        ProviderSelectionConfigV1(provider=choice),
        tuple(
            ProviderExecutorRegistrationV1(provider, executors[provider])
            for provider in (ProviderChoiceV1.OPENAI, ProviderChoiceV1.OLLAMA)
        ),
    )
    composition = ScoutRuntimeCompositionV1(
        selector,
        ScoutRuntimeConfigV1("scout-config:workflow-test"),
        ScoutRuntimeOptionsV1("scout-options:workflow-test"),
        ScoutCancellationV1(False),
    )
    bridge = ScoutRuntimeExecutionBridgeV1(composition)
    legacy_result = ScoutRuntimeResultV1(selected.result)
    legacy = _LegacyWorkflow(legacy_result, [])
    return (
        ScoutWorkflowExecutionV1(legacy, bridge),
        ScoutRuntimeRequestV1(True, request),
        legacy,
        selected,
        other,
        selector,
    )


def _downstream(result: ScoutRuntimeResultV1) -> tuple[object, ...]:
    provider = result.provider_result
    return (
        provider.request_id,
        provider.provider_id,
        provider.outcome,
        provider.failure_code,
        provider.failure_message,
    )


def test_public_api_is_small_and_application_owned() -> None:
    assert public_api.__all__ == (
        "LegacyScoutWorkflowExecutionV1",
        "ScoutWorkflowExecutionError",
        "ScoutWorkflowExecutionV1",
    )


def test_legacy_workflow_remains_the_default_and_bridge_is_not_called() -> None:
    workflow, request, legacy, selected, other, _ = _workflow(ProviderChoiceV1.OPENAI)

    result = workflow.execute(request)

    assert result is legacy.result
    assert legacy.calls == [request]
    assert selected.calls == other.calls == []


@pytest.mark.parametrize("choice", (ProviderChoiceV1.OPENAI, ProviderChoiceV1.OLLAMA))
def test_opt_in_executes_selected_provider_once_through_bridge(choice) -> None:
    workflow, request, legacy, selected, other, selector = _workflow(choice)

    result = workflow.execute_provider_neutral(request)

    assert selected.calls == [request.provider_request]
    assert other.calls == []
    assert legacy.calls == []
    assert workflow.runtime_bridge.composition.selector is selector
    assert selector.executor is selected
    assert result.provider_result == selected.result
    assert result.provider_result is not selected.result


@pytest.mark.parametrize("choice", (ProviderChoiceV1.OPENAI, ProviderChoiceV1.OLLAMA))
def test_legacy_and_neutral_paths_have_identical_downstream_output(choice) -> None:
    workflow, request, _, selected, other, _ = _workflow(choice)

    legacy_output = _downstream(workflow.execute(request))
    neutral_output = _downstream(workflow.execute_provider_neutral(request))

    assert legacy_output == neutral_output
    assert len(selected.calls) == 1
    assert other.calls == []


def test_request_authority_is_reused_at_workflow_bridge_boundary(monkeypatch) -> None:
    workflow, request, _, selected, _, _ = _workflow(ProviderChoiceV1.OLLAMA)
    observed = []
    original_execute = ScoutRuntimeExecutionBridgeV1.execute

    def observe(bridge, supplied):
        observed.append(supplied)
        return original_execute(bridge, supplied)

    monkeypatch.setattr(ScoutRuntimeExecutionBridgeV1, "execute", observe)

    workflow.execute_provider_neutral(request)

    assert observed == [request]
    assert observed[0] is request
    assert selected.calls == [request.provider_request]


def test_repeated_workflow_is_deterministic_with_one_execution_per_call() -> None:
    workflow, request, _, selected, other, _ = _workflow(ProviderChoiceV1.OPENAI)

    outputs = tuple(
        _downstream(workflow.execute_provider_neutral(request)) for _ in range(3)
    )

    assert outputs[0] == outputs[1] == outputs[2]
    assert len(selected.calls) == 3
    assert other.calls == []


@pytest.mark.parametrize("invalid", (None, object(), "request"))
def test_invalid_request_executes_neither_path(invalid) -> None:
    workflow, _, legacy, selected, other, _ = _workflow(ProviderChoiceV1.OPENAI)

    with pytest.raises(ScoutWorkflowExecutionError, match="workflow request"):
        workflow.execute_provider_neutral(invalid)  # type: ignore[arg-type]

    assert legacy.calls == []
    assert selected.calls == other.calls == []


def test_invalid_dependencies_are_rejected_without_execution() -> None:
    workflow, _, legacy, selected, other, _ = _workflow(ProviderChoiceV1.OPENAI)
    with pytest.raises(ScoutWorkflowExecutionError, match="legacy Scout workflow"):
        ScoutWorkflowExecutionV1(object(), workflow.runtime_bridge)  # type: ignore[arg-type]
    with pytest.raises(ScoutWorkflowExecutionError, match="runtime execution bridge"):
        ScoutWorkflowExecutionV1(legacy, object())  # type: ignore[arg-type]
    assert legacy.calls == []
    assert selected.calls == other.calls == []


@pytest.mark.parametrize(
    "dependency",
    (
        type("Missing", (), {})(),
        type("WrongCount", (), {"execute": lambda self: None})(),
        type("WrongName", (), {"execute": lambda self, value: None})(),
        type("Static", (), {"execute": staticmethod(lambda request: None)})(),
        type("Class", (), {"execute": classmethod(lambda cls, request: None)})(),
        type(
            "Property", (), {"execute": property(lambda self: lambda request: None)}
        )(),
    ),
)
def test_malformed_legacy_protocols_are_rejected_without_invocation(dependency) -> None:
    workflow, _, legacy, selected, other, _ = _workflow(ProviderChoiceV1.OPENAI)

    with pytest.raises(ScoutWorkflowExecutionError, match="legacy Scout workflow"):
        ScoutWorkflowExecutionV1(dependency, workflow.runtime_bridge)

    assert legacy.calls == []
    assert selected.calls == other.calls == []


def test_dynamic_legacy_attribute_is_rejected_without_lookup() -> None:
    workflow, _, _, selected, other, _ = _workflow(ProviderChoiceV1.OPENAI)

    class Dynamic:
        lookups = 0

        def __getattr__(self, name):
            self.lookups += 1
            return lambda request: None

    dependency = Dynamic()
    with pytest.raises(ScoutWorkflowExecutionError, match="legacy Scout workflow"):
        ScoutWorkflowExecutionV1(dependency, workflow.runtime_bridge)
    assert dependency.lookups == 0
    assert selected.calls == other.calls == []


def test_copy_deepcopy_repr_equality_and_pickle_do_not_traverse_dependencies() -> None:
    workflow, _, legacy, selected, other, _ = _workflow(ProviderChoiceV1.OLLAMA)

    shallow = copy.copy(workflow)
    deep = copy.deepcopy(workflow)

    assert shallow.legacy_workflow is deep.legacy_workflow is legacy
    assert shallow.runtime_bridge is deep.runtime_bridge is workflow.runtime_bridge
    assert shallow == deep == workflow
    assert repr(workflow) == (
        "ScoutWorkflowExecutionV1("
        "legacy_workflow=<injected LegacyScoutWorkflowExecutionV1>, "
        "runtime_bridge=<injected ScoutRuntimeExecutionBridgeV1>)"
    )
    with pytest.raises(
        TypeError, match="Scout workflow execution boundary does not support pickle"
    ):
        pickle.dumps(workflow)
    assert selected.calls == other.calls == []


def test_copied_invalid_retained_state_fails_closed() -> None:
    workflow, _, _, selected, other, _ = _workflow(ProviderChoiceV1.OPENAI)
    object.__setattr__(workflow, "legacy_workflow", object())

    for operation in (
        lambda: copy.copy(workflow),
        lambda: copy.deepcopy(workflow),
        lambda: repr(workflow),
        lambda: pickle.dumps(workflow),
    ):
        with pytest.raises(ScoutWorkflowExecutionError):
            operation()
    assert selected.calls == other.calls == []


def test_legacy_exception_is_replaced_by_safe_isolated_error() -> None:
    workflow, request, _, selected, other, _ = _workflow(ProviderChoiceV1.OPENAI)

    class FailingLegacy:
        def execute(self, request: ScoutRuntimeRequestV1) -> ScoutRuntimeResultV1:
            raise RuntimeError("raw provider secret")

    failing_workflow = ScoutWorkflowExecutionV1(
        FailingLegacy(), workflow.runtime_bridge
    )
    with pytest.raises(
        ScoutWorkflowExecutionError, match="legacy Scout workflow failed"
    ) as captured:
        failing_workflow.execute(request)

    assert "secret" not in str(captured.value)
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True
    assert selected.calls == other.calls == []


def test_runtime_bridge_exception_is_replaced_without_legacy_fallback(
    monkeypatch,
) -> None:
    workflow, request, legacy, selected, other, _ = _workflow(ProviderChoiceV1.OLLAMA)

    def fail(bridge, supplied):
        raise RuntimeError("raw lower secret")

    monkeypatch.setattr(ScoutRuntimeExecutionBridgeV1, "execute", fail)
    with pytest.raises(
        ScoutWorkflowExecutionError, match="Scout runtime execution bridge failed"
    ) as captured:
        workflow.execute_provider_neutral(request)

    assert "secret" not in str(captured.value)
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True
    assert legacy.calls == []
    assert selected.calls == other.calls == []


def test_import_is_passive_and_has_no_provider_implementation_dependency() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-W",
            "error",
            "-c",
            "import pastila_scout.scout_workflow_execution_v1",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0
    assert completed.stdout == completed.stderr == ""

    forbidden = {
        "openai",
        "provider_execution_openai_v2",
        "provider_execution_ollama_v1",
        "poller",
        "http_client",
        "cli",
    }
    imports = set()
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports.update(
            (node.module or "").split(".")[-1]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        imports.update(
            alias.name.split(".")[-1]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
    assert not imports & forbidden

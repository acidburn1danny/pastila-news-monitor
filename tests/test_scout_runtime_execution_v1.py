"""Offline tests for the first explicit Scout provider-neutral execution path."""

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

import pastila_scout.scout_runtime_execution_v1 as public_api
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
    ProviderFinishReasonV2,
    ProviderMessageInputV2,
    ProviderOutputInputV2,
    ProviderRequestIntentV2,
    ProviderRequestUnitInputV2,
    ProviderResultProjectionV2,
    ProviderResultStatusV2,
    build_provider_request_envelope,
)
from pastila_scout.scout_runtime_execution_v1 import (
    ScoutRuntimeExecutionBridgeV1,
    ScoutRuntimeExecutionError,
    ScoutRuntimeRequestV1,
    ScoutRuntimeResultV1,
)
from pastila_scout.scout_runtime_v1 import (
    ScoutCancellationV1,
    ScoutRuntimeCompositionV1,
    ScoutRuntimeConfigV1,
    ScoutRuntimeOptionsV1,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "scout_runtime_execution_v1"
NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
ZERO = "0" * 64
IDENTITY = f"scout:test-artifact:{ZERO}"
EXPECTED_API = (
    "ScoutRuntimeExecutionBridgeV1",
    "ScoutRuntimeExecutionError",
    "ScoutRuntimeRequestV1",
    "ScoutRuntimeResultV1",
)


@dataclass
class _FixedExecutor:
    result: ProviderExecutionResultV2 | None = None
    calls: list[ProviderExecutionRequestV2] | None = None

    def __post_init__(self) -> None:
        self.calls = []

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        assert self.calls is not None
        self.calls.append(request)
        assert self.result is not None
        return self.result


def _provider_request(
    choice: ProviderChoiceV1, *, units: int = 1
) -> ProviderExecutionRequestV2:
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
        request_units=tuple(
            ProviderRequestUnitInputV2(
                source_request_reference=f"source:{choice.value}:{ordinal}",
                ordinal=ordinal,
                messages=(
                    ProviderMessageInputV2(
                        role="generation",
                        content=f"Execute neutral request {ordinal}.",
                        ordinal=0,
                    ),
                ),
            )
            for ordinal in range(units)
        ),
    )
    return ProviderExecutionRequestV2(
        provider=descriptor,
        request_intent=intent,
        request_envelope=build_provider_request_envelope(intent, descriptor),
        context=ExecutionContextV2(
            request_id=f"scout-runtime:{choice.value}", requested_at=NOW
        ),
        timeout_policy=TimeoutPolicyV2(timeout_seconds=10),
    )


def _provider_result(request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
    return ProviderExecutionResultV2(
        request_id=request.context.request_id,
        provider_id=request.provider.provider_id,
        request_envelope_identity=request.request_envelope.identity,
        outcome=ExecutionOutcomeV2.PROVIDER_FAILURE,
        finished_at=NOW,
        failure_code="test-provider-failure",
        failure_message="Deterministic test provider result.",
    )


def _completed_result(
    request: ProviderExecutionRequestV2,
    references: tuple[str, ...],
) -> ProviderExecutionResultV2:
    return ProviderExecutionResultV2(
        request_id=request.context.request_id,
        provider_id=request.provider.provider_id,
        request_envelope_identity=request.request_envelope.identity,
        outcome=ExecutionOutcomeV2.COMPLETED,
        finished_at=NOW,
        provider_result=ProviderResultProjectionV2(
            status=ProviderResultStatusV2.SUCCESS,
            outputs=tuple(
                ProviderOutputInputV2(
                    source_request_reference=reference,
                    ordinal=ordinal,
                    generated_text=f"Output {ordinal}",
                    finish_reason=ProviderFinishReasonV2.COMPLETED,
                )
                for ordinal, reference in enumerate(references)
            ),
        ),
    )


def _bridge(
    choice: ProviderChoiceV1,
    *,
    request: ProviderExecutionRequestV2 | None = None,
    result: ProviderExecutionResultV2 | None = None,
):
    request = request or _provider_request(choice)
    selected = _FixedExecutor(result=result or _provider_result(request))
    other_request = _provider_request(
        ProviderChoiceV1.OLLAMA
        if choice is ProviderChoiceV1.OPENAI
        else ProviderChoiceV1.OPENAI
    )
    other = _FixedExecutor(result=_provider_result(other_request))
    executors = {
        choice: selected,
        (
            ProviderChoiceV1.OLLAMA
            if choice is ProviderChoiceV1.OPENAI
            else ProviderChoiceV1.OPENAI
        ): other,
    }
    selector = ProviderSelectorV1(
        ProviderSelectionConfigV1(provider=choice),
        tuple(
            ProviderExecutorRegistrationV1(provider, executors[provider])
            for provider in (ProviderChoiceV1.OPENAI, ProviderChoiceV1.OLLAMA)
        ),
    )
    composition = ScoutRuntimeCompositionV1(
        selector,
        ScoutRuntimeConfigV1("scout-config:execution-test"),
        ScoutRuntimeOptionsV1("scout-options:execution-test"),
        ScoutCancellationV1(False),
    )
    return ScoutRuntimeExecutionBridgeV1(composition), request, selected, other


def test_public_api_is_exact_and_contains_no_provider_implementation() -> None:
    assert public_api.__all__ == EXPECTED_API


@pytest.mark.parametrize("choice", (ProviderChoiceV1.OPENAI, ProviderChoiceV1.OLLAMA))
def test_executes_selected_provider_exactly_once_through_selector(choice) -> None:
    bridge, provider_request, selected, other = _bridge(choice)
    scout_request = ScoutRuntimeRequestV1(True, provider_request)

    result = bridge.execute(scout_request)

    assert isinstance(result, ScoutRuntimeResultV1)
    assert result.provider_result == selected.result
    assert result.provider_result is not selected.result
    assert selected.calls is not None and len(selected.calls) == 1
    assert selected.calls[0] == provider_request
    assert other.calls == []
    assert bridge.composition.selector.executor is selected


@pytest.mark.parametrize("opt_in", (False, 0, 1, None, "true"))
def test_execution_requires_explicit_exact_true_opt_in(opt_in) -> None:
    _, request, selected, _ = _bridge(ProviderChoiceV1.OPENAI)
    with pytest.raises(ScoutRuntimeExecutionError, match="explicit opt-in"):
        ScoutRuntimeRequestV1(opt_in, request)  # type: ignore[arg-type]
    assert selected.calls == []


@pytest.mark.parametrize("composition", (None, object(), "runtime"))
def test_invalid_runtime_composition_is_rejected(composition) -> None:
    with pytest.raises(ScoutRuntimeExecutionError, match="runtime composition"):
        ScoutRuntimeExecutionBridgeV1(composition)  # type: ignore[arg-type]


def test_invalid_selector_is_rejected_without_execution() -> None:
    bridge, _, selected, other = _bridge(ProviderChoiceV1.OPENAI)
    composition = bridge.composition
    object.__setattr__(composition, "selector", object())

    with pytest.raises(ScoutRuntimeExecutionError, match="provider selector"):
        ScoutRuntimeExecutionBridgeV1(composition)
    assert selected.calls == other.calls == []


def test_copied_invalid_request_is_rejected_before_executor_call() -> None:
    bridge, provider_request, selected, _ = _bridge(ProviderChoiceV1.OPENAI)
    request = ScoutRuntimeRequestV1(True, provider_request)
    object.__setattr__(request, "provider_execution_opt_in", False)

    with pytest.raises(ScoutRuntimeExecutionError, match="explicit opt-in"):
        bridge.execute(request)
    assert selected.calls == []


def test_result_lineage_mismatch_is_rejected_without_retry() -> None:
    bridge, provider_request, selected, _ = _bridge(ProviderChoiceV1.OPENAI)
    assert selected.result is not None
    selected.result = selected.result.model_copy(update={"request_id": "wrong-request"})

    with pytest.raises(ScoutRuntimeExecutionError, match="lineage mismatch"):
        bridge.execute(ScoutRuntimeRequestV1(True, provider_request))
    assert selected.calls is not None and len(selected.calls) == 1


def test_copied_invalid_reordered_result_is_rejected_without_retry() -> None:
    request = _provider_request(ProviderChoiceV1.OPENAI, units=2)
    references = tuple(
        item.source_request_reference for item in request.request_envelope.request_units
    )
    valid_result = _completed_result(request, references)
    assert valid_result.provider_result is not None
    reordered_projection = valid_result.provider_result.model_copy(
        update={"outputs": tuple(reversed(valid_result.provider_result.outputs))}
    )
    copied_invalid_result = valid_result.model_copy(
        update={"provider_result": reordered_projection}
    )
    bridge, _, selected, other = _bridge(
        ProviderChoiceV1.OPENAI,
        request=request,
        result=copied_invalid_result,
    )

    with pytest.raises(
        ScoutRuntimeExecutionError, match="invalid Scout provider execution result"
    ):
        bridge.execute(ScoutRuntimeRequestV1(True, request))

    assert selected.calls is not None and len(selected.calls) == 1
    assert other.calls == []


@pytest.mark.parametrize("case", ("foreign", "missing", "extra"))
def test_complete_output_lineage_rejects_foreign_missing_and_extra_units(case) -> None:
    units = 2 if case == "missing" else 1
    request = _provider_request(ProviderChoiceV1.OPENAI, units=units)
    references = tuple(
        item.source_request_reference for item in request.request_envelope.request_units
    )
    if case == "foreign":
        references = ("foreign-output-reference",)
    elif case == "missing":
        references = references[:1]
    else:
        references = (*references, "extra-output-reference")
    result = _completed_result(request, references)
    bridge, _, selected, other = _bridge(
        ProviderChoiceV1.OPENAI, request=request, result=result
    )

    with pytest.raises(ScoutRuntimeExecutionError, match="output lineage mismatch"):
        bridge.execute(ScoutRuntimeRequestV1(True, request))

    assert selected.calls is not None and len(selected.calls) == 1
    assert other.calls == []


def test_selected_executor_substitution_is_rejected_before_execution() -> None:
    bridge, request, selected, other = _bridge(ProviderChoiceV1.OPENAI)
    replacement = _FixedExecutor(result=_provider_result(request))
    object.__setattr__(bridge.composition.selector, "executor", replacement)

    with pytest.raises(ScoutRuntimeExecutionError, match="authority changed"):
        bridge.execute(ScoutRuntimeRequestV1(True, request))

    assert selected.calls == other.calls == replacement.calls == []


def test_executor_exception_is_isolated_without_retry_or_fallback() -> None:
    bridge, provider_request, selected, other = _bridge(ProviderChoiceV1.OPENAI)
    selected.result = None
    scout_request = ScoutRuntimeRequestV1(True, provider_request)

    with pytest.raises(ScoutRuntimeExecutionError, match="executor failed") as captured:
        bridge.execute(scout_request)

    assert selected.calls is not None and len(selected.calls) == 1
    assert other.calls == []
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True
    authorities = (
        bridge,
        bridge.composition,
        selected,
        other,
        provider_request,
        scout_request,
    )
    traceback = captured.value.__traceback__
    retained = []
    while traceback is not None:
        if traceback.tb_frame.f_globals.get("__name__", "").startswith(
            "pastila_scout.scout_runtime_execution_v1"
        ):
            retained.extend(
                value
                for value in tuple(traceback.tb_frame.f_locals.values())
                if any(value is authority for authority in authorities)
            )
        traceback = traceback.tb_next
    assert retained == []


def test_repeated_execution_is_deterministic_with_one_call_per_opt_in() -> None:
    bridge, provider_request, selected, _ = _bridge(ProviderChoiceV1.OLLAMA)
    request = ScoutRuntimeRequestV1(True, provider_request)

    results = tuple(bridge.execute(request) for _ in range(3))

    assert results[0] == results[1] == results[2]
    assert selected.calls is not None and len(selected.calls) == 3


def test_request_and_result_copy_deepcopy_and_pickle_revalidate_state() -> None:
    _, provider_request, selected, _ = _bridge(ProviderChoiceV1.OPENAI)
    request = ScoutRuntimeRequestV1(True, provider_request)
    assert selected.result is not None
    result = ScoutRuntimeResultV1(selected.result)
    for value in (request, result):
        assert copy.copy(value) == value
        assert copy.deepcopy(value) == value
        assert pickle.loads(pickle.dumps(value)) == value

    object.__setattr__(request, "provider_execution_opt_in", False)
    for operation in (
        lambda: copy.copy(request),
        lambda: copy.deepcopy(request),
        lambda: pickle.dumps(request),
    ):
        with pytest.raises(ScoutRuntimeExecutionError):
            operation()


def test_bridge_copy_preserves_composition_and_pickle_is_safely_unsupported() -> None:
    bridge, _, selected, other = _bridge(ProviderChoiceV1.OLLAMA)
    shallow = copy.copy(bridge)
    deep = copy.deepcopy(bridge)

    assert shallow.composition is deep.composition is bridge.composition
    assert shallow == deep == bridge
    with pytest.raises(
        TypeError, match="Scout runtime execution bridge does not support pickle"
    ):
        pickle.dumps(bridge)
    assert selected.calls == other.calls == []


def test_import_is_passive_and_legacy_scout_does_not_import_new_path() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-W",
            "error",
            "-c",
            (
                "import sys; import pastila_scout.poller; "
                "assert 'pastila_scout.scout_runtime_execution_v1' not in sys.modules"
            ),
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

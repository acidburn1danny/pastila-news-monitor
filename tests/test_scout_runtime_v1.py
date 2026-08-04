"""Focused offline tests for the inert Scout runtime composition boundary."""

from __future__ import annotations

import ast
import copy
import pickle
import subprocess
import sys
from dataclasses import FrozenInstanceError, dataclass, fields
from pathlib import Path

import pytest

import pastila_scout.scout_runtime_v1 as public_api
from pastila_scout.provider_execution_v2 import (
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_selection_v1 import (
    ProviderChoiceV1,
    ProviderExecutorRegistrationV1,
    ProviderSelectionConfigV1,
    ProviderSelectorV1,
)
from pastila_scout.scout_runtime_v1 import (
    ScoutCancellationV1,
    ScoutRuntimeCompositionError,
    ScoutRuntimeCompositionV1,
    ScoutRuntimeConfigV1,
    ScoutRuntimeOptionsV1,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "scout_runtime_v1"
EXPECTED_API = (
    "ScoutCancellationV1",
    "ScoutRuntimeCompositionError",
    "ScoutRuntimeCompositionV1",
    "ScoutRuntimeConfigV1",
    "ScoutRuntimeOptionsV1",
)


@dataclass
class _InertExecutor:
    calls: int = 0

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        del request
        self.calls += 1
        raise AssertionError("runtime composition must not execute providers")


def _selector() -> tuple[ProviderSelectorV1, tuple[_InertExecutor, _InertExecutor]]:
    openai = _InertExecutor()
    ollama = _InertExecutor()
    selector = ProviderSelectorV1(
        ProviderSelectionConfigV1(provider=ProviderChoiceV1.OPENAI),
        (
            ProviderExecutorRegistrationV1(ProviderChoiceV1.OPENAI, openai),
            ProviderExecutorRegistrationV1(ProviderChoiceV1.OLLAMA, ollama),
        ),
    )
    return selector, (openai, ollama)


def _composition() -> tuple[ScoutRuntimeCompositionV1, tuple[_InertExecutor, ...]]:
    selector, executors = _selector()
    return (
        ScoutRuntimeCompositionV1(
            selector=selector,
            config=ScoutRuntimeConfigV1(configuration_identity="scout-config:test"),
            options=ScoutRuntimeOptionsV1(options_identity="scout-options:test"),
            cancellation=ScoutCancellationV1(cancellation_requested=False),
        ),
        executors,
    )


def test_public_api_is_intentionally_small_and_composition_only() -> None:
    assert public_api.__all__ == EXPECTED_API
    assert tuple(item.name for item in fields(ScoutRuntimeCompositionV1)) == (
        "selector",
        "config",
        "options",
        "cancellation",
    )


def test_valid_composition_preserves_selector_and_reconstructs_owned_models() -> None:
    selector, executors = _selector()
    config = ScoutRuntimeConfigV1(configuration_identity="scout-config:test")
    options = ScoutRuntimeOptionsV1(options_identity="scout-options:test")
    cancellation = ScoutCancellationV1(cancellation_requested=False)

    composition = ScoutRuntimeCompositionV1(selector, config, options, cancellation)

    assert composition.selector is selector
    assert composition.config == config and composition.config is not config
    assert composition.options == options and composition.options is not options
    assert composition.cancellation == cancellation
    assert composition.cancellation is not cancellation
    assert tuple(item.calls for item in executors) == (0, 0)


@pytest.mark.parametrize("selector", (None, object(), "openai"))
def test_invalid_selector_is_rejected_without_provider_activity(selector) -> None:
    with pytest.raises(ScoutRuntimeCompositionError, match="provider selector"):
        ScoutRuntimeCompositionV1(
            selector=selector,  # type: ignore[arg-type]
            config=ScoutRuntimeConfigV1("scout-config:test"),
            options=ScoutRuntimeOptionsV1("scout-options:test"),
            cancellation=ScoutCancellationV1(False),
        )


@pytest.mark.parametrize(
    ("dependency", "replacement", "message"),
    (
        ("config", "configuration_identity", "configuration"),
        ("options", "options_identity", "options"),
        ("cancellation", "cancellation_requested", "cancellation"),
    ),
)
def test_copied_invalid_dependencies_are_reconstructed_and_rejected(
    dependency: str, replacement: str, message: str
) -> None:
    selector, executors = _selector()
    values = {
        "config": ScoutRuntimeConfigV1("scout-config:test"),
        "options": ScoutRuntimeOptionsV1("scout-options:test"),
        "cancellation": ScoutCancellationV1(False),
    }
    object.__setattr__(
        values[dependency], replacement, 1 if dependency != "cancellation" else 0
    )

    with pytest.raises(ScoutRuntimeCompositionError, match=message) as captured:
        ScoutRuntimeCompositionV1(selector=selector, **values)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None
    assert captured.value.__suppress_context__ is True
    assert tuple(item.calls for item in executors) == (0, 0)


@pytest.mark.parametrize(
    "factory",
    (
        lambda: ScoutRuntimeConfigV1(" "),
        lambda: ScoutRuntimeOptionsV1(" padded "),
        lambda: ScoutCancellationV1(0),
    ),
)
def test_strict_models_reject_coercion_and_invalid_values(factory) -> None:
    with pytest.raises(ScoutRuntimeCompositionError):
        factory()


def test_models_and_composition_are_immutable() -> None:
    composition, _ = _composition()
    for value, attribute in (
        (composition, "config"),
        (composition.config, "configuration_identity"),
        (composition.options, "options_identity"),
        (composition.cancellation, "cancellation_requested"),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(value, attribute, None)


def test_equality_is_deterministic_and_instances_have_no_shared_state() -> None:
    selector, executors = _selector()
    first = ScoutRuntimeCompositionV1(
        selector,
        ScoutRuntimeConfigV1("scout-config:test"),
        ScoutRuntimeOptionsV1("scout-options:test"),
        ScoutCancellationV1(False),
    )
    second = ScoutRuntimeCompositionV1(
        selector,
        ScoutRuntimeConfigV1("scout-config:test"),
        ScoutRuntimeOptionsV1("scout-options:test"),
        ScoutCancellationV1(False),
    )

    assert first == second
    assert first is not second
    assert tuple(item.calls for item in executors) == (0, 0)


def test_repr_equality_and_copy_do_not_invoke_or_copy_injected_dependencies() -> None:
    selector, executors = _selector()
    composition = ScoutRuntimeCompositionV1(
        selector,
        ScoutRuntimeConfigV1("scout-config:test"),
        ScoutRuntimeOptionsV1("scout-options:test"),
        ScoutCancellationV1(False),
    )

    rendered = repr(composition)
    shallow = copy.copy(composition)
    deep = copy.deepcopy(composition)

    assert "<injected ProviderSelectorV1>" in rendered
    assert "_InertExecutor" not in rendered
    assert shallow == deep == composition
    assert shallow.selector is deep.selector is selector
    assert tuple(item.calls for item in executors) == (0, 0)


def test_models_revalidate_copy_deepcopy_and_pickle_round_trips() -> None:
    values = (
        ScoutRuntimeConfigV1("scout-config:test"),
        ScoutRuntimeOptionsV1("scout-options:test"),
        ScoutCancellationV1(False),
    )
    for value in values:
        assert copy.copy(value) == value
        assert copy.deepcopy(value) == value
        assert pickle.loads(pickle.dumps(value)) == value


def test_corrupted_retained_state_fails_repr_copy_deepcopy_and_pickle() -> None:
    composition, _ = _composition()
    object.__setattr__(composition.config, "configuration_identity", " ")
    for operation in (
        lambda: repr(composition),
        lambda: copy.copy(composition),
        lambda: copy.deepcopy(composition),
    ):
        with pytest.raises(ScoutRuntimeCompositionError):
            operation()
    with pytest.raises(ScoutRuntimeCompositionError):
        pickle.dumps(composition)

    options = ScoutRuntimeOptionsV1("scout-options:test")
    object.__setattr__(options, "options_identity", 1)
    for operation in (
        lambda: repr(options),
        lambda: copy.copy(options),
        lambda: copy.deepcopy(options),
        lambda: pickle.dumps(options),
    ):
        with pytest.raises(ScoutRuntimeCompositionError):
            operation()


def test_composition_pickle_is_explicitly_unsupported_without_touching_selector() -> (
    None
):
    composition, executors = _composition()
    with pytest.raises(
        TypeError, match="Scout runtime composition does not support pickle"
    ):
        pickle.dumps(composition)
    assert tuple(item.calls for item in executors) == (0, 0)


def test_public_validation_error_traceback_retains_no_injected_dependency() -> None:
    selector, _ = _selector()
    config = ScoutRuntimeConfigV1("scout-config:test")
    options = ScoutRuntimeOptionsV1("scout-options:test")
    cancellation = ScoutCancellationV1(False)
    object.__setattr__(config, "configuration_identity", " ")
    dependencies = (selector, config, options, cancellation)

    with pytest.raises(ScoutRuntimeCompositionError) as captured:
        ScoutRuntimeCompositionV1(selector, config, options, cancellation)

    traceback = captured.value.__traceback__
    retained = []
    while traceback is not None:
        if traceback.tb_frame.f_globals.get("__name__", "").startswith(
            "pastila_scout.scout_runtime_v1"
        ):
            retained.extend(
                value
                for value in tuple(traceback.tb_frame.f_locals.values())
                if any(value is dependency for dependency in dependencies)
            )
        traceback = traceback.tb_next
    assert retained == []
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True


def test_import_is_passive_and_has_no_scout_or_provider_implementation_dependency() -> (
    None
):
    completed = subprocess.run(
        [sys.executable, "-W", "error", "-c", "import pastila_scout.scout_runtime_v1"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0
    assert completed.stdout == completed.stderr == ""

    forbidden = {
        "config",
        "poller",
        "http_client",
        "openai",
        "provider_execution_openai_v2",
        "provider_execution_ollama_v1",
        "socket",
        "threading",
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

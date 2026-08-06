"""Focused verification for the private Editor command-time composition root."""

from __future__ import annotations

import copy
import inspect
import pickle
import sys
from pathlib import Path

import httpx
import pytest

from pastila_scout.editor_application_v1 import (
    runtime_composition as application_runtime,
)
from pastila_scout.editor_application_v1.application import (
    EditorApplicationCoordinatorV1,
)
from pastila_scout.editor_application_v1.errors import (
    EditorApplicationCoordinatorError,
)
from pastila_scout.editor_generation_runtime_v1 import (
    EditorGenerationRuntimeCompositionError,
    EditorGenerationRuntimeSessionFactoryV1,
)
from pastila_scout.editor_generation_runtime_v1 import composition as runtime
from pastila_scout.editor_operational_execution_v1 import (
    EditorOperationalExecutionCoordinatorV1,
)
from pastila_scout.editor_operational_execution_v1.production import (
    _create_editor_operational_execution_coordinator_v1,
    _EditorControlledGeneratorFactoryV1Impl,
)
from pastila_scout.provider_runtime_openai_v2 import OpenAIRuntimeComposerV2
from pastila_scout.provider_runtime_openai_v2.production import (
    _create_environment_openai_runtime_composer_v2,
)

IMPLEMENTATION_SCOPE = {
    "src/pastila_scout/provider_runtime_openai_v2/production.py",
    "src/pastila_scout/editor_generation_runtime_v1/composition.py",
    "src/pastila_scout/editor_operational_execution_v1/production.py",
    "src/pastila_scout/editor_application_v1/runtime_composition.py",
    "tests/test_editor_application_runtime_composition_v1.py",
}
MAINTENANCE_SCOPE = {
    "tests/test_editor_application_contracts_v1.py",
    "tests/test_editor_application_v1.py",
}


def test_exact_private_zero_argument_authority() -> None:
    function = application_runtime._compose_editor_application_runtime_v1
    assert tuple(inspect.signature(function).parameters) == ()
    assert (
        inspect.get_annotations(function)["return"] == "EditorApplicationCoordinatorV1"
    )
    assert "_compose_editor_application_runtime_v1" not in application_runtime.__all__
    assert application_runtime.__all__ == ()


def test_nominal_composition_is_exact_and_fresh() -> None:
    first = application_runtime._compose_editor_application_runtime_v1()
    second = application_runtime._compose_editor_application_runtime_v1()
    assert type(first) is EditorApplicationCoordinatorV1
    assert type(second) is EditorApplicationCoordinatorV1
    assert first is not second


def test_composition_is_passive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "os.getenv", lambda *args, **kwargs: pytest.fail("environment read")
    )
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda *args, **kwargs: pytest.fail("HTTP client construction"),
    )
    before = set(sys.modules)
    result = application_runtime._compose_editor_application_runtime_v1()
    assert type(result) is EditorApplicationCoordinatorV1
    assert "openai" not in set(sys.modules) - before


def test_runtime_factory_has_exact_five_dependencies() -> None:
    factory = runtime._create_editor_generation_runtime_session_factory_v1()
    assert type(factory) is EditorGenerationRuntimeSessionFactoryV1
    values = tuple(
        object.__getattribute__(factory, name) for name in runtime._FACTORY_FIELDS
    )
    assert len(values) == 5
    assert type(values[0]) is runtime._OpenAIComposerFactoryV1
    assert type(values[1]) is runtime._OllamaRuntimeSessionFactoryV1
    assert type(values[2]) is runtime._FailClosedLegacyWorkflowV1
    assert type(values[3]) is runtime._EditorAdapterDependenciesFactoryV1


def test_runtime_symbols_have_existing_composition_identity() -> None:
    symbols = (
        runtime._OpenAIComposerFactoryV1,
        runtime._OllamaRuntimeSessionFactoryV1,
        runtime._OllamaRuntimeLifecycleV1,
        runtime._EditorAdapterDependenciesFactoryV1,
        runtime._EditorRuntimeClockV1,
        runtime._EditorRuntimeCancellationSourceV1,
        runtime._EditorAttemptReferenceFactoryV1,
        runtime._FailClosedLegacyWorkflowV1,
    )
    assert all(item.__module__ == runtime.__name__ for item in symbols)
    assert not Path(
        "src/pastila_scout/editor_generation_runtime_v1/production.py"
    ).exists()


def test_openai_helper_is_passive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "os.getenv", lambda *args, **kwargs: pytest.fail("credential read")
    )
    composer = _create_environment_openai_runtime_composer_v2(
        model_identifier="gpt-4.1-mini", timeout_seconds=30
    )
    assert type(composer) is OpenAIRuntimeComposerV2


def test_openai_factory_delegates_once(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = _create_environment_openai_runtime_composer_v2(
        model_identifier="gpt-4.1-mini", timeout_seconds=30
    )
    calls = []

    def create(*, model_identifier, timeout_seconds):
        calls.append((model_identifier, timeout_seconds))
        return expected

    monkeypatch.setattr(
        runtime, "_create_environment_openai_runtime_composer_v2", create
    )
    actual = runtime._OpenAIComposerFactoryV1().create(
        model_identifier="gpt-4.1-mini", timeout_seconds=30
    )
    assert actual is expected
    assert calls == [("gpt-4.1-mini", 30)]


def test_adapter_dependencies_are_fresh_and_exact() -> None:
    first = runtime._EditorAdapterDependenciesFactoryV1().create(
        operation_reference="operation-v1"
    )
    second = runtime._EditorAdapterDependenciesFactoryV1().create(
        operation_reference="operation-v1"
    )
    assert type(first.clock) is runtime._EditorRuntimeClockV1
    assert type(first.cancellation_source) is runtime._EditorRuntimeCancellationSourceV1
    assert type(first.reference_factory) is runtime._EditorAttemptReferenceFactoryV1
    assert first.attempt_recorder is not second.attempt_recorder
    assert first.cancellation_source.snapshot().cancellation_requested is False
    assert first.clock.now().utcoffset().total_seconds() == 0


def test_attempt_reference_is_deterministic() -> None:
    factory = runtime._EditorAttemptReferenceFactoryV1(
        operation_reference="operation-v1"
    )
    fingerprint = "a" * 64
    first = factory.create(prompt_fingerprint=fingerprint, attempt_number=1)
    second = copy.copy(factory).create(prompt_fingerprint=fingerprint, attempt_number=1)
    assert first == second
    assert first.startswith("editor-attempt-v1-1-")
    assert len(first) <= 120


@pytest.mark.parametrize(
    "fingerprint,attempt", [("A" * 64, 1), ("a" * 63, 1), ("a" * 64, 0)]
)
def test_attempt_reference_rejects_invalid_values(fingerprint, attempt) -> None:
    factory = runtime._EditorAttemptReferenceFactoryV1(
        operation_reference="operation-v1"
    )
    with pytest.raises(EditorGenerationRuntimeCompositionError):
        factory.create(prompt_fingerprint=fingerprint, attempt_number=attempt)


def test_fail_closed_legacy_workflow() -> None:
    with pytest.raises(EditorGenerationRuntimeCompositionError):
        runtime._FailClosedLegacyWorkflowV1().execute(object())


def test_controlled_generator_factory_protocol_signature() -> None:
    signature = inspect.signature(_EditorControlledGeneratorFactoryV1Impl.create)
    assert tuple(signature.parameters) == ("self", "provider", "config")
    assert signature.parameters["provider"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["config"].kind is inspect.Parameter.KEYWORD_ONLY


def test_operational_composer_returns_exact_type() -> None:
    factory = runtime._create_editor_generation_runtime_session_factory_v1()
    result = _create_editor_operational_execution_coordinator_v1(
        session_factory=factory
    )
    assert type(result) is EditorOperationalExecutionCoordinatorV1


@pytest.mark.parametrize("stage", ("runtime", "operational", "application"))
def test_rt1_rt3_reduce_to_safe_public_error(
    monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    if stage == "runtime":
        monkeypatch.setattr(
            application_runtime,
            "_create_editor_generation_runtime_session_factory_v1",
            lambda: object(),
        )
    elif stage == "operational":
        monkeypatch.setattr(
            application_runtime,
            "_create_editor_operational_execution_coordinator_v1",
            lambda **kwargs: object(),
        )
    else:
        monkeypatch.setattr(
            application_runtime,
            "_compose_editor_application_coordinator_v1",
            lambda **kwargs: object(),
        )
    with pytest.raises(EditorApplicationCoordinatorError) as captured:
        application_runtime._compose_editor_application_runtime_v1()
    error = captured.value
    assert str(error) == "Editor application coordinator failed."
    assert error.__cause__ is None
    assert error.__context__ is None
    assert error.__suppress_context__ is True


@pytest.mark.parametrize(
    "value",
    (
        runtime._OpenAIComposerFactoryV1(),
        runtime._OllamaRuntimeSessionFactoryV1(),
        runtime._EditorAdapterDependenciesFactoryV1(),
        runtime._EditorRuntimeClockV1(),
        runtime._EditorRuntimeCancellationSourceV1(),
        runtime._FailClosedLegacyWorkflowV1(),
        _EditorControlledGeneratorFactoryV1Impl(),
    ),
)
def test_stateless_object_safety(value: object) -> None:
    assert not hasattr(value, "__dict__")
    assert "0x" not in repr(value)
    assert copy.copy(value) == value
    assert copy.deepcopy(value) == value
    with pytest.raises(TypeError):
        pickle.dumps(value)


def test_no_public_facade_expansion() -> None:
    import pastila_scout.editor_application_v1 as facade

    assert "_compose_editor_application_runtime_v1" not in facade.__all__


def test_exact_authorized_worktree_shape() -> None:
    import subprocess

    output = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    paths = {line[3:].replace("\\", "/") for line in output}
    assert paths == IMPLEMENTATION_SCOPE | MAINTENANCE_SCOPE
